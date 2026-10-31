# 自动生成实验存档与授权发布

## 依赖与边界

参考 [SekaiArendelle/physicslab](https://github.com/SekaiArendelle/physicslab) 的**本地建模、元件、导线、坐标和存档读写**。当前已测试提交 `fa95b96910dd0fd4e09cf27e24cefaf9b91798ad`（physicslab 3.0.0，Python 3.14+）。不参考、不调用其网络模块：不要使用 physicslab.web、email_login、网络迭代器或库的发布封装。

在隔离 Python 环境安装并核对实际版本。不要照搬旧版 Experiment/OpenMode 的代码；当前接口包括 crt_circuit_experiment、LogicInput、LogicOutput、Position、crt_elements、crt_a_wire、save_to，以及对应载入函数。Celestial/Electromagnetism 的构造器和对象需按该版本本地模块文档核实，不凭名字猜参数。

该提交的顶层导入会因本地模块的默认参数求值触发匿名网络登录。**不要直接 `import physicslab`**；在新的 Python 进程先使用随附 `scripts/offline_physicslab.py` 的 `load_local_modules()`，从其返回的 circuit/celestial/electromagnetism/coordinate_system 模块操作。它绕开根包的网络导入，用无会话占位隔离本地模块未使用的网络默认值，不执行库网络模块、不创建真实网络身份。示例已在禁止 socket 连接的条件下通过生成与重新载入测试。不能拿占位 User 或匿名默认值去做社区请求。

本库生成的是物理实验室实验存档，不是通用物理解算器。代码可运行、存档可重新载入，不等于实验已在官方客户端仿真验证；没有运行仿真就必须标注“未验证仿真”，不能编造测量值。

## 生成流程

1. 根据用户目标确定电路/天体/电磁类型、布局、元件参数、连接关系及预期行为。可自行补足常规布局；影响实验目的的条件缺失才询问。
2. 只在任务工作目录创建脚本与新存档。修改已有存档时先复制并保留原件。生成文件名不复用已存在文件，不覆盖用户的本地实验目录。
3. 首次先运行 `scripts/experiment_example.py --output <新的绝对路径.plsav> --title <标题>`，或根据目标编写同等的本地脚本。这个示例只用本地库 API，创建两个逻辑元件和一根导线；它不登录、不发布。
4. 按目标扩展元件和连接，核对坐标、引脚、类型及导线端点。保存后解析 JSON，再用同版本的载入函数重新载入。StatusSave 等字段若为 JSON 字符串，解析其内部模型，检查元件 ID 唯一、导线端点存在、元件/导线数量和预期布局。
5. 交付 .plsav、生成脚本和简要使用说明。没有官方客户端时可以完成存档验证，但应如实说明尚未做客户端仿真。

## 发布流程

用户明确要求“制作并发布”时，该请求已经授权按指定账号发布相应实验；不必重复索要同一许可。仅要求制作时，先交付本地存档，不能顺手发到社区。

1. 用已关联账号/安全登录流程确定发布账号，读取实时标签配置，准备准确标题、介绍、分类与标签。保留当前任务的实验文件和生成依据。
   库内 Tag 枚举不能代替当前在线标签配置；在线提交使用实时 Identifier 和当前账号正常权限。
2. **优先走官方客户端的正常导入与发布界面**：在可控制的物理实验室客户端导入生成的 .plsav（“从本地读取”等正常入口），打开并检查实验，按需要运行仿真，再使用客户端发布入口提交。根据实际可见界面操作，不编造按钮、字段或成功状态。密码由用户在安全窗口自行填写，AI 不读取。
3. 发布后通过已验证的社区 API，按作者 ID、分类和近期时间范围取得候选，以返回的新摘要 ID、作者、标题、创建时间和实际模型核验；再读取 GetSummary 和 GetExperiment 确认真实存档。仅凭 HTTP 200、生成文件或点击发布不能报告成功。
4. 若客户端不可用，或者新建实验的 HTTP 提交流程尚未核实，停止在“存档已生成、等待发布”，说明具体缺少的执行路径。不要把既有作品改 ID、猜造 SubmitExperiment 的新建字段，或回头调用不可靠的库网络模块。

当前已核对的 `/Contents/SubmitExperiment` 用于 practical-api.md 所述既有作品文本/标签编辑；这不证明它的新建模型、封面上传和首次发布协议已验证。未来要走 HTTP 自动新建，先依据正常客户端真实调用确认完整结构和读回流程，不能仅凭库里的网络实现补齐。

## Chat、Work、本地与通用版

- 本地 Codex/OpenCode/通用版：可运行本地 Python 生成与验证，有官方客户端和可用界面控制工具时继续正常发布。
- 云端 Work：可在支持 Python 3.14 和安装依赖的执行环境生成存档；客户端或其正常发布界面不可达时，交付存档并明确待发布。
- Chat 插件：提供这份可复用流程和已有社区工具。普通 Chat 没有代码执行或官方客户端控制时，不能声称已经执行本地库；将可运行脚本/存档生成任务交给有这些能力的 Work 或本地环境，再按同一账号核验发布结果。

本次仅验证本地生成、JSON结构与重新载入，没有向社区试发实验。

## 本地模块参考

- [快速开始的本地建模部分](https://github.com/SekaiArendelle/physicslab/blob/fa95b96910dd0fd4e09cf27e24cefaf9b91798ad/docs/quick_start.md)。忽略其中网络示例。
- [电路存档与操作](https://github.com/SekaiArendelle/physicslab/blob/fa95b96910dd0fd4e09cf27e24cefaf9b91798ad/physicslab/circuit/experiment.py)。
- [元件](https://github.com/SekaiArendelle/physicslab/tree/fa95b96910dd0fd4e09cf27e24cefaf9b91798ad/physicslab/circuit/elements)、[坐标](https://github.com/SekaiArendelle/physicslab/blob/fa95b96910dd0fd4e09cf27e24cefaf9b91798ad/physicslab/coordinate_system.py)。
