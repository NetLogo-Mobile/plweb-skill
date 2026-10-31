# 可填值与标签

## 1. 分类与目标

| 字段 | 值 | 说明 |
|---|---|---|
| 作品 Category | `Experiment`、`Discussion` | 实验区、讨论区（黑洞） |
| 评论 TargetType | `User`、`Experiment`、`Discussion` | 用户留言板、实验评论、讨论评论 |
| MoveCategory.Target | `Experiment`、`Discussion` | 目标分区 |
| GetLibrary.Identifier | `Discussions` | 讨论页；其他 Identifier 使用服务端页面配置，不把任意名称当作有效页 |

Model 是客户端出现的内容分类，可见于标签规则及关联数据；不由此推定所有作品接口都支持 Category=Model。

## 2. 语言

`Chinese`、`English`、`ChineseTraditional`、`German`、`French`、`Japanese`、`Italian`、`Polish`、`Spanish`、`Ukrainian`。

传 API 名称，不传 zh-CN 等浏览器语言代码。模板某语言字段为 null 时回退到可用语言或原文本。

## 3. 查询、关系与操作值

| 字段 | 可填值 | 语义与限制 |
|---|---|---|
| Query.Special | `null`、`Favorite`、`Support`、`Star` | null为普通列表；其余来自客户端特殊查询枚举，不保证与任意作者/标签组合兼容 |
| Query.Sort | `0` | 默认排序；不要把不同分区、区域和版本的数字排序含义混用 |
| Query.Sort 其他线索 | `1`、`2` | 客户端出现的值，不能据名称固定为统一的热门/随机语义 |
| GetRelations.DisplayType | `0`、`1` | 粉丝、关注 |
| GetUser返回Relation | `0`、`1`、`2`、`3` | 无关注、自己关注对方、对方关注自己、互关；它是返回值，不是DisplayType |
| Follow.Action | `1`、`0` | 关注、取消关注 |
| Block.Action | `1`、`0` | 屏蔽、解除；关系副作用由后端决定 |
| StarContent.Type | `0`、`1` | 收藏、金币支持 |
| StarContent.Status | `true`、`false` | 收藏开关；不能用false退款支持 |
| PostComment.Special | `null`、`Reminder` | 普通评论、用户警告 |
| 其他Special线索 | `Locked`、`Anonymous` | 客户端枚举线索，不据此假定可用于任意目标或身份 |
| ModifyInformation.Field | `Signature` | 修改签名；其他资料字段需有可靠参数依据 |

分页采用正数 Take，常用20。不要硬编码“负数都取绝对值”，也不要把库中的-101当作通用可用值。

## 4. 通知类别

| CategoryID | 分类 |
|---|---|
| 0 | 全部 |
| 1 | 系统邮件 |
| 2 | 关注、社交及相关订阅通知 |
| 3 | 评论与回复 |
| 4 | 作品通知 |
| 5 | 管理记录 |

分类名称不是完整事件枚举，正文应依TemplateID和Fields解释。Unread为0表示未读取，非零为读取时间戳；Handled不等同Unread。

## 5. 身份与任命

用户 Verification 中出现的身份值：`Oldtimer`、`Volunteer`、`Junior`、`Emeritus`、`Editor`、`Administrator`、`Banned`；普通身份还可能为空或null。

网页有Teacher翻译线索，不据此当作稳定的管理角色。原生客户端任命菜单包含 Volunteer、Junior、Editor、Emeritus；任命Type不是完整Verification枚举，Oldtimer不能直接作为可用Appoint.Type。封禁正常清除一切身份，解封不补回。

## 6. 实时标签配置

标签不再维护静态快照。选择、校验或编辑标签之前，调用 `get_available_tags`，或通用版 `CommunityReads.get_available_tags()`，从正常 Authenticate 响应中的 `Data.ContentTags` 读取当前完整配置。失败时说明错误，不恢复旧表或自行编造标签。

发请求使用 `Identifier`，`Subject` 是多语言显示名；返回时保留 `Tips`、`ModeratorTips`、`Available`、`Flags`、`Conflicts`。Flags/Conflicts 可能是 `$values` 包装数组，辅助接口会规范为数组。不要把显示名或旧别名当作可新增 Identifier。

`Available=false` 不能单独用来排除所有标签，Flags 也不等于后端授权。依据实时 Flags 检查分类、角色、系统类型、Required/Immutable/EditOnly 等限制，保留原有正确的系统标签；依据实时 Conflicts 和 Tips 检查冲突与附加条件。不要把配置中列出的标签宣称为当前账号都能提交；最终以服务端正常权限校验为准。

账号会话、公开配置与不同筛选分区可能有差别。一次批次读取一次相关配置即可，不为每个对象重新登录；不得用静态表替代失败的实时读取。详见 [自动分页与批量接口](operations.md)。

## 来源

- 服务端公开配置：Authenticate.Data.ContentTags。
- [网页设备标识](https://github.com/NetLogo-Mobile/plweb2/blob/85ca269a6e1bf1ecc353882f0e38217a2b0c24be/src/services/api/getDevice.ts)。
- [网页类型与枚举线索](https://github.com/NetLogo-Mobile/plweb2/blob/85ca269a6e1bf1ecc353882f0e38217a2b0c24be/src/pl-serve-type-main/type/main.ts)。客户端类型可以陈旧，不能覆盖服务端返回的校验结果。
