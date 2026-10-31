# 创建与发布实验

使用本包 `vendor/physicslab` 内置的本地建模库（Python 3.10+），由 [Arendelle](https://github.com/SekaiArendelle) 的 [physicslab](https://github.com/SekaiArendelle/physicslab) 适配，保留 MIT 许可。网络、上传和登录缓存读取部分已移除。先通过 `scripts/offline_physicslab.py` 的 `load_local_modules()` 加载 circuit、celestial、electromagnetism 和 coordinate_system；可运行随附示例生成存档。

**使用随包内置库，不从作者GitHub或PyPI另取库。AI交付由此库生成的结果时，提及作者 Arendelle 并附 https://github.com/SekaiArendelle 。** 云端有代码执行能力的环境用 `get_modeling_library` 获取插件内置ZIP并解压，保留 scripts/vendor 目录关系。音乐生成见 [音乐电路](music.md)，Chat可直接调用 `generate_music_experiment`。

```text
python scripts/experiment_example.py --type circuit --output <新文件.plsav> --title <标题>
python scripts/experiment_example.py --type celestial --output <新文件.plsav> --title <标题>
python scripts/experiment_example.py --type electromagnetism --output <新文件.plsav> --title <标题>
```

示例分别创建逻辑输入/输出及导线、太阳与地球、正负电荷。扩展实验时按目标设置元件、位置、参数和连接；保存后重新载入，核对元件标识、导线端点与数量。修改现有存档时保留原件。

## 发布

用户要求发布时直接调用 `CommunityActions.publish` 或云端工具 `publish_experiment`。用户只要求制作时交付存档。

```text
python scripts/community_cli.py --account <用户ID> publish --archive <文件.plsav> --title <标题> --description <介绍> --tag <实时标签Identifier>
```

发布方法提交 `Summary`、`Experiment` 和 `Workspace`，读取返回的摘要ID与保存ContentID。默认按实际模型布局生成PNG封面并上传，也可传 `--cover <图片>`。最后读回摘要、模型和封面序号，返回 `published`、`modelVerified`、`coverUploaded`。

直接请求形式：`POST /Contents/SubmitExperiment`，正文为 `{Summary:{ID:null,ContentID:null,Category:"Experiment",Subject,Description,Tags,Language,...},Experiment:{ID:null,Type,StatusSave,CameraSave,...},Workspace:null}`。使用 `.plsav` 中的 Summary/Experiment 构造完整对象，标题、介绍、标签按任务替换，保留模型字段。

`publish_experiment` 专门从模型存档发布作品；标题和介绍不能代替 `.plsav` 模型。参数必填 `source`：

- `source="archive_json"`：仅填 `archive_json`，值是完整 `.plsav` 对象的JSON序列化字符串，包含 `Experiment` 对象和 `StatusSave` 模型字符串。
- `source="plugin_file"`：仅填 `archive_file_id`，值必须是插件保存的完整archive文件ID。

可选 `title:string`、`description:string[]`、`tags:string[]`、`category:"Experiment"|"Discussion"|"Model"`、`language:string`、`account_id:string`。封面可选 `cover_base64:string` 或 `cover_file_id:string`，二选一；省略则自动生成。

大型存档和图片先分块调用 `store_file_chunk`，`kind` 选 `archive` 或 `image`，`encoding` 选 `utf8` 或 `base64`，单块不超过60000字符。首块index=0且不传file_id，续块传上一响应的 `plugin_file_id` 作为file_id，index连续递增，末块complete=true。返回 `plugin_file_id`（`fileId`同值）具有 `plfile_` 前缀；不是ChatGPT附件ID。发布传 `source="plugin_file"` 与 `archive_file_id`，图片工具传 `image_source="plugin_file"` 与 `image_file_id`。完整模型在文件和程序中处理，不全文输出到聊天。

本地建模示例验证存档构造、保存和重载；实验说明中的测量值应来自实际计算或测量。模型类型0为电路、3为天体、4为电磁。
