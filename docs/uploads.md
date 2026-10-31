# 图片上传

本地使用 `CommunityActions.set_avatar(image_path)` 与 `set_cover(summary_id,image_path,category="Experiment")`。云端使用 `upload_avatar`、`upload_cover`，必填 `image_source`：`base64` 时只填原始 `image_base64` 字符串（不含data:前缀）；`plugin_file` 时只填 `image_file_id`。

`image_file_id` 只能是本插件 `store_file_chunk` 返回的 `plfile_…`，文件必须 `kind=image` 且 `complete=true`。ChatGPT附件ID、生成图片的附件ID和路径都不能直接传入。先在有文件读取能力的环境中读取附件字节，分块Base64保存到本插件，再使用返回ID。

例如 `upload_avatar({image_source:"plugin_file",image_file_id:"plfile_<UUID>"})`。小图也可 `upload_avatar({image_source:"base64",image_base64:"<原始Base64>"})`。两种方式均可选传 `account_id`。封面工具另外必填 `summary_id`，可选 `category`。

## 头像

1. 读取当前用户最新Avatar，使用新序号Avatar+1。
2. 调用RequestAvatar，Request为`{Extension:".jpg",FileSize:-图片字节数}`。
3. 用返回的Data凭据上传图片。
4. ConfirmAvatar传`{Avatar:新序号}`，重新GetUser核对。

头像文件上限为 **1,048,576字节（1MiB）**；封面文件上限为 **8,388,608字节（8MiB）**，发送前拒绝超限文件。图片格式为 JPEG、PNG 或 WebP。像素尺寸与文件字节数是两个不同概念；插件不另设宽高像素上限，不能将文件大小写成1024×1024像素。

## 封面

1. GetSummary取最新Image，使用Image+1。
2. ConfirmExperiment传Category、SummaryID、新Image和Extension=".png"。
3. SubmitExperiment传原Summary（Image更新为新序号）和Request=`{Extension:".jpg",FileSize:-图片字节数}`。
4. 使用Data.Token上传图片，随后再次ConfirmExperiment并读回摘要。

## 存储上传表单

- RequestHost非空：向该HTTPS地址发送key=RequestURI、OSSAccessKeyId=AccessKey、policy=Policy、Signature=Authorization及file。
- RequestHost为空：向`https://v0.api.upyun.com`加RequestURI发送authorization、policy及file。
- file使用image.jpg文件名，实际图片支持JPEG、PNG或WebP。上传程序内部处理临时凭据；不向图片主机发送账号Token/AuthCode。

`publish`默认根据模型生成封面，也可指定图片。命令行示例：

```text
python scripts/community_cli.py --account <用户ID> avatar --image <图片>
python scripts/community_cli.py --account <用户ID> cover --summary-id <摘要ID> --image <图片>
```
