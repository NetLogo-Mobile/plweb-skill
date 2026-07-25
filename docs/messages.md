# 消息接口详解

消息接口位于 `Messages/` 路径下，提供站内信的获取与发送功能。所有接口均需认证。

## 1. 获取站内信列表（Messages/GetMessages）

获取当前用户的站内信列表，支持按分类筛选和分页。

### 请求

```http
POST /Messages/GetMessages
```

**请求体：**
```json
{
  "CategoryID": 0,
  "Skip": 0,
  "Take": 16,
  "NoTemplates": true
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `CategoryID` | int | 消息分类 ID，`0` 表示全部 |
| `Skip` | int | 跳过条数（分页偏移） |
| `Take` | int | 获取条数（默认 16） |
| `NoTemplates` | bool | 是否排除模板消息（系统通知模板） |

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": {
    "$type": "...",
    "$values": [
      {
        "ID": "message_id_string",
        "CategoryID": 1,
        "Category": "评论",
        "Title": "消息标题",
        "Content": "消息内容",
        "Sender": {
          "ID": "...",
          "Nickname": "发送者昵称"
        },
        "Receiver": {
          "ID": "...",
          "Nickname": "接收者昵称"
        },
        "SendDate": "2024-01-01T00:00:00Z",
        "IsRead": false,
        "IsSystem": false
      }
    ]
  }
}
```

> 列表数据在 `Data["$values"]` 数组中。

### Message 字段说明

| 字段 | 说明 |
|------|------|
| `ID` | 消息唯一 ID |
| `CategoryID` | 消息分类 ID |
| `Category` | 消息分类名称 |
| `Title` | 消息标题 |
| `Content` | 消息正文内容 |
| `Sender` | 发送者信息（ID、Nickname） |
| `Receiver` | 接收者信息 |
| `SendDate` | 发送时间（ISO 8601） |
| `IsRead` | 是否已读 |
| `IsSystem` | 是否为系统消息 |

## 2. 获取单条站内信（Messages/GetMessage）

获取指定 ID 的单条站内信详情。

### 请求

```http
POST /Messages/GetMessage
```

**请求体：**
```json
{
  "ID": "message_id_string"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ID` | string | 消息 ID |

### 响应

返回单条消息的完整信息，结构与列表中的单个消息对象相同。

## 3. 发送站内信（Messages/SendMessage）

向指定用户发送站内信。

### 请求

```http
POST /Messages/SendMessage
```

**请求体：**
```json
{
  "ReceiverID": "5d0f4390ca68215906d1a0fd",
  "Content": "消息内容文本"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ReceiverID` | string | 接收者用户 ID |
| `Content` | string | 消息内容（纯文本） |

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": null
}
```

### 注意事项

- 不能给自己发送站内信
- 消息内容有长度限制
- 被对方拉黑后可能无法发送
- 频繁发送可能触发频率限制
