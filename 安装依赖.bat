chcp 65001
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
nb driver install nonebot2[fastapi]
nb adapter install nonebot-adapter-onebot
deactivate
pause