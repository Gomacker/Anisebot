# Anisebot(Lite)

## Lite 版本
 - [x] 基础Query
 - [x] 一图同步
 - [x] 查盘器实现

## How to start

### 脚本<del>（好像还是有点问题，欢迎大家推优化）</del>
1. 如果缺少python，安装python环境 (推荐3.10.x)
2. 运行安装依赖.bat
3. 运行bot `runbot.bat`
4. 配置并运行你的 bot 前端实现（[go-cqhttp](https://github.com/Mrs4s/go-cqhttp) 、 [mirai](https://mirai.mamoe.net/) 等）
   ```
   推荐用反向ws连接 ws://127.0.0.1:8080/onebot/v11/
   ```

### 手动
使用 Poetry 进行包管理
1. 如果缺少python，安装python环境 (推荐3.10.x)
2. Win+R启动 cmd 或 powershell 运行以下命令安装 poetry
   ```
   > pip install poetry
   ```
3. 在目录内运行
   ```
   > poetry install
   ```
4. 补全 playwright 依赖
   ```
   > playwright install
   ```
5. 启动Bot
   ```
   > poetry run nb run
   ```
6. 配置并运行你的 bot 前端实现（[go-cqhttp](https://github.com/Mrs4s/go-cqhttp) 、 [mirai](https://mirai.mamoe.net/) 等）

   推荐用反向ws连接 `ws://127.0.0.1:8080/onebot/v11/`
