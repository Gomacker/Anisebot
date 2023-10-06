# Mirai
mirai相当于一个门童，你需要让这个门童登录你的bot并接收消息

这位门童将会把消息递交给anisebot，bot返回的消息也将通过他传递给用户

## 1、资源
[mirai官方论坛](https://mirai.mamoe.net/)

[MCL Installer](https://github.com/iTXTech/mcl-installer)

[mirai-login-solver-sakura](https://github.com/KasukuSakura/mirai-login-solver-sakura)

[onebot-mirai](https://github.com/yyuueexxiinngg/onebot-kotlin/releases)

## 2、安装

1. 通过mcl安装mirai

    下载安装包后一路回车，mcl Installer会帮你一键下载java以及mirai

    运行mcl.cmd即可启动bot

    看到命令行出现如下语句即为运行成功
    ```
    mirai-console started successfully
    ```

2. 安装mirai-login-solver-sakura

    mirai-login-solver-sakura是一套验证处理工具，用于处理登录时的身份验证

    从 [Releases](https://github.com/KasukuSakura/mirai-login-solver-sakura/releases)下载

    - `mirai-login-solver-sakura-XXX.mirai2.jar` -> mirai-console 插件
    - `apk-release.apk` 安卓应用程序

    将插件本体拖入mirai\plugins文件夹即可；apk可用安卓手机安装来方便获取ticket，非必须
3. 安装onebot-mirai

    onebot-mirai是mirai的onebot协议实现

    从 [Releases](https://github.com/yyuueexxiinngg/onebot-kotlin/releases)下载jar包后拖入mirai\plugins文件夹

    运行miraibot将在`config/com.github.yyuueexxiinngg.onebot`文件夹下生成setting.yml文件
## 3、配置

 1. 修改`config/Console/AutoLogin.yml` 

     填入bot账号密码即可

 2. 修改`config/com.github.yyuueexxiinngg.onebot/setting.yml`
    
     修改botID，将ws_reverse改为如下格式，使用反向ws连接anisebot
     ```
     ws_reverse: 
       - enable: true
         postMessageFormat: string
         reverseHost: 0.0.0.0
         reversePort: 8080
         accessToken: ''
         reversePath: '/onebot/v11/'
         reverseApiPath: '/onebot/v11/'
         reverseEventPath: '/onebot/v11/'
         useUniversal: true
         useTLS: false
         reconnectInterval: 3000
     ```

## 4、连接Anisebot
 1. 运行anisebot
 2. 运行mcl
 3. anisebot命令行出现如下语句即为连接成功
     ```
    [INFO] uvicorn | ('这里是ip', 这里是端口) - "WebSocket /onebot/v11/" [accepted]
    [INFO] nonebot | OneBot V11 | Bot 这里是账号 connected
    [INFO] websockets | connection open
     ```
