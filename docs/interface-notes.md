# 接口线索与协议边界

这些路径出现在正常社区客户端中，但参数或完整副作用没有可靠说明。它们用于后续查找客户端调用，不是可直接执行的请求模板。

| 路径 | 功能线索 | 使用前需要确认 |
|---|---|---|
| `/Contents/AcknowledgeExperiment` | 作品确认或处理 | 请求字段、动作语义、状态副作用 |
| `/Contents/SelectExperiment` | 作品选择或管理 | 是否改变精选/分类，如何撤销，角色要求 |
| `/Contents/VisitExperiment` | 访问记录 | 请求字段和计数副作用 |
| `/Contents/InviteCoauthor` | 邀请合作者 | 目标用户、作品字段及邀请状态 |
| `/Contents/RemoveCoauthor` | 移除合作者 | 权限、字段及对方创作权限变化 |
| `/Messages/HandleInvitation` | 处理通知邀请 | 邀请ID、接受/拒绝字段、权限变化 |
| `/Users/RequestAvatar` | 请求头像上传 | 请求元数据、上传凭据及目标索引 |
| `/Users/ConfirmAvatar` | 确认头像 | 文件上传和确认的完整协议 |

不得只根据类似接口猜字段，不将账号身份字段、前端菜单可见性或本地客户端修改作为授权手段。

## 图片协议边界

`SubmitExperiment`、`ConfirmExperiment` 和又拍云上传可组成图片流程，但网页存在特殊的负文件大小、扩展名和调用顺序。仅知道接口名称不足以构造新图上传，先核对完整调用链；不要覆盖原图后再声称已恢复。

## 参考实现

- [网页客户端](https://github.com/NetLogo-Mobile/plweb2/tree/85ca269a6e1bf1ecc353882f0e38217a2b0c24be/src)。
- physicslab仅参考本地建模模块，见 [实验建模](experiments.md)；本阶段不参考其网络模块。

不要使用physicslab网络封装补齐未知请求；历史字段解释、分页和异常处理可能失效。原生客户端可提供更多正常业务路径，但字符串存在不证明参数、权限或服务端兼容性。
