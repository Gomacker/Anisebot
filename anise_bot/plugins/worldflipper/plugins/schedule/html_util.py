import datetime
import io
import time
from typing import List

import imgkit
from PIL import Image

from anise_core import RES_PATH

tag2color = {
    '活动': 'rgba(236, 0, 4, 0.7)',
    '兑换': 'rgba(0, 161, 253, 0.7)',
    '卡池': 'rgba(0, 161, 253, 0.7)',
    '限定卡池': 'rgba(0, 161, 253, 0.7)',
    '定期重置': 'rgba(126, 3, 186, 0.7)',
    '体力药过期': 'rgba(126, 3, 186, 0.7)',
    '千里眼': 'rgba(249, 200, 0, 0.7)',
    '贩售': 'rgba(249, 200, 0, 0.7)',
    '停服维护': 'rgba(126, 3, 186, 0.7)',
    '版本更新': 'rgba(126, 3, 186, 0.7)',
    '运营活动': 'rgba(126, 3, 186, 0.7)'
}


def entry(progress, tag, title, date, dateless, tag2):
    progress = '{:.2%}'.format(1 - progress)
    color = tag2color[tag] if tag in tag2color else 'rgba(0, 0, 0, 0.7)'
    return f'''
    <div class="main entry">
        <div class="progress" style="right: {progress}"></div>
        <div class="name entry">
            <p class="label" style="background-color: {color};">{tag2}{tag}</p>
            <p class="title entry">{title}</p>
        </div>
        <div class="main part_right">
            <p class="time part_right">{date}</p>
            <p class="remain part_right">{dateless}</p>
        </div>
    </div>
    '''


def sub_body(main_title, entry_list: List):
    return f'''
    <div class="main sub_body">
        <header class="header">
            {main_title}
        </header>
        {''.join(entry_list)}
    </div>
    '''


def get_sub_title(a: datetime.timedelta):
    if a.days <= 7:
        return 1
    elif a.days <= 30:
        return 2
    else:
        return 0


def get_entries(qly: bool, info):
    t = time.time()
    entries = {
        '7天内': [],
        '30天内': [],
        '更远': []
    }
    for entry_ in info['list'][1]['list']:
        if t > entry_['timeEnd']:
            continue
        if qly and entry_['tag'] != '千里眼':
            continue
        elif not qly and entry_['tag'] == '千里眼':
            continue
        # progress_ = 0
        # sub_title = 0
        entry_['timeEnd'] = entry_['timeEnd'] / 1000
        entry_['edit'] = entry_['edit'] / 1000

        if 'timeEnd' not in entry_:
            progress_ = 0
            progress_ = (entry_['edit'] - time.time()) / progress_
            date_ = datetime.datetime.fromtimestamp(entry_['timeStart'])
            dateless_ = date_ - datetime.datetime.now()
            sub_title = get_sub_title(dateless_)
            date_ = date_.strftime('%m月%d日%H:%M')
            dateless_text = f'还有{dateless_.days}天'

        if 'timeStart' not in entry_:
            progress_ = entry_['edit'] - entry_['timeEnd']
            progress_ = (entry_['edit'] - time.time()) / progress_
            date_ = datetime.datetime.fromtimestamp(entry_['timeEnd'])
            dateless_ = date_ - datetime.datetime.now()
            sub_title = get_sub_title(dateless_)
            date_ = date_.strftime('%m月%d日%H:%M')
            dateless_text = f'剩余{dateless_.days}天'

        else:
            entry_['timeStart'] = entry_['timeStart'] / 1000

            if t > entry_['timeStart']:
                progress_ = entry_['timeStart'] - entry_['timeEnd']
                progress_ = (entry_['timeStart'] - time.time()) / progress_
                date_ = datetime.datetime.fromtimestamp(entry_['timeEnd'])
                dateless_ = date_ - datetime.datetime.now()
                sub_title = get_sub_title(dateless_)
                date_ = date_.strftime('%m月%d日 %H:%M')
                dateless_text = f'剩余{dateless_.days}天'
            else:
                progress_ = 0
                date_ = datetime.datetime.fromtimestamp(entry_['timeStart'])
                dateless_ = date_ - datetime.datetime.now()
                sub_title = get_sub_title(dateless_)
                date_ = date_.strftime('%m月%d日%H:%M')
                dateless_text = f'{dateless_.days}天后开始'
        tag2 = entry_['tag2'] if 'tag2' in entry_ else ''
        if sub_title == 1:
            entries['7天内'].append((progress_, entry_['tag'], entry_['title'], date_, dateless_text, dateless_, tag2))
        elif sub_title == 2:
            entries['30天内'].append((progress_, entry_['tag'], entry_['title'], date_, dateless_text, dateless_, tag2))
        elif sub_title == 0:
            entries['更远'].append((progress_, entry_['tag'], entry_['title'], date_, dateless_text, dateless_, tag2))
    return entries


def gen_pic(qly: bool, info):
    """
    TODO 注：大可转成playwright抓取
    ps: 不过我本来打算自写UI转化再重整了所以就先不补了
    """
    s = open(RES_PATH / 'worldflipper' / 'schedule.html', 'r', encoding='UTF-8').read()

    t = datetime.datetime.now()
    # entries = {
    #     '7天内': [],
    #     '30天内': [],
    #     '更远': []
    # }
    total_content = f'<h2 style="margin-top: 20px;">更新时间：{t.strftime("%Y-%m-%d, %H:%M:%S")}</h2>'
    if not qly:
        total_content += f'''
        <h1>活动一览</h1>
        '''

        for k, v in get_entries(False, info).items():
            v.sort(key=lambda x: x[5])
            total_content += sub_body(k, list(map(lambda x: entry(x[0], x[1], x[2], x[3], x[4], x[6]), v)))
    if qly:
        total_content += f'''
        <h1>千里眼</h1>
        <p class="qly" style="color: crimson;">千里眼基于过往活动数据预测，最终活动请以官宣内容为准</p>
        '''
        for k, v in get_entries(True, info).items():
            v.sort(key=lambda x: x[5])
            total_content += sub_body(k, list(map(lambda x: entry(x[0], x[1], x[2], x[3], x[4], x[6]), v)))
    config = imgkit.config(wkhtmltoimage=RES_PATH / 'tool' / 'wkhtmltoimage.exe')
    options = {'width': 672}
    return Image.open(io.BytesIO(
        imgkit.from_string(s.replace('{{}}', total_content), False, options=options, config=config)
    ))
