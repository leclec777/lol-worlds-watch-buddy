# GitHub 发布信息

这是待发布的项目元数据和首个版本文案，不代表已经公开发布。

## 仓库

- 仓库名：`lol-worlds-watch-buddy`
- 可见性：Public
- 许可证：MIT
- 首个公开版本：`v1.1.0`

## About / Description

LOL 世界赛观赛搭子：和好友支持主队，用积分竞猜比拼眼光。LoL Worlds Pick’em for friends — local-first League of Legends match predictions, official LPL schedule sync, custom odds & friendly leaderboards. Python · MIT.

## Topics

`lol`, `league-of-legends`, `lol-worlds`, `worlds`, `esports`, `lpl`, `pickem`, `predictions`, `watch-party`, `friends`, `leaderboard`, `local-first`, `python`, `open-source`, `chinese`

GitHub Topics 使用英文小写标签，中文关键词通过仓库简介、README 标题和项目介绍呈现。以上标签与真实功能对应，不使用与项目无关的热门词。

## 首个 Release 标题

v1.1.0 · 观赛搭子 / LoL Worlds Watch Buddy

## Release 介绍

世界赛，一个人看是比赛，和朋友一起看就是主场。

观赛搭子是一款本地运行的开源 LOL / 英雄联盟比赛积分预测工具。你和好朋友各自支持主队，在比赛前用虚拟积分预测输赢，赛后一起看排行榜、比眼光。

### 本版功能

- 通过 lpl.qq.com 官方赛程，按 UTC+8 日期预览并勾选导入比赛。
- 赛程未公布或对阵待定时明确提示；没有比赛时不生成假对局。
- 赔率完全由你们手动设置；下注时锁定赔率，后续修改不影响旧预测。
- 双人切换、主队标记、比赛搜索、日期分组和状态筛选。
- 开赛自动封盘，手动确认赛果后自动结算虚拟积分；取消比赛退款。
- 双人排行榜、命中率、积分走势与 JSON 备份。
- Python 3.8+，标准库零依赖，支持 macOS、Windows 与 Linux。

### 下载和使用

下载并解压 `lol-worlds-watch-buddy-v1.1.0.zip`。Mac 双击「启动观赛搭子.command」，Windows 双击「启动-Windows.bat」。其他系统运行 `python3 server.py --open`。

当前版本支持同一台电脑上的两位玩家轮流使用，属于好友互信房间。没有充值、提现、现金奖励或远程多人账号功能。与 Riot Games / 腾讯官方无隶属关系。

English: A local-first LoL Worlds Pick’em app for friends. Support your favorite team, make virtual-point match predictions, and enjoy a friendly rivalry with your watch buddy. Official LPL schedule import, user-defined odds, and private local data. MIT licensed.

## 发布核验

发布时应确认仓库首页可匿名访问、README 与许可证可见、源码完整、Release 包可下载。单独上传 ZIP 不视为完成源码开源。
