# 接口与流程

## 目录

认证与通用请求；作品查询；作品编辑与标签；收藏和金币支持；删除、隐藏与恢复；评论与警告；通知；用户资料和关系；管理；活动与图片。

## 1. 认证与通用请求

中国区基址：`https://physics-api-cn.turtlesim.com`。除 `GET /Users` 外，下列可调用接口使用 `POST` 和 JSON；图片资源及上传例外。

普通业务请求头：

```http
Content-Type: application/json
x-API-Token: <Token>
x-API-AuthCode: <AuthCode>
x-API-Version: 2502
```

登录专用调用使用 `Content-Type`；Token 登录另带已有的 Token、AuthCode。请求体 `Version` 与请求头 `x-API-Version` 是不同字段，不合并处理。

### POST /Users/Authenticate

| 字段 | 类型 | 填写方式 |
|---|---|---|
| `Login` | string/null | 用户名或邮箱；匿名、Token 登录为 null |
| `Password` | string/null | 账号密码；匿名、Token 登录为 null |
| `Version` | integer | 网页协议值 `2411` |
| `Device.Identifier` | string | 默认固定值 `0d1a760b44023875d2123f2cfcb56dad`；也可使用已有浏览器的 visitorId |
| `Device.Language` | string | 如 `Chinese`，值见 practical-values.md |
| `Device` 其他属性 | 按属性类型 | Token 登录可补网页设备信息，不伪造账号身份 |

默认硬编码并复用以下设备标识，无需浏览器环境：

```javascript
const DEVICE_IDENTIFIER = "0d1a760b44023875d2123f2cfcb56dad";
const body = {
  Login: login,
  Password: password,
  Version: 2411,
  Device: { Identifier: DEVICE_IDENTIFIER, Language: "Chinese" }
};
```

固定标识由网页方式生成，可作为这个 Skill 的稳定设备标识持续使用。普通 HTTP 客户端可直接使用它，不需要安装指纹库或启动浏览器。不要为每个请求、登录或任务生成新标识，以免在服务端积累无用设备记录。

可选浏览器方式：需要沿用已有网页设备时，在该浏览器环境中使用 FingerprintJS（网页版本线索为 `5.0.1`），以取得的 visitorId 覆盖默认标识：

```javascript
const fp = await FingerprintJS.load();
const { visitorId } = await fp.get();
body.Device.Identifier = visitorId;
```

选择浏览器方式后复用同一指纹；不要在固定标识和浏览器指纹之间无故切换。设备标识不是登录凭据，不提供额外权限。

Token 登录：`Login=null, Password=null`，请求头携带已有凭据。匿名登录：同样的空登录字段，但不带账号凭据；适合取得公开首页和标签配置，不要为了读取每一页反复创建匿名会话。

成功响应顶层提供 `Token`、`AuthCode`，账号和配置在 `Data`。按响应更新会话凭据；响应头若续发 `x-API-Token`、`x-API-AuthCode`，也应更新。匿名 `Token` 可以为 null，不能把匿名 AuthCode 当作账号权限。不要向无关主机转发这些认证头。

`Data.ContentTags` 是标签配置；`Data.Library` 是首页分区数据；`Data.User`、`Data.Statistic` 是账号与统计信息，字段可为空。账号登录和匿名登录返回的扩展数据可以不同。

### 响应处理

```json
{"Status":200,"Message":"","Data":{}}
```

`Data` 可以是对象、数组、`$values` 包装、字符串、布尔值或 null，不统一转换成对象。失败时保存非敏感的 `Status`、`Message` 和字段错误 `Data`。

- `User.Not.Allowed`、`Permission.Denied`：后端不允许操作，不绕过。
- `Input.Field.Invalid`：检查 `Data` 指向的字段及其类型、取值。
- `Input.Field.Outof.Bound`：长度或数值范围不合法，不猜测精确边界。
- `Nickname.Duplicated`：昵称被占用；原样提交已有昵称也可能触发。
- `Stopword.Blocked...`：内容被服务端拒绝，不规避过滤。

业务错误也可能通过 HTTP 200 返回。`Status=403` 不一定都是令牌过期，应结合 `Message` 判断，不对所有 403 循环重新登录。

## 2. 作品查询

以下作品摘要参数使用摘要 ID。保存数据和工作区参数使用摘要中的 `ContentID`。

| 接口 | JSON 字段 | 返回 Data |
|---|---|---|
| `GET /Users` | 无请求体 | 启动页、导航和分区数据 |
| `/Contents/GetLibrary` | `Identifier:string, Language:string`；讨论页用 `Discussions, Chinese` | 页面 Blocks 等结构 |
| `/Contents/QueryExperiments` | 外层 `Query`，字段见下表 | `Data.$values` 中的摘要 |
| `/Contents/GetSummary` | `Category:string, ContentID:string`；此处传摘要 ID | 直接是摘要对象 |
| `/Contents/GetExperiment` | `ContentID:string`；传保存 ID | 实验保存对象 |
| `/Contents/GetWorkspace` | `ContentID:string, Language:string`；传保存 ID | 工作区对象，或成功的 null |
| `/Contents/GetDerivatives` | `Category:string, ContentID:string, Language:string, WithSummary:boolean`；传摘要 ID | Summary、Parent、Model、Supporters、Survey、Experiments 等关联数据；字段可为空 |
| `/Contents/GetProfile` | `ID:string`；用户 ID | `Experiments` 等主页分组 |
| `/Contents/GetSupporters` | `Category:string, ContentID:string, Skip:integer, Take:integer`；传摘要 ID | 支持者列表，通常在 `$values` |

`GetExperiment` 的 `StatusSave`、`CameraSave` 是序列化实验数据，不是社区介绍。不要仅为修改标题、介绍或标签而重建实验模型。

### QueryExperiments.Query

```json
{
  "Query": {
    "Category": "Discussion",
    "Languages": [],
    "ExcludeLanguages": [],
    "Tags": null,
    "ExcludeTags": null,
    "ModelTags": null,
    "ModelID": null,
    "ParentID": null,
    "UserID": null,
    "Special": null,
    "From": null,
    "Skip": 0,
    "Take": 20,
    "Days": 0,
    "Sort": 0,
    "ShowAnnouncement": false
  }
}
```

| 字段 | 类型 | 用途 |
|---|---|---|
| `Category` | string | `Experiment` 或 `Discussion`；未知分区不自动并入其中 |
| `Languages / ExcludeLanguages` | string[] | 包含或排除的语言；空数组不加相应筛选 |
| `Tags / ExcludeTags` | string[]/null | 按标签 Identifier 包含或排除 |
| `ModelTags` | string[]/null | 模型标签筛选；没有需求时为 null |
| `ModelID / ParentID` | string/null | 模型、父作品筛选 |
| `UserID` | string/null | 作者筛选，优先传用户 ID |
| `Special` | string/null | 特殊列表，值见 practical-values.md；普通查询为 null |
| `From` | string/null | 按时间方向续页的游标；当前接口实测传上一页末条摘要 ID，首页 null。直接传毫秒数、数字时间字符串或 ISO 时间会返回 Input.Field.Invalid |
| `Skip / Take` | integer | `Skip` 固定 0，传跳过条数无效且会重复页；`Take` 为正数页大小，通常 20 |
| `Days` | integer | 时间窗口条件；不指定窗口用 0 |
| `Sort` | integer | 排序值见 practical-values.md |
| `ShowAnnouncement` | boolean | 是否带公告 |

作品分页固定筛选条件和排序，保持 `Skip=0`，每次用上一页末尾作品的摘要 ID 推进 `Query.From`，用 `SortingDate` 记录并核对时间范围。`Skip` 传条数无效，会反复返回同页。当前接口实测不接受直接传毫秒或 ISO 时间；不要把时间方向的游标误写为原始时间参数。按摘要 ID 去重，遇空页、游标不推进或整页无新增 ID 时停止；不凭样本断言全站不存在。细节见 [分页与查找目标](finding.md)。负数 Take 可被拒绝，不依赖 `-101`。

`GetSupporters` 的完整分页协议未核对，只读取所需首批并说明范围，不能假定Skip是正确条数偏移，也不能擅自补From或复制作品列表分页协议。

## 3. 编辑作品、标签与移动

### POST /Contents/SubmitExperiment

文本、标签编辑共用提交接口，没有必要寻找或猜造独立的改标签端点。

```javascript
const payload = {
  Summary: {
    ...originalSummary,
    Subject: title,
    Description: introduction.split("\n"),
    Tags: tagIdentifiers,
    Language: "Chinese"
  },
  Workspace: workspace ? { ...workspace, Summary: null } : null
};
```

- `Summary`：从 `GetSummary` 获取完整对象，保留 `ID`、`ContentID`、作者、分类、图片与未修改字段。
- `Subject`：标题字符串；`Description`：按行拆分的字符串数组；`Tags`：标签 Identifier 数组。
- `Workspace`：从 `GetWorkspace` 读取的原对象；无工作区时为 null，不把 null 当成读取失败。
- 只改标签时仅替换 `Summary.Tags`；先检查标签冲突、系统类型标签和服务端权限，不把翻译名称当成 Identifier。
- 新建作品需要与目标实验类型匹配的完整摘要和保存结构，不把既有作品改 ID 后当作可靠的新建协议。

成功后按原摘要 ID 和分类重新 `GetSummary`，确认标题、介绍、标签及其他需要保留的内容。

### POST /Contents/MoveCategory

```json
{"Category":"Discussion","SummaryID":"<摘要ID>","Target":"Experiment"}
```

`Category` 是来源分区，`Target` 是目标分区。成功后按目标分区读取相同摘要 ID。需要移回时交换来源与目标；核对标签是否仍适用，移动不等于改标签。

## 4. 收藏与金币支持

### POST /Contents/IsStarred

请求：`{Category:string, ContentID:string}`，传摘要 ID。成功 `Data` 为收藏状态布尔值。

### POST /Contents/StarContent

```json
{"Category":"Discussion","ContentID":"<摘要ID>","Type":0,"Status":true}
```

- `Type=0`：收藏；`Status=true` 添加，`false` 取消。恢复操作使用原布尔状态，不盲目切换。
- `Type=1`：金币支持，消耗 100 金币。不能支持自己的作品，同一账号不能对同一作品重复支持。`Status=false` 不是支持退款或撤销协议。
- 支持前核对对象、已有支持信息与用户的花费授权；余额不代表已有支持状态。`IsStarred` 查询收藏，不能用它替代支持状态检查。
- `GetSupporters` 首批列表中没有自己不证明从未支持；列表可能分页。后端拒绝重复或自支持时停止，不换账号、改身份或变造 ID 重试。

## 5. 删除、隐藏与恢复

### POST /Contents/RemoveExperiment

```json
{"Category":"Discussion","SummaryID":"<摘要ID>","Hiding":true,"Reason":"<操作理由>"}
```

删除、隐藏作品会扣金币。`Hiding=true` 是隐藏调用形式；不要把所有删除操作都描述成物理删除，也不要自行推断 `Hiding=false` 的删除策略。删除与隐藏都可能留下管理记录，费用不会因恢复自动返还。

### POST /Contents/RestoreExperiment

```json
{"Category":"Discussion","SummaryID":"<摘要ID>","Reason":"<恢复理由>"}
```

恢复后重新读取摘要并核对可见性。Visibility映射参考responses.md；旧网页说明与后端枚举存在冲突，未经写入核验不能仅凭数字断言已隐藏/恢复。恢复不是 `RemoveExperiment(Hiding=false)` 的同义替代。

## 6. 评论、回复、@ 与警告

### POST /Messages/GetComments

```json
{"TargetID":"<目标ID>","TargetType":"User","CommentID":"","Skip":0,"Take":20}
```

`TargetType` 为 User、Experiment 或 Discussion。结果位于 `Data.Comments`，并可带 `Count`、`Target`。

评论已做授权账号只读测试：第一页 `CommentID=""`、`Skip=0`，续页 `CommentID=上一页末条评论ID`、`Skip=0`。服务端会再次包含边界评论，按 ID 去重，不能盲删每页首条。GetComments.Data.Comments 可为数组或 `$values` 包装。整页无新增或游标不推进时停止；不要递增 Skip 条数或给此接口补作品的 From。指定数量优先使用 fetch_comments 内部循环，详见 operations.md。

### POST /Messages/PostComment

```json
{
  "TargetID":"<目标ID>",
  "TargetType":"User",
  "Content":"<留言正文>",
  "ReplyID":"",
  "Language":"Chinese",
  "Special":null,
  "ID":"",
  "UserID":""
}
```

- `TargetID`：留言板用户 ID，或作品摘要 ID。
- `ReplyID`：被回复的用户 ID，不是评论 ID；普通留言为空字符串。
- `Content`：文本和社区富文本。用户引用形式为 `<user=用户ID>显示名</user>`。回复或 @ 可以产生通知，包括本人引用。
- `Special=null`：普通评论。`Special=Reminder` 且 `TargetType=User`：管理警告，会出现 Reminder、Locked 标记；需要正常管理权限。
- 不把 Discussion 上的 `Special=Reminder` 成功响应视为有效警告：它可以生成无警告标记的普通评论。
- `ID`、`UserID` 的空字符串来自网页请求形式，不是身份授权手段。评论作者由正常登录身份决定。

成功 `Data` 是评论对象。保留返回的评论 ID；警告正文可能由服务端加工，不能仅靠提交正文完全相等定位。Locked 警告的删除由服务端管理权限控制。

### POST /Messages/RemoveComment

请求：`{TargetType:string, CommentID:string}`。只删除任务范围内的评论；成功 Data 可以为字符串。删除后按目标重新读取确认，已发通知与管理记录不等于同步撤回。

## 7. 通知

### POST /Messages/GetMessages

```json
{"CategoryID":0,"Skip":0,"Take":20,"NoTemplates":false}
```

返回 `Data.Messages`，模板位于 `Data.Templates`。按对方后端说明，GetMessages首批可能清零聚合未读计数，属于有状态读取；本轮未以收件箱实测验证。首次取 `NoTemplates=false` 获取模板，后续页可为 true 并复用模板；模板 ID 或配置变化时重新获取。分类 0–5 见 practical-values.md。当前只保证首批；通知分页协议未核验，不擅自补From或宣称Skip能正确遍历。

消息包含 `ID`、`CategoryID`、`TemplateID`、`Users`、`UserNames`、`Fields`、`Numbers`、`Unread`、`Handled` 等。按 TemplateID 关联模板，用 Subject/Content 的语言字段生成标题和正文；缺少模板时可回退到 `Fields.Content`。

| 占位符 | 数据来源 |
|---|---|
| `{Users}` | Users、UserNames，生成用户引用 |
| `{Experiment}` | Fields.Discussion/DiscussionID 或 Experiment/ExperimentID |
| `{$Content}` | Fields.Content |
| `{$TargetName}` | Fields.TargetName，可回退登录用户昵称 |
| `{$Until}` | Fields.Until |
| `{$Editor}` | Fields.Editor |
| `{$Gold}` | Numbers.Gold |

这些是网页采用的模板规则，不保证涵盖所有服务端模板。分类名称不能代替模板语义，例如社交分类也可能包含作品订阅通知。

### POST /Messages/GetMessage

请求：`{MessageID:string}`。它执行通知读取处理，返回 User、Statistic、Backpack、Bonuses、Relation 等数据包，不是消息正文。

- 通知 `Unread=0`：未读；读取后为非零读取时间戳。
- `Handled` 是另一个状态，读取不等于处理邀请。
- `Statistic.UnreadMessages / UnreadLetters` 是聚合提示，不按它们反推每条通知状态。读取后以重新查询的消息条目为准。
- 某些模板带 Bonuses、Action；不要为获取正文自动逐条调用 GetMessage，也不把处理邀请或领取奖励视为纯查询。
- 网页本地 `clearNotificationUnread()` 只清前端提示，不是服务端批量已读接口。

## 8. 用户资料与关系

| 接口 | JSON 字段 | 含义和要点 |
|---|---|---|
| `/Users/GetUser` | `{ID:string}` 或 `{Name:string}` | 按ID或完整昵称读取；实测Name精确定位可用，两者同时传时ID优先。不等于模糊搜索 |
| `/Users/GetRelations` | `UserID:string, DisplayType:integer, Query:string, Skip:integer, Take:integer` | 关系列表在 `$values`；0粉丝、1关注。Query可在关系范围按精确昵称筛选，非全站模糊搜索；Skip语义和完整续页先单独核验 |
| `/Users/Follow` | `TargetID:string, Action:integer` | 1关注、0取消；Relation读回核对 |
| `/Users/Block` | `TargetID:string, Action:integer` | 屏蔽状态操作；自目标被拒绝，关系副作用不可假定完全可恢复 |
| `/Users/Rename` | `UserID:string, Target:string` | Target为新昵称；同名可报重复，成功后重读确认 |
| `/Users/ModifyInformation` | `Field:string, Target:string` | 签名使用 `Field=Signature`；其他字段不凭名称猜写 |
| `/Users/SetCover` | `Category:string, ContentID:string` | 用作品摘要ID设置主页封面引用；原封面见Statistic.Cover |
| `/Users/Logout` | `{}` | 退出登录会话；如需继续任务，重新正常登录 |

Relation 的已知值：0无互关、1自己关注对方、2对方关注自己、3互关。不要假设屏蔽后只需还原自己的关注就能恢复对方的关系。

## 9. 管理

管理操作只在用户授权范围内执行，服从服务端正常角色判断。读取到 Editor 等身份不表示所有管理接口都可调用。

| 接口 | JSON 字段 | 行为 |
|---|---|---|
| `/Users/Ban` | `TargetID:string, Reason:string, Length:integer` | 封禁天数为正整数；封禁清除一切身份 |
| `/Users/Unban` | `TargetID:string, Reason:string` | 解除封禁，不恢复原身份 |
| `/Users/Appoint` | `TargetID:string, Type:string, Length:integer, Reason:string` | 角色任命；Type及任期必须符合服务端要求 |

Appoint 的客户端角色选项包括 Volunteer、Junior、Editor、Emeritus；不要由 Verification 枚举推导所有角色都可任命。Oldtimer 不能直接作为可用 Type；Type校验失败不通过变体猜测绕过。

任命、解除、封禁会产生通知或管理记录。用户只要求封禁/解封时，不附带恢复原角色的任命操作。

## 10. 活动与图片

| 接口 | JSON 字段 | 注意事项 |
|---|---|---|
| `/Users/SyncActivities` | `ContentID:string, Language:string` | 活动同步调用；不视为奖励领取接口 |
| `/Users/ReceiveBonus` | `ActivityID:string, Index:integer, Statistic:object` | 使用服务端活动ID、奖励索引及原Statistic；领取状态不可完整撤销 |
| `/Contents/ConfirmExperiment` | `Category:string, SummaryID:string, Image:integer, Extension:string` | 确认图片索引；不是完整文件上传协议 |

图片上传还涉及 SubmitExperiment 的 `Request:{Extension:string,FileSize:integer}` 和 Data.Token 中的 Policy、Authorization。旧网页流程会先 Confirm，再 Submit，上传后再次 Confirm，并存在负 FileSize 及 .jpg/.png 混用；不能把这些特殊形式推广成稳定的通用上传协议。需要上传时，先核对网页的完整协议，不自行补齐未知字段。

网页文件上传地址：`POST https://v0.api.upyun.com/qphysics`，multipart字段为 `authorization`、`policy`、`file`；只使用针对目标对象正常取得的上传凭据，不转发账号Token。

网页静态资源基址：`https://physics-lab.oss-cn-hongkong.aliyuncs.com`。

- 头像：`/users/avatars/{ID[0:4]}/{ID[4:6]}/{ID[6:8]}/{ID[8:24]}/{序号}.jpg{后缀}`。
- 封面：`/experiments/images/{ID[0:4]}/{ID[4:6]}/{ID[6:8]}/{ID[8:24]}/{序号}.jpg{后缀}`。
- 后缀可为空；网页网络策略还使用 `!block`、`!tiny.round`、`!small.round`。
- 序号、ImageRegion、AvatarRegion以服务端对象为准；图像不存在或区域不匹配时不猜测大量地址。保持TLS验证开启。

## 按名称找用户或作品

支持GetUser(Name)精确昵称定位与关系范围精确筛选，未确认全站模糊昵称或作品标题搜索接口。先按链接/ID定位，或缩小已知作者、分类、标签和时间范围，按时间取回候选后本地匹配，再按 ID 核验。完整步骤、同名处理和停止条件见 [分页与查找目标](finding.md)。

## 11. 技能辅助接口

fetch_comments / fetch_works 自动循环取得指定数量，并支持多个目标/作者 ID；get_available_tags 实时读取完整标签配置。read_community/write_community 兼容 body 或多个 bodies。全部按两个并发、每批评论1000条/作品或用户20个执行，超限拒绝。工具不是新增社区端点，具体参数和通用版 Python 用法见 [自动分页与批量接口](operations.md)。

本地生成实验及官方客户端授权发布见 [实验建模与发布](experiments.md)。不使用 physicslab 网络模块，既有 SubmitExperiment 编辑协议不等于新建模型/上传协议已经核实。

## 12. 大实验输出边界

插件读取 GetExperiment 默认返回 inspect_experiments 的有界概览与私人归档引用，不再内联原始 Data/StatusSave。用 read_experiment_page 按集合、offset、limit（最多20）和 fields 取片段；这属于文件切片，不是社区 Skip 分页。通用版用 CommunityReads.inspect_experiments 与 experiment_view.py。完整数据留在文件/代码进程中，详见 [大实验概览与分页](large-experiments.md)。
