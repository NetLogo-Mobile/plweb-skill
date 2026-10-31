# 图片上传

本地使用 `CommunityActions.set_avatar(image_path)` 与 `set_cover(summary_id,image_path,category="Experiment")`。云端使用 `upload_avatar`、`upload_cover`，图片可以是小文件的Base64或分块上传后的image_file_id。

## 头像

1. 读取当前用户最新Avatar，使用新序号Avatar+1。
2. 调用RequestAvatar，Request为`{Extension:".jpg",FileSize:-图片字节数}`。
3. 用返回的Data凭据上传图片。
4. ConfirmAvatar传`{Avatar:新序号}`，重新GetUser核对。

头像上限为 **1024×1024字节（1MB）**；辅助代码在发送前拒绝超限文件。

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
