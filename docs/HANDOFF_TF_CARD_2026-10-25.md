# R2S / R4S TF 卡镜像备份与恢复交接

日期：2026-10-25

## 当前任务与状态

- 用户提供了以前实际使用的 macOS 命令，要求先整理 handoff。
- 本次只整理文档，未识别 TF 卡、执行备份或恢复，未验证历史镜像。
- 后续由代理执行操作，不应仅把命令交给用户。先识别当前设备，再按实际目标操作。
- 历史命令不是当前执行授权；恢复会覆盖目标卡，必须明确本次恢复目标。

## 执行环境与历史文件

命令运行在插有读卡器的 Mac 上，可在本机终端执行，也可 SSH 登录该 Mac 执行。
它们不是在 R2S / R4S 的 OpenWrt shell 中运行的命令。
通过 SSH 执行时，`~/Desktop` 指远端 Mac 当前登录账户的桌面。
sudo 若需密码，应由用户在受控终端输入，不将密码写入脚本或日志。

历史镜像名称：

- R4S：`~/Desktop/R4S_10.0.1.254_Master.img.gz`
- R2S：`~/Desktop/R2S_10.0.1.254_Master.img.gz`

`10.0.1.254` 是文件名中的设备标识，不是备份命令连接的地址。
R2S 与 R4S 镜像按对应机型使用，不混刷。
历史盘符 `disk6`、`disk4` 仅供参考，每次插卡都必须重新识别。

## 关键边界：历史备份只有前 512 MiB

`bs=1m count=512` 在 macOS dd 中表示读取 512 个 1 MiB 块，
即卡前部 536870912 字节，不是整卡镜像。

它可能包含引导、分区表和部分或全部系统分区，但只有确认所有必要分区、
文件系统及数据都位于这个范围内，才能作为完整可恢复的系统备份。
已扩容的 rootfs、后置 overlay 或其他分区可能不在该范围内。
不能因镜像可以解压或可以引导，就认定配置与数据完整。

恢复只会覆盖镜像长度对应的前部，不会自动清空目标卡剩余区域。
若布局不匹配、存在 GPT 尾部信息或需扩容，应另行检查处理，不能盲目认定适用。

## 用户提供的历史命令（原样保留，不直接执行）

查看磁盘：

```sh
diskutil list
```

R4S 备份：

```sh
diskutil unmountDisk /dev/disk6
sudo dd if=/dev/rdisk6 bs=1m count=512 | gzip > ~/Desktop/R4S_10.0.1.254_Master.img.gz
```

R4S 恢复：

```sh
diskutil unmountDisk /dev/disk4
gzip -dc ~/Desktop/R4S_10.0.1.254_Master.img.gz | sudo dd of=/dev/rdisk4 bs=1m
```

R2S 备份：

```sh
diskutil unmountDisk /dev/disk4
sudo dd if=/dev/rdisk4 bs=1m count=512 | gzip > ~/Desktop/R2S_10.0.1.254_Master.img.gz
```

R2S 恢复：

```sh
diskutil unmountDisk /dev/disk4
gzip -dc ~/Desktop/R2S_10.0.1.254_Master.img.gz | sudo dd of=/dev/rdisk4 bs=1m
```

## 后续实际执行步骤

### 1. 确认卡与备份范围

先正常关闭路由器，再拔卡接入读卡器。

```sh
diskutil list
diskutil list external physical
diskutil info /dev/diskN
```

`N` 是占位符。根据外置设备属性、容量、分区布局和插拔前后变化确认目标，
不能直接沿用文档中的数字。记录机型、执行 Mac、账户、盘符、容量及分区结束位置。
判断用户本次要保留历史 512 MiB 母盘方式，还是需要完整整卡备份。
整卡备份应省略 `count=512`，同时确认剩余存储空间足够。

### 2. 备份

- 用 `diskutil unmountDisk` 卸载整张卡上的分区，成功后才继续；不是 eject。
- 默认使用带日期的新文件名，避免覆盖已有 Master 母盘。
- 在 bash / zsh 中先执行 `set -o pipefail`，确保 dd 失败不会被 gzip 的成功退出掩盖。
- macOS dd 运行时可按 Control+T 查看进度。
- 完成后检查管道退出状态、dd 实际读取字节数，并运行 `gzip -t`。
- 镜像哈希可用 `shasum -a 256` 记录；哈希用于后续核对，不能代替首次内容校验。
- 必要时将解压后的镜像字节流与原卡对应范围逐字节或按哈希比较。
- `gzip -t` 通过只证明压缩流完整，不能证明备份包含所有分区。

### 3. 恢复

- 再次确认镜像机型、实际解压字节数、目标卡盘符与容量，明确用户授权覆盖该卡。
- 写卡前先对镜像运行 `gzip -t`，然后卸载目标卡；任一步失败即停止。
- bash / zsh 使用 `set -o pipefail` 后，再按对应机型的恢复方式写卡。
- `if` / `of` 不能反写：备份是卡到文件，恢复是文件到卡。
- 确认管道成功，执行 `sync`，对写入范围做读回比较，再 `diskutil eject /dev/diskN`。
- 测试机应与现有同 IP 路由器隔离，避免 `10.0.1.254` 地址冲突。
- 上机检查引导、接口、管理 IP、配置及 OpenClash 等服务。能启动不等于全部恢复成功。

## 交接结果应报告

机型、操作类型、执行主机与账户、实际盘符、卡容量、镜像路径、
512 MiB 或整卡范围、读取/写入字节数、退出状态、压缩完整性、
SHA256、读回比较结果、是否弹出、上机验证结果或未验证项。
镜像可能包含订阅及设备凭据，不上传 GitHub/Gist，也不提交镜像内容。
