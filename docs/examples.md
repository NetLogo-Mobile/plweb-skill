# 完整代码示例

以下是使用 Python、Node.js 和 curl 调用物理实验室 AR API 的完整示例。

## Python 示例

### 完整 API 客户端类

```python
import json
import ssl
import urllib.request


class PhysicsLabAPI:
    """物理实验室 AR 社区 API 客户端"""

    DOMAIN = "physics-api-cn.turtlesim.com"

    def __init__(self):
        self.token = None
        self.auth_code = None
        self.user_id = None
        self._ssl_context = ssl._create_unverified_context()

    def _post(self, path, body, need_auth=True):
        """发送 POST 请求"""
        url = f"https://{self.DOMAIN}:443/{path}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.headers = {"Content-Type": "application/json"}
        if need_auth:
            req.headers["x-API-Token"] = self.token or ""
            req.headers["x-API-AuthCode"] = self.auth_code or ""
        with urllib.request.urlopen(req, context=self._ssl_context) as resp:
            if resp.info().get("Content-Encoding") == "gzip":
                import gzip
                content = gzip.decompress(resp.read())
            else:
                content = resp.read()
            return json.loads(content)

    def _get(self, path):
        """发送 GET 请求"""
        url = f"https://{self.DOMAIN}:443/{path}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, context=self._ssl_context) as resp:
            return json.loads(resp.read())

    # ========== 登录 ==========

    def login(self, email, password, version=2411):
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
            self.token = result.get("Token")
            self.auth_code = result.get("AuthCode")
            self.user_id = result["Data"]["User"]["ID"]
        return result

    def anonymous_login(self, version=2411):
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
            self.token = result.get("Token")
            self.auth_code = result.get("AuthCode")
            self.user_id = result["Data"]["User"]["ID"]
        return result

    # ========== 用户 ==========

    def get_user(self, name=None, user_id=None):
        """获取用户信息"""
        body = {}
        if name:
            body["Name"] = name
        elif user_id:
            body["ID"] = user_id
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

    def get_relations(self, user_id, display_type="Follower", skip=0, take=20):
        """获取粉丝/关注列表"""
        return self._post("Users/GetRelations", {
            "UserID": user_id,
            "DisplayType": display_type,
            "Skip": skip,
            "Take": take,
            "Query": "",
        })

    # ========== 内容/实验 ==========

    def query_experiments(self, category="Experiment", skip=0, take=16, sort=0,
                          tags=None, user_id=None):
        """查询实验列表"""
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
            "From": None,
            "Skip": skip,
            "Take": take,
            "Days": 0,
            "Sort": sort,
            "ShowAnnouncement": False,
        }
        return self._post("Contents/QueryExperiments", {"Query": query})

    def get_experiment(self, content_id):
        """获取实验详情"""
        return self._post("Contents/GetExperiment", {"ContentID": content_id})

    def get_summary(self, content_id, category="Experiment"):
        """获取实验摘要"""
        return self._post("Contents/GetSummary", {
            "ContentID": content_id,
            "Category": category,
        })

    def get_derivatives(self, content_id, category="Experiment"):
        """获取衍生作品"""
        return self._post("Contents/GetDerivatives", {
            "ContentID": content_id,
            "Category": category,
        })

    def get_supporters(self, content_id, category="Experiment", skip=0, take=10):
        """获取支持者列表"""
        return self._post("Contents/GetSupporters", {
            "ContentID": content_id,
            "Category": category,
            "Skip": skip,
            "Take": take,
        })

    def star(self, content_id, category="Experiment", star=True):
        """点赞/取消点赞"""
        return self._post("Contents/Star", {
            "ContentID": content_id,
            "Category": category,
            "Action": 1 if star else 0,
        })

    def remove_experiment(self, content_id, category="Experiment"):
        """删除实验"""
        return self._post("Contents/RemoveExperiment", {
            "ContentID": content_id,
            "Category": category,
        })

    # ========== 评论 ==========

    def get_comments(self, content_id, category="Experiment", skip=0, take=16):
        """获取评论列表"""
        return self._post("Contents/GetComments", {
            "ContentID": content_id,
            "Category": category,
            "Skip": skip,
            "Take": take,
        })

    def post_comment(self, content_id, content, category="Experiment"):
        """发表评论"""
        return self._post("Contents/PostComment", {
            "ContentID": content_id,
            "Category": category,
            "Content": content,
        })

    def remove_comment(self, content_id, comment_id, category="Experiment"):
        """删除评论"""
        return self._post("Contents/RemoveComment", {
            "ContentID": content_id,
            "Category": category,
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

    def send_message(self, receiver_id, content):
        """发送站内信"""
        return self._post("Messages/SendMessage", {
            "ReceiverID": receiver_id,
            "Content": content,
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
result = api.anonymous_login()
print(f"登录状态: {result['Status']}, 用户ID: {api.user_id}")

# 查询最新实验
result = api.query_experiments(category="Experiment", skip=0, take=5, sort=0)
experiments = result["Data"]["$values"]
for exp in experiments:
    print(f"  [{exp['ContentID'][:8]}] {exp['Title']} - by {exp['Author']['Nickname']} (★{exp['Stars']})")

# 获取某个实验的详情
if experiments:
    content_id = experiments[0]["ContentID"]
    detail = api.get_experiment(content_id)
    print(f"实验详情: {detail['Data']['Title']}")

# 获取实验评论
comments = api.get_comments(content_id, take=5)
for c in comments["Data"]["$values"]:
    print(f"  {c['Author']['Nickname']}: {c['Content']}")

# 邮箱登录后可以发表评论、点赞等
# api.login("user@example.com", "password")
# api.star(content_id)
# api.post_comment(content_id, "很棒的实验！")
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
      headers["x-API-AuthCode"] = authCode;
    }
    const options = {
      hostname: DOMAIN,
      port: 443,
      path: `/${path}`,
      method: "POST",
      headers,
      rejectUnauthorized: false, // 忽略证书验证
    };
    const req = https.request(options, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        const buffer = Buffer.concat(chunks);
        resolve(JSON.parse(buffer.toString()));
      });
    });
    req.on("error", reject);
    req.write(data);
    req.end();
  });
}

async function main() {
  // 匿名登录
  const loginResult = await post("Users/Authenticate", {
    Login: null,
    Password: null,
    Version: 2411,
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

  const experiments = queryResult.Data.$values;
  experiments.forEach((exp) => {
    console.log(`  ${exp.Title} - by ${exp.Author.Nickname} (★${exp.Stars})`);
  });
}

main().catch(console.error);
```

## curl 示例

```bash
# 匿名登录
curl -k -X POST "https://physics-api-cn.turtlesim.com/Users/Authenticate" \
  -H "Content-Type: application/json" \
  -d '{"Login":null,"Password":null,"Version":2411,"Device":{"Identifier":"7db01528cf13e2199e141c402d79190e","Language":"Chinese"}}'

# 邮箱登录（替换邮箱和密码）
curl -k -X POST "https://physics-api-cn.turtlesim.com/Users/Authenticate" \
  -H "Content-Type: application/json" \
  -d '{"Login":"user@example.com","Password":"yourpassword","Version":2411,"Device":{"Identifier":"7db01528cf13e2199e141c402d79190e","Language":"Chinese"}}'

# 查询实验（替换 TOKEN 和 AUTHCODE）
curl -k -X POST "https://physics-api-cn.turtlesim.com/Contents/QueryExperiments" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"Query":{"Category":"Experiment","Languages":[],"ExcludeLanguages":[],"Tags":null,"ExcludeTags":null,"ModelTags":null,"ModelID":null,"ParentID":null,"UserID":null,"Special":null,"From":null,"Skip":0,"Take":10,"Days":0,"Sort":0,"ShowAnnouncement":false}}'

# 获取实验详情（替换 CONTENT_ID, TOKEN, AUTHCODE）
curl -k -X POST "https://physics-api-cn.turtlesim.com/Contents/GetExperiment" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"ContentID":"CONTENT_ID"}'

# 获取评论列表
curl -k -X POST "https://physics-api-cn.turtlesim.com/Contents/GetComments" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"ContentID":"CONTENT_ID","Category":"Experiment","Skip":0,"Take":10}'

# 发表评论
curl -k -X POST "https://physics-api-cn.turtlesim.com/Contents/PostComment" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"ContentID":"CONTENT_ID","Category":"Experiment","Content":"很棒的实验！"}'

# 点赞
curl -k -X POST "https://physics-api-cn.turtlesim.com/Contents/Star" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"ContentID":"CONTENT_ID","Category":"Experiment","Action":1}'

# 获取站内信
curl -k -X POST "https://physics-api-cn.turtlesim.com/Messages/GetMessages" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"CategoryID":0,"Skip":0,"Take":10,"NoTemplates":true}'

# 发送站内信
curl -k -X POST "https://physics-api-cn.turtlesim.com/Messages/SendMessage" \
  -H "Content-Type: application/json" \
  -H "x-API-Token: TOKEN" \
  -H "x-API-AuthCode: AUTHCODE" \
  -d '{"ReceiverID":"TARGET_USER_ID","Content":"你好！"}'

# 获取社区首页（无需登录）
curl -k "https://physics-api-cn.turtlesim.com/Users"
```

## 常见使用场景

### 场景 1：批量获取热门实验

```python
api = PhysicsLabAPI()
api.anonymous_login()

all_experiments = []
skip = 0
while True:
    result = api.query_experiments(category="Experiment", skip=skip, take=50, sort=1)
    experiments = result["Data"]["$values"]
    if not experiments:
        break
    all_experiments.extend(experiments)
    skip += 50
    if len(all_experiments) >= 200:  # 获取前 200 个
        break

print(f"共获取 {len(all_experiments)} 个热门实验")
```

### 场景 2：自动回复评论

```python
api = PhysicsLabAPI()
api.login("user@example.com", "password")

# 获取自己作品的评论
result = api.query_experiments(user_id=api.user_id, take=5)
for exp in result["Data"]["$values"]:
    comments = api.get_comments(exp["ContentID"])
    for comment in comments["Data"]["$values"]:
        # 自动回复每条评论
        api.post_comment(exp["ContentID"], f"感谢 {comment['Author']['Nickname']} 的评论！")
```

### 场景 3：获取用户所有作品

```python
api = PhysicsLabAPI()
api.anonymous_login()

# 先获取用户信息
user = api.get_user(name="某用户名")
user_id = user["Data"]["User"]["ID"]

# 获取用户资料页（包含精选/热门/最新作品）
profile = api.get_profile(user_id)
for category in ["Featured-Experiments", "Popular-Experiments", "Latest-Experiments"]:
    experiments = profile["Data"]["Experiments"][category]
    print(f"\n{category}:")
    for exp in experiments:
        print(f"  {exp['Title']} (★{exp['Stars']})")
```
