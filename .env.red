# 配置方法见 https://github.com/nonebot/adapter-red
LOG_LEVEL=INFO
DRIVER=~httpx+~websockets
RED_BOTS='
[
    {
        "port": "port",
        "token": "token",
        "host": "host"
    }
]
'