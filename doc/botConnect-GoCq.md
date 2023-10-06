# Go-CqHttp

## 1、资源
[unidbg-fetch-qsign](https://github.com/rhwong/unidbg-fetch-qsign-onekey)

[go-cqhttp](https://github.com/Mrs4s/go-cqhttp)


## 2、安装
1. 安装签名服务器

    运行Start_Qsign.bat

    全默认后获取api地址 `http://127.0.0.1:13579`，默认key `1145141919810`
2. 安装go-cqhttp
    运行go-cqhttp.bat

    选择3反向ws通讯后生成config.yml


## 3、配置
1. 修改配置

    更改config.yml中的账号密码以及刚刚获取的api地址和key

    并且开启自动刷新登录

    修改反向代理有关配置

    ```
    servers:
        universal:ws://127.0.0.1:8080/onebot/v11/
    ```


## 4、连接Anisebot
1. 运行anisebot
2. 运行go-cqhttp，完成ticket验证
3. anisebot命令行出现如下语句即为连接成功
     ```
    [INFO] uvicorn | ('这里是ip', 这里是端口) - "WebSocket /onebot/v11/" [accepted]
    [INFO] nonebot | OneBot V11 | Bot 这里是账号 connected
    [INFO] websockets | connection open
     ```
