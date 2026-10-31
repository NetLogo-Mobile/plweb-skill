# 完整代码示例

以下是使用 Python、Node.js 和 curl 调用物理实验室 AR API 的完整示例。

## Python 示例

### 完整 API 客户端类

```python
import json
import urllib.request
import threading
import time

# 从仓库根目录运行；作为其他项目依赖时将scripts加入模块路径。
import sys
sys.path.insert(0, "scripts")
from community_client import redact, CommunityError


class PhysicsLabAPI:
    """物理实验室 AR 社区 API 客户端"""

    DOMAIN = "physics-api-cn.turtlesim.com"

    def __init__(self):
        self.token = None
        self.auth_code = None
        self.user_id = None
        self._lock = threading.RLock()
        self._next_start = 0.0

    def _post(self, path, body, need_auth=True):
        """发送 POST 请求；不向调用者返回凭据。账号常规使用login_gui.py。"""
        url = f"https://{self.DOMAIN}/{path}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.headers = {"Content-Type": "application/json", "x-API-Version": "2502"}
        # 多线程时串行发送并更新凭据，不自动重试。
        with self._lock:
            if need_auth:
                req.headers["x-API-Token"] = self.token or ""
                req.headers["x-API-AuthCode"] = self.auth_code or ""
            time.sleep(max(0, self._next_start - time.monotonic()))
            self._next_start = time.monotonic() + 0.35
            # 禁止重定向，防止认证头转发到其他主机。
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as resp:
                if resp.info().get("Content-Encoding") == "gzip":
                    import gzip
                    content = gzip.decompress(resp.read())
                else:
                    content = resp.read()
                result = json.loads(content)
                if result.get("Status") != 200:
                    raise CommunityError(result.get("Status"), "business_error", code=result.get("Message"), data=result.get("Data"), http_status=resp.status)
                if path == "Users/Authenticate":
                    self.token = result.get("Token")
                    self.auth_code = result.get("AuthCode")
                self.token = resp.headers.get("x-API-Token") or self.token
                self.auth_code = resp.headers.get("x-API-AuthCode") or self.auth_code
                return redact(result)

    def _get(self, path):
        """发送 GET 请求"""
        url = f"https://{self.DOMAIN}/{path}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    # ========== 登录 ==========

    def login(self, email, password, version):
        """邮箱登录"""
        body = {
            "Login": email,
            "Password": password,
            "Version": version,
            "Device": {
                "Identifier": "7db01528cf13e2199e141c402d79190e",
                "Language": "Chinese",
            },
        }
        result = self._post("Users/Authenticate", body, need_auth=False)
        if result.get("Status") == 200:
            self.user_id = result["Data"]["User"]["ID"]
        return result

    def anonymous_login(self, version):
        """匿名登录"""
        body = {
            "Login": None,
            "Password": None,
            "Version": version,
            "Device": {
                "Identifier": "7db01528cf13e2199e141c402d79190e",
                "Language": "Chinese",
            },
        }
        result = self._post("Users/Authenticate", body, need_auth=False)
        if result.get("Status") == 200:
            self.user_id = result["Data"]["User"]["ID"]
        return result

    # ========== 用户 ==========

    def get_user(self, name=None, user_id=None):
        """获取用户信息"""
        body = {}
        if user_id:
            body["ID"] = user_id
        elif name:
            body["Name"] = name
        return self._post("Users/GetUser", body)

    def get_profile(self, user_id):
        """获取用户资料页"""
        return self._post("Contents/GetProfile", {"ID": user_id})

    def follow(self, target_id, follow=True):
        """关注/取关用户"""
        return self._post("Users/Follow", {
            "TargetID": target_id,
            "Action": 1 if follow else 0,
        })

    def get_relations(self, user_id, display_type=0, skip=0, take=20):
        """获取粉丝/关注列表"""
        if isinstance(display_type, bool) or not isinstance(display_type, int):
            raise ValueError("DisplayType must be an integer; strings may silently select fans")
        if isinstance(take, bool) or not isinstance(take, int) or not 1 <= take <= 20:
            raise ValueError("A user batch supports Take 1..20")
        return self._post("Users/GetRelations", {
            "UserID": user_id,
            "DisplayType": display_type,
            "Skip": skip,
            "Take": take,
            "Query": "",
        })

    # ========== 内容/实验 ==========

    def query_experiments(self, category="Experiment", skip=0, take=16, sort=0,
                          tags=None, user_id=None, cursor=None):
        """查询实验列表；续页用末条ID游标，不能递增Skip。"""
        if skip != 0 or not 1 <= take <= 20:
            raise ValueError("Use Skip=0, From cursor and Take 1..20")
        query = {
            "Category": category,
            "Languages": [],
            "ExcludeLanguages": [],
            "Tags": tags,
            "ExcludeTags": None,
            "ModelTags": None,
            "ModelID": None,
            "ParentID": None,
            "UserID": user_id,
            "Special": None,
            "From": cursor,
            "Skip": 0,
            "Take": take,
            "Days": 0,
            "Sort": sort,
            "ShowAnnouncement": False,
        }
        return self._post("Contents/QueryExperiments", {"Query": query})

    def get_experiment(self, save_id):
        """获取实验详情"""
        return self._post("Contents/GetExperiment", {"ContentID": save_id})

    def get_summary(self, summary_id, category="Experiment"):
        """获取实验摘要"""
        return self._post("Contents/GetSummary", {
            "ContentID": summary_id,
            "Category": category,
        })

    def get_derivatives(self, summary_id, category="Experiment"):
        """获取衍生作品"""
        return self._post("Contents/GetDerivatives", {
            "ContentID": summary_id,
            "Category": category,
        })

    def get_supporters(self, summary_id, category="Experiment", skip=0, take=10):
        """获取支持者列表"""
        if isinstance(take, bool) or not isinstance(take, int) or not 1 <= take <= 20:
            raise ValueError("A user batch supports Take 1..20")
        return self._post("Contents/GetSupporters", {
            "ContentID": summary_id,
            "Category": category,
            "Skip": skip,
            "Take": take,
        })

    def star(self, summary_id, category="Experiment", star=True):
        """点赞/取消点赞"""
        return self._post("Contents/StarContent", {
            "ContentID": summary_id,
            "Category": category,
            "Status": star,
            "Type": 0,
        })

    def remove_experiment(self, summary_id, category="Experiment"):
        """删除实验"""
        return self._post("Contents/RemoveExperiment", {
            "SummaryID": summary_id,
            "Category": category,
        })

    # ========== 评论 ==========

    def get_comments(self, summary_id, category="Experiment", skip=0, take=16, cursor=None):
        """获取评论列表；边界按ID去重。"""
        if skip != 0 or not 1 <= take <= 1000:
            raise ValueError("Use Skip=0 and CommentID cursor")
        return self._post("Messages/GetComments", {
            "TargetID": summary_id,
            "TargetType": category,
            "CommentID": cursor or "",
            "Skip": 0,
            "Take": take,
        })

    def post_comment(self, summary_id, content, category="Experiment"):
        """发表评论"""
        return self._post("Messages/PostComment", {
            "TargetID": summary_id,
            "TargetType": category,
            "Content": content,
        })

    def remove_comment(self, comment_id, category="Experiment"):
        """删除评论"""
        return self._post("Messages/RemoveComment", {
            "TargetType": category,
            "CommentID": comment_id,
        })

    # ========== 消息 ==========

    def get_messages(self, category_id=0, skip=0, take=16):
        """获取站内信列表"""
        return self._post("Messages/GetMessages", {
            "CategoryID": category_id,
            "Skip": skip,
            "Take": take,
            "NoTemplates": True,
        })

    def send_template_messages(self, target_ids, category, template_id, summary_ids=None):
        """管理员专用批量发送模板消息；不是普通用户自由文本私信。"""
        if not isinstance(target_ids, list) or not target_ids or len(target_ids) > 20:
            raise ValueError("This skill limits each user batch to 20 targets")
        return self._post("Messages/SendMessages", {
            "TargetID": target_ids,
            "Category": category,
            "SummaryID": summary_ids or [],
            "TemplateID": template_id,
        })

    # ========== 社区 ==========

    def get_library(self, identifier="Homepage", language="Chinese"):
        """获取社区库内容"""
        return self._post("Contents/GetLibrary", {
            "Identifier": identifier,
            "Language": language,
        })

    def get_start_page(self):
        """获取社区首页（无需登录）"""
        return self._get("Users")
```

### 使用示例

```python
# 初始化客户端
api = PhysicsLabAPI()

# 匿名登录
result = api.anonymous_login(version=2609)
print(f"登录状态: {result['Status']}, 用户ID: {api.user_id}")

# 查询最新实验
result = api.query_experiments(category="Experiment", skip=0, take=5, sort=0)
data = result["Data"]
experiments = data.get("$values", []) if isinstance(data, dict) else data
experiments = experiments or []
for exp in experiments:
    print(f"  [{exp['ID'][:8]}] {exp['Subject']} - by {exp['User']['Nickname']} (★{exp['Stars']})")

summary_id = None
# 获取某个实验的有界概览，完整模型不进入聊天
if experiments and experiments[0].get("ContentID"):
    summary_id = experiments[0]["ID"]
    save_id = experiments[0].get("ContentID")
    from community_reads import CommunityReads
    views = CommunityReads(lambda path, body: api._post(path.lstrip("/"), body)).inspect_experiments([save_id], "private-results")
    print(views)

# 获取实验评论
if summary_id:
    comments = api.get_comments(summary_id, take=5)
    rows = comments["Data"]["Comments"]
    rows = rows.get("$values", []) if isinstance(rows, dict) else rows
    for c in rows:
        print(f"  {c['Nickname']}: {c['Content']}")

# 邮箱登录后可以发表评论、点赞等
# api.login("user@example.com", "<从安全存储读取>", version=2609)
# api.star(summary_id)
# api.post_comment(summary_id, "很棒的实验！")
```

## Node.js 示例

```javascript
const https = require("https");

const DOMAIN = "physics-api-cn.turtlesim.com";

function post(path, body, token, authCode) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const headers = { "Content-Type": "application/json" };
    if (token) {
      headers["x-API-Token"] = token;
    }
    if (authCode) {
      headers["x-API-AuthCode"] = authCode;
    }
    const options = {
      hostname: DOMAIN,
      port: 443,
      path: `/${path}`,
      method: "POST",
      headers,
      rejectUnauthorized: true,
      timeout: 30000,
    };
    const req = https.request(options, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        const buffer = Buffer.concat(chunks);
        try {
          const payload = JSON.parse(buffer.toString());
          if (res.statusCode !== 200 || payload.Status !== 200) {
            reject(new Error(`Community request failed: HTTP ${res.statusCode}, Status ${payload.Status}`));
            return;
          }
          resolve(payload); // 认证响应只在程序内部使用，不能整包打印。
        } catch (_) { reject(new Error("Invalid community response")); }
      });
    });
    req.on("timeout", () => req.destroy(new Error("Community request timed out")));
    req.on("error", () => reject(new Error("Community network error")));
    req.write(data);
    req.end();
  });
}

async function main() {
  // 匿名登录
  const loginResult = await post("Users/Authenticate", {
    Login: null,
    Password: null,
    Version: 2609,
    Device: { Identifier: "7db01528cf13e2199e141c402d79190e", Language: "Chinese" },
  });

  const token = loginResult.Token;
  const authCode = loginResult.AuthCode;
  console.log("登录成功, 用户ID:", loginResult.Data.User.ID);

  // 查询实验
  const queryResult = await post("Contents/QueryExperiments", {
    Query: {
      Category: "Experiment", Languages: [], ExcludeLanguages: [],
      Tags: null, ExcludeTags: null, ModelTags: null, ModelID: null,
      ParentID: null, UserID: null, Special: null, From: null,
      Skip: 0, Take: 5, Days: 0, Sort: 0, ShowAnnouncement: false,
    },
  }, token, authCode);

  const data = queryResult.Data;
  const experiments = Array.isArray(data) ? data : (data?.$values || []);
  experiments.forEach((exp) => {
    console.log(`  ${exp.Subject} - by ${exp.User.Nickname} (★${exp.Stars})`);
  });
}

main().catch(console.error);
```

## curl 示例

```bash
# 匿名登录
curl -X POST "https://physics-api-cn.turtlesim.com/Users/Authenticate" \
  -H "Content-Type: application/json" \
  -d '{"Login":null,"Password":null,"Version":2609,"Device":{"Identifier":"<stable-device-id>","Language":"Chinese"}}'

# 邮箱登录协议示意；真实使用运行login_gui.py，不在命令行粘贴密码。不要打印认证原始响应。
curl -X POST "https://physics-api-cn.turtlesim.com/Users/Authenticate" \
  -H "Content-Type: application/json" \
  -d '{"Login":"user@example.com","Password":"<secret>","Version":2609,"Device":{"Identifier":"<stable-device-id>","Language":"Chinese"}}'

# 查询实验（替换 TOKEN 和 AUTHCODE）
curl -X POST "https://physics-api-cn.turtlesim.com/Contents/QueryExperiments" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"Query":{"Category":"Experiment","Languages":[],"ExcludeLanguages":[],"Tags":null,"ExcludeTags":null,"ModelTags":null,"ModelID":null,"ParentID":null,"UserID":null,"Special":null,"From":null,"Skip":0,"Take":10,"Days":0,"Sort":0,"ShowAnnouncement":false}}'

# 下载实验到当前用户的私人任务文件（替换 CONTENT_ID, TOKEN, AUTHCODE）；不要将文件全文发给模型
curl -X POST "https://physics-api-cn.turtlesim.com/Contents/GetExperiment" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"ContentID":"CONTENT_ID"}' -o experiment-private.json

# 获取评论列表
curl -X POST "https://physics-api-cn.turtlesim.com/Messages/GetComments" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"TargetID":"CONTENT_ID","TargetType":"Experiment","Skip":0,"Take":10}'

# 发表评论
curl -X POST "https://physics-api-cn.turtlesim.com/Messages/PostComment" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"TargetID":"CONTENT_ID","TargetType":"Experiment","Content":"很棒的实验！"}'

# 点赞
curl -X POST "https://physics-api-cn.turtlesim.com/Contents/StarContent" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"ContentID":"CONTENT_ID","Category":"Experiment","Status":true,"Type":0}'

# 获取站内信
curl -X POST "https://physics-api-cn.turtlesim.com/Messages/GetMessages" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"CategoryID":0,"Skip":0,"Take":10,"NoTemplates":true}'

# 管理员发送模板通知（普通账号不可用）
curl -X POST "https://physics-api-cn.turtlesim.com/Messages/SendMessages" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"TargetID":["TARGET_USER_ID"],"Category":"Experiment","SummaryID":[],"TemplateID":"TEMPLATE_ID"}'

# 获取社区首页（无需登录）
curl "https://physics-api-cn.turtlesim.com/Users"
```

## 常见使用场景

### 场景 1：批量获取热门实验

```python
api = PhysicsLabAPI()
api.anonymous_login(version=2609)

from community_reads import CommunityReads
client = CommunityReads(lambda path, body: api._post(path.lstrip("/"), body))
# 单批最多20个；排序1是原版热门用法，当前区域的推进语义应检查。
result = client.fetch_works(category="Experiment", count=20, sort=1)
print({key: result[key] for key in ("returned", "complete", "stopReason", "nextCursor")})
```

### 场景 2：按用户明确授权自动回复评论

```python
api = PhysicsLabAPI()
api.login("user@example.com", "<从安全存储读取>", version=2609)

# 获取自己作品的评论
result = api.query_experiments(user_id=api.user_id, take=5)
data = result["Data"]
experiments = data.get("$values", []) if isinstance(data, dict) else data
for exp in experiments or []:
    comments = api.get_comments(exp["ID"])
    rows = comments["Data"]["Comments"]
    rows = rows.get("$values", []) if isinstance(rows, dict) else rows
    for comment in rows:
        # 仅在用户已授权这些目标及正文时执行；不把示例当作发送授权。
        api.post_comment(exp["ID"], f"感谢 {comment['Nickname']} 的评论！")
```

### 场景 3：获取用户主页展示的作品（不是全部历史作品）

```python
api = PhysicsLabAPI()
api.anonymous_login(version=2609)

# 先获取用户信息
user = api.get_user(name="某用户名")
user_id = user["Data"]["User"]["ID"]

# 获取用户资料页（包含精选/热门/最新作品）
profile = api.get_profile(user_id)
for category in ["Featured-Experiments", "Popular-Experiments", "Latest-Experiments"]:
    experiments = profile["Data"]["Experiments"][category]
    print(f"\n{category}:")
    for exp in experiments:
        print(f"  {exp['Subject']} (★{exp['Stars']})")
```
