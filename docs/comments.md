# 评论接口详解

评论接口位于 `Contents/` 路径下，提供对实验/讨论作品的评论发表、获取、删除功能。所有接口均需认证。

## 1. 获取评论列表（Contents/GetComments）

获取指定作品的评论列表。

### 请求

```http
POST /Contents/GetComments
```

**请求体：**
```json
{
  "ContentID": "16a627bdb25f77131ba28018",
  "Category": "Experiment",
  "Skip": 0,
  "Take": 16
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ContentID` | string | 内容 ID |
| `Category` | string | `"Experiment"` 或 `"Discussion"` |
| `Skip` | int | 跳过条数（分页偏移） |
| `Take` | int | 获取条数（默认 16） |

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": {
    "$type": "...",
    "$values": [
      {
        "ID": "comment_id_string",
        "ContentID": "16a627bdb25f77131ba28018",
        "Content": "评论内容文本",
        "Author": {
          "ID": "...",
          "Nickname": "评论者昵称",
          "Avatar": 0,
          "AvatarRegion": 0,
          "Level": 1
        },
        "SendDate": "2024-01-01T00:00:00Z",
        "Floor": 1,
        "IsEdited": false
      }
    ]
  }
}
```

> 列表数据在 `Data["$values"]` 数组中。

### Comment 字段说明

| 字段 | 说明 |
|------|------|
| `ID` | 评论唯一 ID |
| `ContentID` | 所属内容 ID |
| `Content` | 评论正文 |
| `Author` | 评论者信息 |
| `SendDate` | 评论时间（ISO 8601） |
| `Floor` | 楼层号 |
| `IsEdited` | 是否被编辑过 |

## 2. 发表评论（Contents/PostComment）

在指定作品或用户留言板下发表评论。

### 请求

```http
POST /Contents/PostComment
```

**请求体：**
```json
{
  "ContentID": "16a627bdb25f77131ba28018",
  "Category": "Experiment",
  "Content": "评论内容文本"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ContentID` | string | 内容 ID |
| `Category` | string | `"Experiment"` 或 `"Discussion"` 或 `"User"` |
| `Content` | string | 评论内容（纯文本） |

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": {
    "ID": "new_comment_id",
    "ContentID": "16a627bdb25f77131ba28018",
    "Content": "评论内容文本",
    "Author": { ... },
    "SendDate": "2024-01-01T00:00:00Z",
    "Floor": 2
  }
}
```

### 注意事项

- 评论内容不能为空
- 评论内容有长度限制
- 匿名用户无法发表评论
- 被作者拉黑后可能无法评论

## 3. 删除评论（Contents/RemoveComment）

删除指定评论。仅评论作者或内容作者或管理员可删除。

### 请求

```http
POST /Contents/RemoveComment
```

**请求体：**
```json
{
  "ContentID": "16a627bdb25f77131ba28018",
  "Category": "Experiment",
  "CommentID": "comment_id_string"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ContentID` | string | 内容 ID |
| `Category` | string | `"Experiment"` 或 `"Discussion"` 或 `"User"` |
| `CommentID` | string | 要删除的评论 ID |

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": null
}
```

### 权限说明

- 评论作者可以删除自己的评论
- 内容（实验/讨论）作者可以删除其作品下的任何评论
- 管理员可以删除任何评论
- 无权限删除会返回 `Permission.Denied` 错误

## 4. 获取讨论区评论（Contents/GetDiscussionComments）已废弃

获取讨论区帖子的评论列表，与 `GetComments` 类似但专用于讨论区。

### 请求

```http
POST /Contents/GetDiscussionComments
```

**请求体：**
```json
{
  "ContentID": "discussion_content_id",
  "Skip": 0,
  "Take": 16
}
```

> 注意：讨论区评论接口不需要 `Category` 字段。
