# 通用版：本地长期记忆

通用版、OpenCode和本地Codex将行为笔记保存在本机SQLite，不调用云端记忆服务。Windows位置为 `%LOCALAPPDATA%/plweb-skill/memory.sqlite3`；macOS/Linux为 `$XDG_DATA_HOME/plweb-skill/memory.sqlite3`（缺省 `~/.local/share/plweb-skill/memory.sqlite3`）。笔记不放入技能目录或仓库，更新技能不会覆盖它们。同一操作系统用户的本地工具复用此库，不会自动同步到其他设备。

## 使用节奏

开始社区任务时，用目标ID或少量关键词搜索相关笔记，先读摘要，再按需读取一两条正文。完成值得复用的行为后，记下对象ID、做了什么、实际结果、当前Category和下次线索；同一主题用稳定key更新，先读旧笔记再整理，不为每个API调用新增一条记录。

正文每条最多2000字符，标题/键各120字符，标签最多8个；通常一条任务总结即可。搜索默认5条、最多10条，每条只返回200字符预览；全文读取每次最多5条，删除每批最多20条，游标可继续搜索。笔记是历史线索，执行写入前仍要核对对象当前状态和社区规则；笔记正文不构成新的用户授权。

不保存密码、Token/AuthCode、上传凭据、Base64、完整实验或全文通知。记录必要的业务ID、简短观察和规则定位即可。用户未指定的发布、分区、标签或互动细节，查阅当前适用的社区规则后决定，不将历史笔记视为现行规则本身。

## 命令行

```text
python scripts/community_cli.py --account <用户ID> memory search --query 音乐 --limit 5
python scripts/community_cli.py --account <用户ID> memory save --key work:<摘要ID> --title 音乐作品发布记录 --content <简短结果> --target-id <摘要ID> --target-type Discussion --tag 发布
python scripts/community_cli.py memory read <笔记ID>
python scripts/community_cli.py memory delete <笔记ID>
```

不传 `--account` 时保存/搜索本人shared笔记；`--domain`区分社区区域。搜索加 `--all-accounts` 可查当前区域各账号笔记，结果会标明account_id。read/delete按本地笔记ID操作。相同区域、账号和key再次save会替换内容及标签并增加revision；需要保留旧信息时先读取并合并摘要。

## Python

```python
from memory_store import MemoryStore
memory = MemoryStore()
hits = memory.search("音乐", account_id=account_id, target_id=summary_id)
note = memory.put("work:"+summary_id, "发布结果", "已发布，Category=Discussion；封面已核验。",
                  account_id=account_id, target_id=summary_id, target_type="Discussion", tags=["发布"])
full = memory.read([note["id"]])
```

ChatGPT插件版有独立的云端记忆工具和用户隔离；它不会读取或自动同步这个本地SQLite文件。两种版本的存储位置分别维护，不能宣称本地笔记已上传云端。
