# 社区/资料页接口详解

社区接口提供社区首页、讨论区、实验区导航内容，以及用户资料页展示数据。所有接口均需认证。

## 1. 获取社区库（Contents/GetLibrary）

获取社区各板块的导航与结构内容，是社区浏览的入口接口。

### 请求

```http
POST /Contents/GetLibrary
```

**请求体：**
```json
{
  "Identifier": "Homepage",
  "Language": "Chinese"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `Identifier` | string | 板块标识符 |
| `Language` | string | `"Chinese"` 或 `"English"` |

### Identifier 取值

| 值 | 说明 |
|----|------|
| `"Homepage"` | 社区首页 |
| `"Discussions"` | 讨论区 |
| `"Experiments"` | 实验区 |

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": {
    "Identifier": "Discussions",
    "Language": "Chinese",
    "Categories": {
      "$values": [
        {
          "Name": "板块名称",
          "Identifier": "板块标识符",
          "Tags": { "$values": ["标签1", "标签2"] }
        }
      ]
    },
    "Announcements": { "$values": [ ... ] }
  }
}
```

### Library 字段说明

| 字段 | 说明 |
|------|------|
| `Data.Identifier` | 当前板块标识符 |
| `Data.Language` | 语言 |
| `Data.Categories` | 板块下的分类列表 |
| `Data.Announcements` | 公告列表 |

## 2. 获取用户资料页（Contents/GetProfile）

获取用户主页的展示数据，包括该用户的精选/热门/最新作品。

### 请求

```http
POST /Contents/GetProfile
```

**请求体：**
```json
{
  "ID": "5d0f4390ca68215906d1a0fd"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ID` | string | 用户 ID |

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": {
    "Experiments": {
      "Featured-Discussions": [],
      "Popular-Discussions": [],
      "Latest-Discussions": [],
      "Featured-Experiments": [],
      "Popular-Experiments": [],
      "Latest-Experiments": []
    },
    "Survey": null
  }
}
```

### Experiments 字段说明

`Data.Experiments` 包含六个分类列表，每个列表为 `ExperimentSummary` 数组：

| 字段 | 说明 |
|------|------|
| `Featured-Discussions` | 精选讨论 |
| `Popular-Discussions` | 热门讨论 |
| `Latest-Discussions` | 最新讨论 |
| `Featured-Experiments` | 精选实验 |
| `Popular-Experiments` | 热门实验 |
| `Latest-Experiments` | 最新实验 |

每个列表中的元素结构与 `QueryExperiments` 返回的 `ExperimentSummary` 相同。

## 3. 获取社区首页（GET /Users）

获取社区首页的初始化数据，无需认证（匿名可访问）。

### 请求

```http
GET /Users
```

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": {
    "Version": "2.4.11",
    "Announcement": "公告内容",
    "Homepage": { ... },
    "Library": { ... }
  }
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `Data.Version` | 当前服务器版本 |
| `Data.Announcement` | 全站公告 |
| `Data.Homepage` | 首页内容 |
| `Data.Library` | 社区库结构 |

## 4. 获取讨论区帖子（Contents/GetDiscussion）

获取讨论区帖子的完整内容。

### 请求

```http
POST /Contents/GetDiscussion
```

**请求体：**
```json
{
  "ContentID": "discussion_content_id"
}
```

### 响应

返回讨论帖的完整内容，包括标题、正文、作者、评论数等信息。

## 5. 获取公告（Contents/GetAnnouncement）

获取指定公告的详细内容。

### 请求

```http
POST /Contents/GetAnnouncement
```

**请求体：**
```json
{
  "ID": "announcement_id_string"
}
```

### 响应

返回公告的标题、内容、发布时间等信息。

## 6. 获取通知消息（Notifications/Get）

获取当前用户的通知消息列表（与站内信不同，通知为系统推送的活动通知）。

### 请求

```http
POST /Notifications/Get
```

**请求体：**
```json
{
  "Skip": 0,
  "Take": 16
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `Skip` | int | 跳过条数 |
| `Take` | int | 获取条数 |

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": {
    "$values": [
      {
        "ID": "notification_id",
        "Title": "通知标题",
        "Content": "通知内容",
        "SendDate": "2024-01-01T00:00:00Z",
        "IsRead": false,
        "Category": "活动"
      }
    ]
  }
}
```
