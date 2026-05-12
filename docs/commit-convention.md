# Commit 规范

格式：`<类型>(<平台>): <说明>`

## 类型

| 类型 | 用途 |
|------|------|
| `feat` | 新增规则或功能 |
| `fix` | 修正错误的规则 |
| `remove` | 删除规则 |
| `tune` | 调整参数（DNS、超时、容差等） |
| `refactor` | 结构调整，功能不变 |

## 平台

| 标识 | 平台 |
|------|------|
| `sr` | Shadowrocket |
| `oc` | OpenClash |
| `all` | 所有平台 |

## 示例

```
feat(sr): 新增 Telegram 分流规则
fix(sr): 修正 iCloud 域名漏网问题
tune(sr): 调整自动测速容差至 75ms
remove(sr): 移除冗余本地规则
refactor(all): 重新整理策略组顺序
```

## 说明

文件头的 Changelog 面向用户，描述配置功能变化；git commit 记录面向自己，追踪每次改动历史。两者独立维护，互不影响。
