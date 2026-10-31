# 快速入门：读取 Physics Lab 社区数据

本例使用 Python 3 和 `requests`，演示匿名/账号登录、响应检查和分页查询。原版字段参考physics-lab-turtle-services后端，但该源码未随仓库提供。以下示例演示匿名读取；账号登录用随附简单窗口和安全会话，见 [安全登录](local-login.md)。遇字段错误以当前响应核验，不盲目重试。

## 1. 准备

```powershell
py -m pip install requests
$env:PL_API_DOMAIN = 'physics-api-cn.turtlesim.com'
$env:PL_API_VERSION = '2609' # 改成实际客户端版本
# 账号模式：先运行 python scripts/login_gui.py，再用community_cli.py --account 用户ID调用。
# 不在命令行、聊天或脚本中输入真实密码。
```

中国区使用 `physics-api-cn.turtlesim.com`，国际区使用 `physics-api-us.turtlesim.com`。TLS 证书验证默认开启；不要设置 `verify=False`。

## 2. 登录并分页查找作品

保存为 `pl_read.py` 后运行 `py pl_read.py`：

```python
import os
import time
import requests


domain = os.environ.get("PL_API_DOMAIN", "physics-api-cn.turtlesim.com")
base = f"https://{domain}"
version = int(os.environ.get("PL_API_VERSION", "2609"))
session = requests.Session()
session.headers.update({"Content-Type": "application/json"})


def check(response):
    response.raise_for_status()  # 传输层错误（TLS、DNS、HTTP 4xx/5xx）
    payload = response.json()
    if payload.get("Status") != 200:
        raise RuntimeError(
            f"API failed: Status={payload.get('Status')} "
            f"Message={payload.get('Message')}"
        )
    # 服务端可在响应头续发认证字段，收到时更新本地会话。
    for header, key in (("x-API-Token", "x-API-Token"),
                        ("x-API-AuthCode", "x-API-AuthCode")):
        value = response.headers.get(header)
        if value:
            session.headers[key] = value
    return payload


login = {
    "Login": None,
    "Password": None,
    "Version": version,
    "Device": {
        "Identifier": "0d1a760b44023875d2123f2cfcb56dad",
        "Language": "Chinese",
    },
}
auth = check(session.post(f"{base}/Users/Authenticate", json=login, timeout=30))

# Token/AuthCode 在响应顶层。匿名登录可能没有 Token；公开读取可以先试。
if auth.get("Token"):
    session.headers["x-API-Token"] = auth["Token"]
if auth.get("AuthCode"):
    session.headers["x-API-AuthCode"] = auth["AuthCode"]


def as_items(data):
    """兼容 Newtonsoft 的 $values 包装和直接数组。"""
    if isinstance(data, dict) and "$values" in data:
        return data["$values"]
    if isinstance(data, list):
        return data
    return []


cursor = None
seen = set()
remaining = 20  # 本批最多20个作品，不自行拆批绕过
for _ in range(40):
    if remaining == 0:
        break
    take = min(20, max(2, remaining + 1))
    time.sleep(0.4)
    query = {
        "Category": "Experiment",
        "Languages": [],
        "ExcludeLanguages": [],
        "Tags": None,
        "ExcludeTags": None,
        "ModelTags": None,
        "ModelID": None,
        "ParentID": None,
        "UserID": None,
        "Special": None,
        "From": cursor,
        "Skip": 0,
        "Take": take,
        "Days": 0,
        "Sort": 0,
        "ShowAnnouncement": False,
    }
    result = check(session.post(
        f"{base}/Contents/QueryExperiments",
        json={"Query": query},
        timeout=30,
    ))
    rows = as_items(result.get("Data"))
    before = len(seen)
    for row in rows:
        identifier = row.get("ID")
        if not identifier or identifier in seen:
            continue
        seen.add(identifier)
        cursor = identifier
        print(identifier, row.get("Subject"), (row.get("User") or {}).get("Nickname"))
        remaining -= 1
        if remaining == 0:
            break
    if len(seen) == before:
        break
print({"returned": len(seen), "complete": remaining == 0, "nextCursor": cursor})
```

匿名登录的实际行为受设备字段和服务端策略影响。账号权限任务使用login_gui.py和已保存会话，不让AI观察输入。不要输出整个登录响应。此处有界循环与辅助脚本使用同一游标原则，生产任务优先使用CommunityReads。

## 3. 读取单个作品

`QueryExperiments` 的每个摘要有两个容易混淆的 ID：`ID` 是社区作品摘要 ID；`ContentID` 是关联的实验保存 ID。`GetSummary` 请求体的字段虽然也叫 `ContentID`，这里应传摘要的 `ID` 并同时传 `Category`；`GetExperiment` 的 `ContentID` 则传摘要对象中的保存 ID。

```python
payload = check(session.post(
    f"{base}/Contents/GetSummary",
    json={"Category": "Experiment", "ContentID": "<summary-ID>"},
    timeout=30,
))
print({"id": payload["Data"].get("ID"), "subject": payload["Data"].get("Subject")})

payload = check(session.post(
    f"{base}/Contents/GetExperiment",
    json={"ContentID": "<summary.ContentID-save-ID>"},
    timeout=30,
))
# 完整响应仅保留在进程或私人文件，不能打印StatusSave。
import sys
sys.path.insert(0, "scripts")
from experiment_view import overview
print(overview(payload))
```

完整实验保存结构可能很大；响应 `Data` 字段说明见 [`responses.md`](responses.md#43-完整保存-contentsgetexperiment)。读取失败时先核对 ID 类型、作品可见性和当前区域。对不可见或不存在的 ID，不要通过重复请求猜测其他对象。

## 4. 认证与失败排查

- `Status` 非 200：按 `Message` 分支处理；`Login.Password.Invalid` 检查账号密码，`Login.Expired` 重新登录，`Permission.Denied`/`User.Not.Allowed` 检查权限。
- `Input.Field.Missing` 或字段校验错误：检查 JSON 嵌套层级与必填字段。`QueryExperiments` 的查询对象放在外层 `Query` 属性中。
- HTTP/TLS 错误：检查区域域名、网络和系统证书。保持 TLS 验证，不用 `-k` 或 `verify=False`。
- 遇到429/503停止当前批次和未开始请求，不自动重试；写请求超时先核验状态，避免重复发布/评论。
- 列表可能是数组，也可能是 `{ "$type": ..., "$values": [...] }`；解析时兼容两种形状。

## 5. 常用真实路由

原有接口范围继续保留；公共仓库不含父目录后端，具体字段按文档、可访问客户端调用及真实响应核验：`Users/Authenticate`、`Users/GetUser`、`Users/GetRelations`、`Contents/QueryExperiments`、`Contents/GetSummary`、`Contents/GetExperiment`、`Contents/GetDerivatives`、`Contents/StarContent`、`Contents/SubmitExperiment`、`Contents/RemoveExperiment`、`Messages/GetComments`、`Messages/PostComment`、`Messages/RemoveComment`、`Messages/GetMessages`、`Messages/GetMessage`、`Messages/SendMessages`。写接口的请求体和副作用应先阅读对应控制器实现及本 skill 的专题文档。
