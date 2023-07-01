@echo off
pip install poetry -i https://pypi.tuna.tsinghua.edu.cn/simple
poetry install
poetry run playwright install

pause