# 用户接口详解

用户接口位于 `Users/` 路径下，提供用户资料查询、关注关系管理、个人信息修改、管理员操作等功能。

所有接口（除 `Authenticate` 外）均需在请求头中携带 `x-API-Token` 和 `x-API-AuthCode`。

## 1. 获取用户信息（Users/GetUser）

按用户名或用户 ID 查询用户资料。

### 请求

```http
POST /Users/GetUser
```

**请求体（按用户名查询）：**
```json
{
  "Name": "用户昵称"
}
```

**请求体（按用户 ID 查询）：**
```json
{
  "ID": "5d0f4390ca68215906d1a0fd"
}
```

> 两个字段二选一，同时提供时以 `Name` 为准。

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": {
    "User": {
      "ID": "5d0f4390ca68215906d1a0fd",
      "Nickname": "test",
      "Signature": null,
      "Verification": null,
      "Avatar": 0,
      "AvatarRegion": 0,
      "Decoration": 0,
      "Gold": 350,
      "Diamond": 0,
      "Fragment": 0,
      "Level": 1,
      "Experience": 0,
      "Prestige": 0
    },
    "Statistic": {
      "ExperimentCount": 0,
      "FollowerCount": 0,
      "FollowingCount": 0
    },
    "Backpack": { ... },
    "Bonuses": [ ... ],
    "UserToken": null,
    "Relation": null,
    "TargetLink": null
  }
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `Data.User` | 用户基本信息 |
| `Data.Statistic` | 用户统计数据（作品数、粉丝数、关注数） |
| `Data.Backpack` | 背包物品 |
| `Data.Bonuses` | 奖励列表 |
| `Data.Relation` | 当前登录用户与目标用户的关系（是否已关注等） |

## 2. 关注/取关用户（Users/Follow）

关注或取消关注指定用户。

### 请求

```http
POST /Users/Follow
```

**请求体：**
```json
{
  "TargetID": "5d0f4390ca68215906d1a0fd",
  "Action": 1
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `TargetID` | string | 目标用户 ID |
| `Action` | int | `1` 关注，`0` 取消关注 |

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": null
}
```

## 3. 获取关注/粉丝列表（Users/GetRelations）

获取指定用户的关注列表或粉丝列表。

### 请求

```http
POST /Users/GetRelations
```

**请求体：**
```json
{
  "UserID": "5d0f4390ca68215906d1a0fd",
  "DisplayType": "Follower",
  "Skip": 0,
  "Take": 20,
  "Query": ""
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `UserID` | string | 目标用户 ID |
| `DisplayType` | string | `"Follower"` 粉丝列表，`"Following"` 关注列表 |
| `Skip` | int | 跳过条数（分页） |
| `Take` | int | 获取条数（默认 20） |
| `Query` | string | 搜索关键词（可为空字符串） |

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": {
    "$type": "...",
    "$values": [
      {
        "ID": "...",
        "Nickname": "...",
        "Avatar": 0,
        "AvatarRegion": 0,
        "Level": 1
      }
    ]
  }
}
```

## 4. 修改昵称（Users/Rename）

修改当前登录用户的昵称。

### 请求

```http
POST /Users/Rename
```

**请求体：**
```json
{
  "Nickname": "新昵称"
}
```

### 响应

成功返回 `Status: 200`，`Data` 为更新后的用户信息。

## 5. 修改个人信息（Users/ModifyInformation）

修改当前用户的个人签名等信息。

### 请求

```http
POST /Users/ModifyInformation
```

**请求体：**
```json
{
  "Target": "新的个性签名内容"
}
```

## 6. 领取活动奖励（Users/ReceiveBonus）

领取指定活动的奖励。

### 请求

```http
POST /Users/ReceiveBonus
```

**请求体：**
```json
{
  "ActivityID": "activity_id_string",
  "Index": 0
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ActivityID` | string | 活动 ID |
| `Index` | int | 奖励索引 |

## 7. 封禁用户（Users/Ban）— 管理员

封禁指定用户，需要管理员权限。

### 请求

```http
POST /Users/Ban
```

**请求体：**
```json
{
  "TargetID": "5d0f4390ca68215906d1a0fd",
  "Reason": "违规原因",
  "Length": 7
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `TargetID` | string | 被封禁用户 ID |
| `Reason` | string | 封禁原因 |
| `Length` | int | 封禁天数（必须大于 0） |

## 8. 解封用户（Users/Unban）— 管理员

解封指定用户，需要管理员权限。

### 请求

```http
POST /Users/Unban
```

**请求体：**
```json
{
  "TargetID": "5d0f4390ca68215906d1a0fd",
  "Reason": "解封原因"
}
```

## 9. 获取头像图片

获取用户头像或实验封面图片，无需认证。

### 请求

```http
GET https://physics-api-cn.turtlesim.com/Avatars/{category}/{target_id}_{index}_{size_category}.png
```

| 参数 | 说明 |
|------|------|
| `category` | `"users"` 用户头像，`"experiments"` 实验封面 |
| `target_id` | 用户 ID 或实验 ID |
| `index` | 历史图片索引（通常为 0） |
| `size_category` | `"small.round"` 小圆头像，`"thumbnail"` 缩略图，`"full"` 完整图 |

### 示例

```
https://physics-api-cn.turtlesim.com/Avatars/users/5d0f4390ca68215906d1a0fd_0_small.round.png
```

> 由于证书与域名不匹配，获取图片时需关闭 SSL 验证。
