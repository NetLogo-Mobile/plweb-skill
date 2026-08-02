# 内容/实验接口详解

内容接口位于 `Contents/` 路径下，提供实验/讨论的查询、获取、发布、删除、点赞、衍生作品查询等功能。所有接口均需认证。

## 1. 查询实验列表（Contents/QueryExperiments）

按多条件搜索实验或讨论作品，是最核心的列表查询接口。

### 请求

```http
POST /Contents/QueryExperiments
```

**请求体：**
```json
{
  "Query": {
    "Category": "Experiment",
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
    "Take": 16,
    "Days": 0,
    "Sort": 0,
    "ShowAnnouncement": false
  }
}
```

### Query 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `Category` | string | `"Experiment"` 实验区，`"Discussion"` 讨论区 |
| `Languages` | array | 筛选语言列表（空数组表示不限） |
| `ExcludeLanguages` | array | 排除语言列表 |
| `Tags` | array/null | 筛选标签列表（如 `["精选"]`） |
| `ExcludeTags` | array/null | 排除标签列表 |
| `ModelTags` | array/null | 模型标签筛选 |
| `ModelID` | string/null | 筛选特定模型 ID |
| `ParentID` | string/null | 筛选特定父作品 ID（获取衍生作品时用） |
| `UserID` | string/null | 筛选特定用户的作品 |
| `Special` | string/null | 特殊筛选 |
| `From` | string/null | 起始内容 ID（游标分页） |
| `Skip` | int | 跳过条数（偏移分页） |
| `Take` | int | 获取条数（默认 16） |
| `Days` | int | 时间范围（天数，0 表示不限） |
| `Sort` | int | 排序方式：`0` 最新，`1` 最热 |
| `ShowAnnouncement` | bool | 是否显示公告 |

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": {
    "$type": "Quantum.Models.Contents.ExperimentSummary[], Quantum Models",
    "$values": [
      {
        "Type": 0,
        "ParentID": null,
        "ParentName": null,
        "ParentCategory": null,
        "ContentID": "16a627bdb25f77131ba28018",
        "Editor": null,
        "Coauthors": [],
        "Description": ["前言", "", "正文内容..."],
        "Title": "实验标题",
        "Author": {
          "ID": "...",
          "Nickname": "作者昵称"
        },
        "Tags": ["精选"],
        "Languages": ["Chinese"],
        "Summary": "实验摘要",
        "Thumbnail": "...",
        "Stars": 100,
        "Comments": 10,
        "Derivatives": 5,
        "PublishDate": "2024-01-01T00:00:00Z",
        "UpdateDate": "2024-01-02T00:00:00Z"
      }
    ]
  }
}
```

> **重要**：列表数据在 `Data["$values"]` 数组中，不是直接在 `Data` 中。

### ExperimentSummary 字段说明

| 字段 | 说明 |
|------|------|
| `ContentID` | 内容唯一 ID（后续获取详情用） |
| `Title` | 作品标题 |
| `Description` | 描述内容数组 |
| `Author` | 作者信息（ID、Nickname） |
| `Tags` | 标签列表 |
| `Summary` | 摘要文本 |
| `Stars` | 点赞数 |
| `Comments` | 评论数 |
| `Derivatives` | 衍生作品数 |
| `PublishDate` | 发布时间 |
| `UpdateDate` | 更新时间 |
| `ParentID` | 父作品 ID（如果是衍生作品） |

## 2. 获取实验详情（Contents/GetExperiment）

获取实验的完整内容数据，包括电路/天体物理模型。

### 请求

```http
POST /Contents/GetExperiment
```

**请求体：**
```json
{
  "ContentID": "16a627bdb25f77131ba28018"
}
```

> 如果传入的是实验 ID（而非 ContentID），需同时提供 `Category` 字段，接口会先查询摘要获取 ContentID。

### 响应

```json
{
  "Status": 200,
  "Message": "",
  "Data": {
    "ContentID": "16a627bdb25f77131ba28018",
    "Title": "实验标题",
    "Content": "{ ... 序列化的实验模型 JSON ... }",
    "Type": 0,
    "Version": "..."
  }
}
```

`Data.Content` 是序列化的实验模型字符串，包含电路元件、连接关系、参数等完整信息。修改实验内容时需解析并保留原有结构。

## 3. 获取实验摘要（Contents/GetSummary）

获取实验的摘要信息，比列表返回的更详细。

### 请求

```http
POST /Contents/GetSummary
```

**请求体：**
```json
{
  "ContentID": "16a627bdb25f77131ba28018",
  "Category": "Experiment"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ContentID` | string | 内容 ID |
| `Category` | string | `"Experiment"` 或 `"Discussion"` |

### 响应

返回该内容的详细摘要信息，包括标题、描述、作者、标签、统计数据等。

## 4. 获取衍生作品（Contents/GetDerivatives）

获取指定作品的改编/衍生作品列表。

### 请求

```http
POST /Contents/GetDerivatives
```

**请求体：**
```json
{
  "ContentID": "16a627bdb25f77131ba28018",
  "Category": "Experiment"
}
```

### 响应

返回衍生作品列表，结构与 `QueryExperiments` 的 `Data["$values"]` 相同。

## 5. 获取支持者列表（Contents/GetSupporters）

获取为指定作品点赞/支持的用户列表。

### 请求

```http
POST /Contents/GetSupporters
```

**请求体：**
```json
{
  "ContentID": "16a627bdb25f77131ba28018",
  "Category": "Experiment",
  "Skip": 0,
  "Take": 10
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ContentID` | string | 内容 ID（必填） |
| `Category` | string | `"Experiment"` 或 `"Discussion"` |
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
        "ID": "...",
        "Nickname": "支持者昵称",
        "Avatar": 0,
        "Level": 1
      }
    ]
  }
}
```

## 6. 点赞/取消点赞（Contents/Star）

为指定作品点赞或取消点赞。

### 请求

```http
POST /Contents/Star
```

**请求体：**
```json
{
  "ContentID": "16a627bdb25f77131ba28018",
  "Category": "Experiment",
  "Action": 1
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ContentID` | string | 内容 ID |
| `Category` | string | `"Experiment"` 或 `"Discussion"` |
| `Action` | int | `1` 点赞，`0` 取消点赞 |

## 7. 确认发布实验（Contents/ConfirmExperiment）

确认实验发布，为底层接口，通常配合 `UploadImage` 使用。

### 请求

```http
POST /Contents/ConfirmExperiment
```

**请求体：**
```json
{
  "SummaryID": "summary_id_string",
  "Category": "Experiment",
  "ImageCounter": 0
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `SummaryID` | string | 摘要 ID |
| `Category` | string | `"Experiment"` 或 `"Discussion"` |
| `ImageCounter` | int | 图片计数器 |

## 8. 删除实验（Contents/RemoveExperiment）

删除已发布的实验作品。

### 请求

```http
POST /Contents/RemoveExperiment
```

**请求体：**
```json
{
  "ContentID": "16a627bdb25f77131ba28018",
  "Category": "Experiment"
}
```

## 9. 上传图片（Contents/UploadImage）

上传实验封面或内容图片。

### 请求

```http
POST /Contents/UploadImage
```

**请求体：**
```json
{
  "ContentID": "16a627bdb25f77131ba28018",
  "Category": "Experiment",
  "Image": "base64编码的图片数据",
  "Index": 0
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ContentID` | string | 内容 ID |
| `Category` | string | `"Experiment"` 或 `"Discussion"` |
| `Image` | string | Base64 编码的图片数据 |
| `Index` | int | 图片索引 |

## 10. 获取用户资料页（Contents/GetProfile）

获取用户主页的展示内容，包括精选作品、热门作品、最新作品等。

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

`Data.Experiments` 包含六个分类列表：精选讨论、热门讨论、最新讨论、精选实验、热门实验、最新实验。

## 11. 获取社区库内容（Contents/GetLibrary）

获取社区首页、讨论区、实验区等导航与板块内容。

### 请求

```http
POST /Contents/GetLibrary
```

**请求体：**
```json
{
  "Identifier": "Discussions",
  "Language": "Chinese"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `Identifier` | string | `"Homepage"` 首页，`"Discussions"` 讨论区，`"Experiments"` 实验区 ,`Workspace` 工作区 |
| `Language` | string | `"Chinese"` 或 `"English"` |

### 响应

返回社区库的板块结构，包含导航分类、板块列表等信息。
