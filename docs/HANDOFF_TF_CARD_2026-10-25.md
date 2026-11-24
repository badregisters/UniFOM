# R2S / R4S TF 卡镜像备份与恢复交接（Agent 实操 SOP）

创建日期：2026-10-25  
更新日期：2026-11-24（补充 Agent 无 TTY 环境下的 `SUDO_ASKPASS` 授权方案与两次实测记录）

---

## 1. 核心目标与给 Codex / Agent 的硬性要求

- **代理必须亲自执行完整个流程**（识别磁盘 → 向用户确认机型/范围/文件名 → 弹窗获取 `sudo` 授权 → 卸载 → `dd` 读写 → `gzip -t` 与读回 SHA256 校验 → 输出标准化报告），**严禁把命令甩给用户让用户自己去终端敲**。
- **每次插卡必须重新识别盘符**（`disk4`、`disk6` 仅是历史记录，绝不能直接硬编码套用）。
- **密码安全边界**：禁止让用户在聊天框里发送 Mac 密码，禁止把密码写进脚本、命令参数或日志。必须使用本文档第 3 节验证通过的 **`SUDO_ASKPASS` + `osascript` 系统密码弹窗 + `sudo -A`** 方案。

---

## 2. 为什么普通 Agent 执行会失败（三个必踩的坑与正解）

在 Codex / Antigravity 等 AI 代理的工具执行环境中，直接跑 `sudo dd ...` 会连续遇到以下三个系统级拦截：

### 坑 1：默认沙箱（Sandbox）拦截 `diskutil` 与 `sudo`
- **现象**：
  - 沙箱内运行 `diskutil list` 报错：`Unable to run because unable to use the DiskManagement framework.`
  - 沙箱内运行 `sudo` 报错：`operation not permitted: sudo`
- **正解**：调用 `diskutil`、访问 `~/Desktop` 以及运行备份/恢复脚本时，必须请求**脱离沙箱执行**（如 `BypassSandbox: true` 或 Codex 的非沙箱/提权模式）。

### 坑 2：Agent 命令无交互式 TTY，普通 `sudo` 直接报错退出
- **现象**：`sudo dd ...` 报错 `sudo: a password is required` 或 `sudo: no tty present and no askpass program specified`。
- **错误做法**：不要用 `echo 密码 | sudo -S`（会泄漏密码到日志），也不要直接放弃让用户自己去跑。

### 坑 3：`osascript -e 'do shell script "dd ..." with administrator privileges'` 被 macOS TCC 拦截
- **现象**：若把 `dd if=/dev/rdiskN` 或 `chown /dev/rdiskN` 放在 `osascript` 的 `with administrator privileges` 里执行，即使输入了管理员密码拿到 `root`，仍会报错：
  `dd: /dev/rdisk4: Operation not permitted (1)`
- **原因**：macOS Sonoma / Sequoia 的 TCC（透明、同意和控制）按负责进程授权外置裸盘（`/dev/rdiskN`）。`do shell script ... with administrator privileges` 由 `SecurityAgent` / `osascript` 派生，**不继承当前终端/IDE 的 TCC 磁盘访问权限**。

### ✅ 唯一验证通过的正解：`sudo -A` + `SUDO_ASKPASS` 弹窗脚本
- **原理**：
  1. 写一个极简的 `askpass.sh`，仅调用 `osascript` 通知 `System Events` 弹出密码输入框（`with hidden answer`），把用户输入的密码通过 `stdout` 吐给 `sudo -A`。
  2. 在主脚本中设置 `export SUDO_ASKPASS="/path/to/askpass.sh"`，直接运行 `sudo -A -v`。
  3. 这样 `sudo` 和子进程 `dd` **依然是当前 Agent 宿主进程（Terminal / IDE）的直接子进程**，完整继承宿主的 TCC 外置磁盘读写权限；同时密码仅在内存中经管道传给 `sudo`，不落盘、不进日志，且一次 `sudo -A -v` 即可缓存凭据供后续备份和读回校验复用。

---

## 3. 标准执行流程（Step-by-Step SOP）

### 第一步：识别外置物理磁盘与分区结束位置

先脱离沙箱执行以下命令，确认当前插入的 TF 卡盘符、总容量和各分区偏移/大小：

```sh
diskutil list external physical
diskutil info /dev/diskN
diskutil info /dev/diskNs1
diskutil info /dev/diskNs2
```

- 将 `N` 替换为实际查到的外置盘编号（例如 `disk4`）。
- **核对设备特征**：
  - `Device Location: External`、`Removable Media: Removable`（常见读卡器名称如 `SDDR-339`）。
  - 计算最后一个分区的结束位置：`Partition Offset + Disk Size`。
  - 例如实测 R2S 固件卡（无论 8.2 GB 还是 31.9 GB 卡）：
    - `diskNs1`：Offset `33,554,432` (32 MiB)，Size `16,777,216` (16 MiB) → 结束于 **48 MiB**
    - `diskNs2`：Offset `67,108,864` (64 MiB)，Size `314,572,800` (300 MiB) → 结束于 `381,681,664` 字节（**364 MiB**）
    - 364 MiB 之后全为未分配空间（`free space`）。因此 `bs=1m count=512`（前 **512 MiB** = `536,870,912` 字节）即可 100% 完整覆盖引导、分区表及全部两个 Linux 分区。

### 第二步：向用户确认关键参数

识别出盘符与分区布局后，必须向用户确认（可合并为一次提问）：

1. **设备机型**：当前卡是 `R2S` 还是 `R4S`？（严禁混刷）
2. **备份范围**：前 512 MiB（`bs=1m count=512`，当确认所有分区结束位置 < 512 MiB 时推荐）还是整卡？
3. **输出/输入文件名**：
   - R2S 默认母盘路径：`~/Desktop/R2S_10.0.1.254_Master.img.gz`
   - R4S 默认母盘路径：`~/Desktop/R4S_10.0.1.254_Master.img.gz`
   - 或带日期的新文件名：`~/Desktop/<机型>_10.0.1.254_YYYY-MM-DD.img.gz`
4. **若为恢复（写卡）操作**：必须向用户明确展示**目标卡盘符（`/dev/diskN`）与精确容量（如 `31.9 GB / 31,914,983,424 字节`）**，获得用户明确确认覆盖后才可写卡。

---

### 第三步：准备 `askpass.sh` 授权辅助脚本

在临时目录（如 `/tmp` 或 Agent 的 `scratch/` 目录）创建 `askpass.sh` 并赋予可执行权限（`chmod +x`）：

```zsh
#!/bin/zsh
osascript \
  -e 'tell application "System Events" to display dialog "请输入 Mac 登录密码以授权 sudo 读写 TF 卡:" default answer "" with hidden answer buttons {"取消", "确定"} default button "确定" with title "UniFOM TF 卡操作授权"' \
  -e 'text returned of result' 2>/dev/null
```

---

### 第四步（场景 A）：执行 TF 卡镜像备份 + 读回 SHA256 校验

创建并执行备份脚本 `backup_tf.sh`（将 `DISK`、`RDISK`、`OUT` 替换为实际确认的值，脱离沙箱运行）：

```zsh
#!/bin/zsh
set -euo pipefail

export SUDO_ASKPASS="/path/to/askpass.sh"

DISK="/dev/disk4"
RDISK="/dev/rdisk4"
OUT="/Users/ayu/Desktop/R2S_10.0.1.254_Master.img.gz"

echo "=== 0. Authenticating sudo via macOS dialog ==="
sudo -A -v

echo "=== 1. Unmounting $DISK ==="
diskutil unmountDisk "$DISK"

sudo -n rm -f "$OUT"

echo "=== 2. Backing up first 512 MiB from $RDISK to $OUT ==="
sudo -n dd if="$RDISK" bs=1m count=512 | gzip -c > "$OUT"
PIPE_STATUS=("${pipestatus[@]}")
echo "dd_exit=${PIPE_STATUS[1]} gzip_exit=${PIPE_STATUS[2]}"

ls -lh "$OUT"
stat -f "compressed_bytes=%z" "$OUT"

echo "=== 3. Testing gzip integrity ==="
gzip -t -v "$OUT"

echo "=== 4. Computing SHA256 checksums ==="
GZ_SHA=$(shasum -a 256 "$OUT" | awk '{print $1}')
echo "gz_sha256=$GZ_SHA"

UNCOMPRESSED_BYTES=$(gzip -dc "$OUT" | wc -c | tr -d ' ')
echo "uncompressed_bytes=$UNCOMPRESSED_BYTES"

IMG_RAW_SHA=$(gzip -dc "$OUT" | shasum -a 256 | awk '{print $1}')
echo "decompressed_sha256=$IMG_RAW_SHA"

CARD_RAW_SHA=$(sudo -n dd if="$RDISK" bs=1m count=512 2>/dev/null | shasum -a 256 | awk '{print $1}')
echo "card_512m_sha256=$CARD_RAW_SHA"

if [[ "$IMG_RAW_SHA" == "$CARD_RAW_SHA" ]]; then
  echo "VERIFY_MATCH=YES"
else
  echo "VERIFY_MATCH=NO"
  exit 1
fi
```

**备份验收要点**：
- `dd_exit=0` 且 `gzip_exit=0`
- `uncompressed_bytes=536870912`（512 MiB）
- `gzip -t -v` 输出 `OK`
- `decompressed_sha256` 与 `card_512m_sha256` 完全一致（`VERIFY_MATCH=YES`）

---

### 第四步（场景 B）：执行 TF 卡镜像恢复（写卡）+ 读回校验 + 安全弹出

恢复前**必须**在脚本开头校验目标盘的外置属性与精确字节容量，防止盘符漂移误写其它磁盘：

```zsh
#!/bin/zsh
set -euo pipefail

export SUDO_ASKPASS="/path/to/askpass.sh"

DISK="/dev/disk4"
RDISK="/dev/rdisk4"
IMG="/Users/ayu/Desktop/R2S_10.0.1.254_Master.img.gz"
EXPECTED_DISK_BYTES="31914983424" # 替换为 diskutil info 查到的目标卡精确字节数

echo "=== 1. Pre-check target disk and image integrity ==="
DISK_INFO=$(diskutil info "$DISK")
if ! echo "$DISK_INFO" | grep -q "${EXPECTED_DISK_BYTES} Bytes"; then
  echo "ERROR: $DISK size does not match expected ${EXPECTED_DISK_BYTES} Bytes!"
  exit 1
fi
if ! echo "$DISK_INFO" | grep -q "Device Location:.*External"; then
  echo "ERROR: $DISK is not an external disk!"
  exit 1
fi

gzip -t -v "$IMG"
EXPECTED_RAW_SHA=$(gzip -dc "$IMG" | shasum -a 256 | awk '{print $1}')
echo "expected_sha256=$EXPECTED_RAW_SHA"

echo "=== 2. Authenticating sudo via macOS dialog ==="
sudo -A -v

echo "=== 3. Unmounting $DISK ==="
diskutil unmountDisk "$DISK"

echo "=== 4. Restoring $IMG to $RDISK ==="
gzip -dc "$IMG" | sudo -n dd of="$RDISK" bs=1m
PIPE_STATUS=("${pipestatus[@]}")
echo "gzip_exit=${PIPE_STATUS[1]} dd_exit=${PIPE_STATUS[2]}"

echo "=== 5. Syncing buffers ==="
sync

echo "=== 6. Unmounting $DISK before read-back verification ==="
diskutil unmountDisk "$DISK"

echo "=== 7. Read-back SHA256 verification (first 512 MiB) ==="
CARD_RAW_SHA=$(sudo -n dd if="$RDISK" bs=1m count=512 2>/dev/null | shasum -a 256 | awk '{print $1}')
echo "readback_sha256=$CARD_RAW_SHA"

if [[ "$CARD_RAW_SHA" == "$EXPECTED_RAW_SHA" ]]; then
  echo "VERIFY_MATCH=YES"
else
  echo "VERIFY_MATCH=NO"
  exit 1
fi

echo "=== 8. Ejecting $DISK ==="
diskutil eject "$DISK"
```

---

## 4. 关键边界说明（前 512 MiB vs 整卡）

- `bs=1m count=512` 在 macOS `dd` 中表示读取 512 个 1 MiB 块（`536,870,912` 字节），不是整卡镜像。
- 每次备份前必须通过 `diskutil info /dev/diskNs1`、`diskutil info /dev/diskNs2`（及后续分区）确认所有分区的结束偏移是否均在 `536,870,912` 字节以内。若存在已扩容的 rootfs 或后置 overlay 分区超出 512 MiB，则必须告知用户并改用整卡备份（省略 `count=512`）。
- 恢复时仅覆盖目标卡前 512 MiB；写完后若 macOS 自动挂载分区，需再次 `diskutil unmountDisk` 后再做 `dd` 读回校验，最后执行 `diskutil eject`。
- 测试机上机启动时，注意与局域网内现有同 IP（如 `10.0.1.254` 或 `192.168.30.254`）的路由器隔离，避免 IP 冲突。

---

## 5. 交接结果报告模板与历史实测记录

每次操作完成后，Agent 必须向用户输出包含以下字段的表格：
- 机型、操作类型、执行主机与账户、实际盘符、卡容量与分区布局、镜像路径、备份/恢复范围、读取/写入字节数、压缩包大小、管道退出状态、`gzip -t` 压缩完整性、`.img.gz` SHA256、512 MiB 原始流 SHA256（镜像 vs 卡读回）、读回比较结果、是否已弹出（`eject`）、上机验证状态。
- **安全红线**：镜像内含机场订阅及设备凭据，严禁上传 GitHub / Gist 或提交到 Git 仓库。

### 历史实测记录汇总

| 日期 | 操作 | 机型 | 盘符 / 读卡器 | 卡容量 | 镜像路径 | 压缩包大小 / SHA256 | 512 MiB 原始流 SHA256（镜像 & 卡读回） | 校验结果 |
|---|---|---|---|---|---|---|---|---|
| 2026-10-25 15:48 | 备份（前 512 MiB） | R2S | `/dev/disk4` (`SDDR-339`) | 8.2 GB (`8,168,931,328` B) | `~/Desktop/R2S_10.0.1.254_Master.img.gz` | `163,961,168` B<br>`64057b3e...372e2ad` | `3ca022484cb71ef9ec3265ebbe11262d6abb770500f70c05208e3a0d2e090431` | `VERIFY_MATCH=YES` |
| 2026-10-25 16:15 | 恢复（前 512 MiB） | R2S | `/dev/disk4` (`SDDR-339`) | 31.9 GB (`31,914,983,424` B) | `~/Desktop/R2S_10.0.1.254_Master.img.gz` | `163,961,168` B<br>`64057b3e...372e2ad` | `3ca022484cb71ef9ec3265ebbe11262d6abb770500f70c05208e3a0d2e090431` | `VERIFY_MATCH=YES`（已弹出） |
| 2026-11-24 22:25 | 备份（前 512 MiB） | R2S | `/dev/disk4` (`SDDR-339`) | 31.9 GB (`31,914,983,424` B) | `~/Desktop/R2S_10.0.1.254_Master.img.gz` | `162,632,848` B<br>`8e811aa4...01d084a` | `c1e78d646776f7af3c0ccea2a0efa818c9c003644c8a86e77c86085fa3bb4be6` | `VERIFY_MATCH=YES` |
