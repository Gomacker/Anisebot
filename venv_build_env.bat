@echo off
py -m venv venv
call .\venv\Scripts\activate
pip install nonebot2[fastapi] -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install nonebot-adapter-onebot -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install Pillow httpx toml pypinyin fuzzywuzzy zhconv -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple
playwright install chromium
pause