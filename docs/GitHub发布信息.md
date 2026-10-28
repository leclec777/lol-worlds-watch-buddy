# GitHub 发布信息

当前源码版本为 **1.2.0**，新增按比赛结果留言的「赛后讨论」面板。

- [项目首页](https://github.com/leclec777/lol-worlds-watch-buddy)
- [最新发布版本和下载包](https://github.com/leclec777/lol-worlds-watch-buddy/releases/latest)
- 对应源码包：`lol-worlds-watch-buddy-v1.2.0.zip`

## 源码和 Release

`main` 保存最新源码；GitHub 首页的 Releases / Latest 显示单独发布的版本。合并代码后，还需要生成对应版本的 Release 和下载包。

仓库现在通过「Publish source release」后台流程完成发布：代码合并到 `main` 且版本或发布配置有变化时，先运行测试、生成干净源码包，再创建对应版本的 Release。下载包上传成功后才公开发布并设为 Latest。

此流程也可以在 GitHub Actions 中手动运行。已经公开发布的同版本下载包会保留；若发布中断留下草稿，再次运行会继续上传并完成发布。

## 准备下个版本

1. 同步更新 `server.py` 中的 `APP_VERSION` 和 `scripts/package.py` 中的 `VERSION`，格式为 `X.Y.Z`。
2. 在 `CHANGELOG.md` 增加对应版本说明，更新 README 中的当前版本。
3. 提交 PR，确认自动检查通过后合并到 `main`。
4. 等待后台发布成功，核对 Releases / Latest 的版本及源码包。

发布流程会检查应用版本、打包版本和更新说明是否匹配，避免将旧包作为新版发布。

## 下载和使用

在最新 Release 页面下载并解压对应的源码 ZIP。macOS 双击「启动观赛搭子.command」，Windows 双击「启动-Windows.bat」；其他系统运行 `python3 server.py --open`。需要 Python 3.8+，无需第三方依赖。

现有数据库和旧备份可继续使用；讨论留言也包含在新备份中。私人数据库、导出备份和本机测试房间不会进入发布包。

当前仍是同机双人互信房间，积分没有现金价值，不包含充值、提现或远程多人账号功能。
