# Anisebot(Lite)

## Lite 版本
 - [x] 基础Query
 - [x] 一图同步
 - [x] 查盘器实现

## How to start

### 脚本<del>（好像还是有点问题，欢迎大家推优化）</del>
1. 如果缺少python，安装python环境
   
   Python版本请使用3.10.x，不同的版本可能会导致不可预知的问题
2. 运行安装依赖.bat

   ① 请确保安装依赖过程正常完成

   ② 根据网络状况可能出现较长耗时，请耐心等待

   ③ 若出现connect、timeout等字样报错大概率为网络问题，请自行调整网络环境

3. 运行bot `runbot.bat`

   请确保运行后命令行看到如下输出，这代表bot已经启动成功并开始监听

   ```
   > [INFO] uvicorn | Waiting for application startup.
   > [INFO] uvicorn | Application startup complete.
   > [INFO] uvicorn | Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
   ```

4. 配置并运行你的 bot 前端实现
   
   ① [go-cqhttp](https://github.com/Mrs4s/go-cqhttp)
   
   [查看文档](doc/botConnect-GoCq.md)

   ② [mirai](https://mirai.mamoe.net/)
   
   [查看文档](doc/botConnect-Mirai.md)

   ③ etc
 

### 手动
使用 Poetry 进行包管理
1. 如果缺少python，安装python环境 
   
   Python版本请使用3.10.x，不同的版本可能会导致不可预知的问题
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
6. 配置并运行你的 bot 前端实现
   
   ① [go-cqhttp](https://github.com/Mrs4s/go-cqhttp)
   
   [查看文档](doc/botConnect-GoCq.md)

   ② [mirai](https://mirai.mamoe.net/)
   
   [查看文档](doc/botConnect-Mirai.md)

   ③ etc

