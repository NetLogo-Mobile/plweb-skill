# 创建与发布实验

使用 physicslab 3.0.0（Python 3.14+）的本地模型接口。先通过 `scripts/offline_physicslab.py` 的 `load_local_modules()` 加载 circuit、celestial、electromagnetism 和 coordinate_system；可运行随附示例生成存档。

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

大型存档和图片先分块调用 `store_file_chunk`，再把返回的 `fileId` 传给 `publish_experiment.archive_file_id` 或图片上传工具。分块index从0连续递增，最后一块complete=true。完整模型在文件和程序中处理，不全文输出到聊天。

本地建模示例验证存档构造、保存和重载；实验说明中的测量值应来自实际计算或测量。模型类型0为电路、3为天体、4为电磁。
