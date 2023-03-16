# Anisebot(Lite)

## Lite 版本
 - [x] 基础Query
 - [x] 基础Gacha
 - [ ] WikiPageGenerator
 - [ ] 查盘器实现
 - [ ] 自动转换数据包
 - [ ] 玩家 / 房间查询

## 注：
   1. 对大部分明文数据做了极度简化的处理，在角色上修并修正后会补全
   2. 测试用资源包：[Alpha(0.1)](https://github.com/Gomacker/Anisebot/releases/tag/v0.1-alpha)
      （稍微看一下数据👉👈）


## How to start

1. 安装依赖 `requirements.txt`
2. 将准备好的资源包(res与data)解压在根目录
   ```
   Anisebot
   ┣ anise_bot
   ┣ anise_core
   ┣ config
   ┣ data
   ┣ res
   ┣ ...
   ```
3. 运行bot `nb run`
4. 配置并运行你的 bot 前端实现（[go-cqhttp](https://github.com/Mrs4s/go-cqhttp) 、 [mirai](https://mirai.mamoe.net/) 等）
   ```
   推荐用反向ws连接 ws://127.0.0.1:8080/onebot/v11/
   ```
