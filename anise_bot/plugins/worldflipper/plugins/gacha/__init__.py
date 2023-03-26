try:
    import ujson as json
except ModuleNotFoundError:
    import json
import os
from collections import defaultdict

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment

from anise_core.worldflipper import wfm
from .gacha import Gacha, GACHA_POOL_CONFIG_PATH, GACHA_POOL_CONFIG
from ..... import utils
from .....service import Service
from .....utils import pic2b64, FreqLimiter, DailyCountLimiter

sv = Service('worldflipper.gacha')

daily_max: int = 0

_group_pool = dict()


def dump_pool_config():
    GACHA_POOL_CONFIG.write_text(json.dumps({
        'daily_limit': jewel_lmt.max,
        'group_pool': _group_pool
    }, ensure_ascii=False, indent=2), 'utf-8')


if not GACHA_POOL_CONFIG.exists():
    os.makedirs(GACHA_POOL_CONFIG.parent, exist_ok=True)
    GACHA_POOL_CONFIG.write_text(json.dumps({}))
with open(GACHA_POOL_CONFIG, 'r', encoding='utf-8') as f:
    data = json.loads(f.read())
    if 'group_pool' not in data:
        data['group_pool'] = {}
    if 'daily_limit' not in data:
        data['daily_limit'] = 3000
    _group_pool = {int(k): v for k, v in data['group_pool'].items()}
    jewel_lmt = DailyCountLimiter('gacha_jewel', data['daily_limit'])
    dump_pool_config()
    # _group_pool = json.loads(GACHA_POOL_CONFIG.read_text('utf-8'))

_group_pool = defaultdict(lambda: 'default', _group_pool)
action_lmt = FreqLimiter(4)


@sv.on_fullmatch(('卡池资讯', '卡池咨询'))
async def gacha_info(bot: Bot, e: GroupMessageEvent):
    ga = Gacha(_group_pool[e.group_id])
    msg = MessageSegment.text(f'本群组加载的卡池如下: \n')
    msg += '卡池up:\n'
    if ga.type == 'armament':
        for sgm in [MessageSegment.image(pic2b64(wfm.get_armament(up).icon(size=62))) for up in ga.star5_up]:
            msg += sgm
    else:
        for sgm in [MessageSegment.image(pic2b64(wfm.get_unit(up).icon(size=62))) for up in ga.star5_up]:
            msg += sgm
    msg += f'UP角色合计={ga.up5_prob_single * len(ga.star5_up * 100)}% 5★概率={ga.star5_prob * 100}%'
    await bot.send(e, msg)


@sv.on_prefix(('切换卡池',))
async def set_pool(bot: Bot, e: GroupMessageEvent):
    if not (bool(Service.OWNER(bot, e)) or bool(Service.ADMIN(bot, e)) or bool(Service.SUPERUSER(bot, e))):
        await bot.send(e, '没有足够的权限切换本群卡池')
        return
    pool_name = utils.normalize_str(e.get_plaintext())
    if pool_name in [x[:-5] for x in os.listdir(GACHA_POOL_CONFIG_PATH)]:
        _group_pool[e.group_id] = pool_name
        dump_pool_config()
        await bot.send(e, f'卡池已切换成{pool_name}了')
        await gacha_info(bot, e)
    else:
        await bot.send(e, '没有找到这个预载卡池')


@sv.on_prefix(('bc卡池',))
async def bc_pool(bot: Bot, e: GroupMessageEvent):
    if not Service.SUPERUSER(bot, e):
        return
    pool_name = utils.normalize_str(e.get_plaintext())
    if pool_name in [x[:-5] for x in os.listdir(GACHA_POOL_CONFIG_PATH)]:
        await bot.send(e, f'卡池{pool_name}已广播至所有群')
        for g in _group_pool:
            _group_pool[g] = pool_name
        dump_pool_config()

        ga = Gacha(pool_name)
        await sv.broadcast(
            f'卡池已广播，' +
            f'本群组加载的卡池如下: \n' +
            '卡池up: \n' +
            ' '.join([str(MessageSegment.image(
                pic2b64(wfm.get_armament(up).icon(size=62))
                if ga.type == 'armament' else
                pic2b64(wfm.get_unit(up).icon(size=62))
            )) for up in ga.star5_up]) +
            f'UP角色合计={ga.up5_prob_single * len(ga.star5_up * 100)}% 5★概率={ga.star5_prob * 100}%',
            priority_group=(e.group_id,))

    else:
        await bot.send(e, '没有找到这个预载卡池')


def gen_team_pic(object_list, size=56):
    num = len(object_list)
    des = Image.new('RGBA', (num * (size + 2), size), 'white')
    for i, unit in enumerate(object_list):
        src = unit.icon(size=size)
        des.paste(src, (i*(size + 2), 0), src)
    return des


@sv.on_prefix(('单抽', '單抽'))
async def _(bot: Bot, e: GroupMessageEvent):
    if len(e.get_plaintext()) > 6:
        return
    if not jewel_lmt.check(e.user_id):
        await bot.send(
            e,
            Service.get_send_content('worldflipper.gacha.gacha_failed').format(max=jewel_lmt.max),
            reply_message=True
        )
        return
    jewel_lmt.increase(e.user_id, 150)
    chara = Gacha(_group_pool[e.group_id]).gacha_select(1)[0]
    await bot.send(
        e,
        MessageSegment.text(Service.get_send_content('worldflipper.gacha.gacha_1')) +
        MessageSegment.image(pic2b64(chara.icon(size=62), format_="JPEG")) +
        f'\n{chara.name} {"★" * chara.rarity}',
        reply_message=True
    )
    await wfm.statistic.add('gacha.count')


@sv.on_prefix(('十连', '十連'))
async def _(bot: Bot, e: GroupMessageEvent):
    if len(e.get_plaintext()) > 6:
        return
    if not jewel_lmt.check(e.user_id):
        await bot.send(
            e,
            Service.get_send_content('worldflipper.gacha.gacha_failed').format(max=jewel_lmt.max),
            reply_message=True
        )
        return
    jewel_less = jewel_lmt.max - jewel_lmt.get(e.user_id)
    g = Gacha(_group_pool[e.group_id])
    if jewel_less >= 1500:
        jewel_lmt.increase(e.user_id, 1500)
        await wfm.statistic.add('gacha.count', 10)
        result = g.gacha_select(10)
        text = Service.get_send_content('worldflipper.gacha.gacha_10')
    else:
        jewel_lmt.increase(e.user_id, jewel_less)
        result = g.gacha_select(jewel_less // 150)
        await wfm.statistic.add('gacha.count', jewel_less // 150)
        text = Service.get_send_content('worldflipper.gacha.gacha_less').format(jewel_less=jewel_less, count_less=jewel_less // 150)

    text += MessageSegment.image(pic2b64(utils.concat_pic([gen_team_pic(result[:5]), gen_team_pic(result[5:])]), format_='JPEG'))
    await bot.send(e, text, reply_message=True)


@sv.on_prefix(('抽干', '抽乾', '梭哈'))
async def _(bot: Bot, e: GroupMessageEvent):
    if len(e.get_plaintext()) > 6:
        return
    print(f'抽干事件:')
    print(f'抽干来源: g{e.group_id}, q{e.user_id}')
    print(f'抽干接收: q{e.self_id}, m{e.message_id}')
    if not jewel_lmt.check(e.user_id):
        await bot.send(
            e,
            Service.get_send_content('worldflipper.gacha.gacha_failed').format(max=jewel_lmt.max),
            reply_message=True
        )
        return
    if e.group_id not in _group_pool:
        _group_pool[e.group_id] = _group_pool.default_factory()
    g = Gacha(_group_pool[e.group_id])
    jewel_less = jewel_lmt.max - jewel_lmt.get(e.user_id)
    gacha_count = jewel_less // 150
    units = g.gacha_select(gacha_count)
    await wfm.statistic.add('gacha.count', gacha_count)
    if None in units:
        await bot.send(e, MessageSegment.reply(e.message_id) + '卡池设置不完整，请检查卡池配置')
    else:
        jewel_lmt.increase(e.user_id, jewel_less)
        text = Service.get_send_content('worldflipper.gacha.gacha_all').format(jewel=jewel_less, count=jewel_less // 150)
        text += MessageSegment.image(pic2b64(utils.concat_pic(
            [gen_team_pic(units[i:i+5]) for i in range(0, len(units), 5)]
        ), format_='JPEG'))
        await bot.send(e, text, reply_message=True)


@sv.on_prefix(('氪金',))
async def kakin(bot: Bot, ev: GroupMessageEvent):
    if await Service.SUPERUSER(bot, ev):
        count = 0
        for m in ev.message:
            if str(m) == 'all':
                jewel_lmt.count = defaultdict(int)
                await bot.send(ev, f'已重置抽卡次数啦（')
                return
            if str(m).isdigit():
                jewel_lmt.reset(eval(str(m)))
                return
            if m.type == 'at' and m.data['qq'] != 'all':
                uid = int(m.data['qq'])
                jewel_lmt.reset(uid)
                count += 1
        if count:
            await bot.send(ev, f"已为{count}位用户充值完毕！谢谢惠顾～")
    else:
        pass


@sv.on_prefix(('吸金',))
async def xikin(bot: Bot, ev: GroupMessageEvent):
    if not await Service.SUPERUSER(bot, ev):
        return
    count = 0
    for m in ev.message:
        if m.type == 'at' and m.data['qq'] != 'all':
            uid = int(m.data['qq'])
            jewel_lmt.increase(uid, jewel_lmt.max)
            count += 1
    if count:
        await bot.send(ev, f"已为{count}位用户扣款完毕！谢谢惠顾～")
