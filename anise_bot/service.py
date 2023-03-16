import asyncio

try:
    import ujson as json
except ModuleNotFoundError:
    import json
import os
import random
from collections import defaultdict
from typing import Callable

import nonebot
from nonebot import on_startswith, on_notice, logger, on_message, on_request
from nonebot import permission as nb_permission
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Event, MessageSegment, Message, MessageEvent, \
    GroupRequestEvent, NotifyEvent, GroupBanNoticeEvent, GroupDecreaseNoticeEvent, PrivateMessageEvent
from nonebot.adapters.onebot.v11 import permission as onebot_permission
from nonebot.internal.rule import Rule

from anise_core import CONFIG_PATH
from .utils import FreqLimiter, normalize_str


async def _poke_checker(e: NotifyEvent) -> bool:
    d = e.dict()
    return d['target_id'] == e.self_id


class PackageChecker:
    def __init__(self, *checkers: Callable):
        self.checkers: list = list(checkers)

    async def __call__(self, e: MessageEvent) -> bool:
        for checker in self.checkers:
            if not await checker(e):
                return False
        return True


class _PrefixChecker:
    def __init__(self, prefix):
        if isinstance(prefix, str):
            prefix = (prefix,)
        self.prefix = prefix

    async def __call__(self, e: MessageEvent):
        tmsg = None
        for m in e.message:
            if m.type == 'text':
                tmsg = m
                break
        if tmsg:
            tmsg.data['text'] = normalize_str(tmsg.data['text'])
            for p in sorted(self.prefix, key=lambda x: len(x), reverse=True):
                if tmsg.data['text'].startswith(p):
                    tmsg.data['text'] = tmsg.data['text'].removeprefix(p)
                    logger.debug(f'True to prefix: {p} on {e.message_id}')
                    return True
            return False
        return False


class _SuffixChecker:
    def __init__(self, suffix):
        if isinstance(suffix, str):
            suffix = (suffix,)
        self.suffix = suffix

    async def __call__(self, e: MessageEvent):
        for m in e.message:
            if m.type == 'text':
                m.data['text'] = normalize_str(m.data['text'])
                for p in sorted(self.suffix, key=lambda x: len(x), reverse=True):
                    if m.data['text'].endswith(p):
                        m.data['text'] = m.data['text'].removesuffix(p)
                        return True
        return False


class _FullmatchChecker:
    def __init__(self, text):
        if isinstance(text, str):
            text = (text,)
        self.text = text

    async def __call__(self, e: MessageEvent):
        return normalize_str(e.get_plaintext()) in self.text


class OnlyBotChecker:
    def __init__(self, uid: int):
        self.uid = uid

    async def __call__(self, e: Event):
        return e.self_id == self.uid


GLOBAL_COOLDOWN: FreqLimiter = FreqLimiter(0)  # 公共CD
SILENT: FreqLimiter = FreqLimiter(60)  # bot静音 !注：禁言Bot可能会导致闷棍


class Service:
    ADMIN = onebot_permission.GROUP_ADMIN
    OWNER = onebot_permission.GROUP_OWNER
    SUPERUSER = nb_permission.SUPERUSER

    def __init__(self, name, default_enable=True):
        config = _load_config(name)
        self.name: str = name
        self.default_enable: bool = config.get('default_enable') if 'default_enable' in config else default_enable
        self.enable_group: set = set(config.get('enable_group', []))
        self.disable_group: set = set(config.get('disable_group', []))

        _services[self.name] = self
        _save_config(self)
        self.on_request_stack: dict[str, tuple[Bot or None, Event or None]] = defaultdict(tuple)

        self.on_send_stack: dict[Callable, int] = defaultdict(int)

    @staticmethod
    def get_send_content(message_key):
        path = CONFIG_PATH / 'message_contents.json'
        os.makedirs(path.parent, exist_ok=True)
        if not path.exists():
            path.write_text(json.dumps({}), 'utf-8')
        data = json.loads(path.read_text('utf-8'))
        result = None
        if message_key in data:
            result = data[message_key]

        if isinstance(result, list):
            return random.choice(result)
        elif isinstance(result, str):
            return result
        else:
            return message_key

    @property
    def bots(self):
        return nonebot.get_bots()

    @staticmethod
    def get_services() -> dict[str, "Service"]:
        return _services

    def set_enable(self, group_id: int):
        if not self.name.startswith('_'):
            self.enable_group.add(group_id)
            self.disable_group.discard(group_id)
            _save_config(self)

    def set_disable(self, group_id: int):
        if not self.name.startswith('_'):
            self.disable_group.add(group_id)
            self.enable_group.discard(group_id)
            _save_config(self)

    async def get_enable_group_and_bot(self) -> dict[int, list]:
        group_list: dict[int, list[Bot]] = defaultdict(list)
        for bot in self.bots.values():
            bot: Bot
            group_set = set(g['group_id'] for g in await bot.get_group_list())
            if self.default_enable:
                group_set -= self.disable_group
            else:
                group_set &= self.enable_group
            for group_id in group_set:
                group_list[group_id].append(bot)
        return group_list

    def check_enable(self, group_id: int) -> bool:
        enable = group_id in self.enable_group or (self.default_enable and group_id not in self.disable_group)
        return enable

    async def _service_checker(self, e: Event) -> bool:
        d = e.dict()
        return \
            ('group_id' in d and self.check_enable(d['group_id']) and SILENT.check(d['group_id'])) \
            or isinstance(e, PrivateMessageEvent)

    def on_prefix(self, prefix, **kwargs) -> Callable:
        if isinstance(prefix, str):
            prefix = (prefix,)
        checkers = [self._service_checker, _PrefixChecker(prefix)]
        if 'rule' in kwargs:
            if isinstance(kwargs['rule'], Rule):
                checkers += [d.call for d in kwargs['rule'].checkers]
            elif isinstance(kwargs['rule'], Callable):
                checkers += [checkers]
            elif isinstance(kwargs['rule'], list):
                checkers += checkers
            del kwargs['rule']
        print(checkers)
        rule = Rule(PackageChecker(*checkers))
        return on_message(rule=rule, **kwargs).handle()

    def on_suffix(self, suffix, **kwargs) -> Callable:
        if isinstance(suffix, str):
            suffix = (suffix,)
        checkers = [self._service_checker, _SuffixChecker(suffix)]
        if 'rule' in kwargs:
            if isinstance(kwargs['rule'], Rule):
                checkers += [d.call for d in kwargs['rule'].checkers]
            elif isinstance(kwargs['rule'], Callable):
                checkers += [checkers]
            elif isinstance(kwargs['rule'], list):
                checkers += checkers
            del kwargs['rule']
        print(checkers)
        rule = Rule(PackageChecker(*checkers))
        return on_message(rule=rule, **kwargs).handle()

    def on_fullmatch(self, text, **kwargs) -> Callable:
        if isinstance(text, str):
            text = (text,)
        checkers = [self._service_checker, _FullmatchChecker(text)]
        if 'rule' in kwargs:
            if isinstance(kwargs['rule'], Rule):
                checkers += [d.call for d in kwargs['rule'].checkers]
            elif isinstance(kwargs['rule'], Callable):
                checkers += [kwargs['rule']]
            elif isinstance(kwargs['rule'], list):
                checkers += kwargs['rule']
            del kwargs['rule']
        print(checkers)
        rule = Rule(PackageChecker(*checkers))
        return on_message(rule=rule, **kwargs).handle()

    # def scheduled_job(self, trigger, *args, **kwargs) -> Callable:
    #     return scheduler.scheduled_job(trigger, *args, **kwargs)

    def on_poke(self, **kwargs) -> Callable:
        return on_notice(rule=Rule(self._service_checker, _poke_checker)).handle()

    async def _broadcast_on(self, groups, msgs, interval_time, limit_count, priority_group):
        groups = sorted(groups.items(), key=lambda x: x[0] in priority_group, reverse=True)
        groups = random.sample(groups, limit_count) if limit_count > 0 else groups
        groups = {k: v for k, v in groups}
        for group_id, bots in groups.items():
            bot: Bot = random.choice(bots)
            try:
                for msg in msgs:
                    await asyncio.sleep(interval_time)
                    await bot.send_group_msg(group_id=group_id, message=msg)
            except Exception as e:
                pass

    async def broadcast_on(self, groups, msgs, interval_time=5, limit_count=0, priority_group=None):
        if priority_group is None:
            priority_group = []
        if isinstance(msgs, (str, MessageSegment, Message)):
            msgs = (msgs,)
        group_list = await self.get_enable_group_and_bot()
        group_list = {k: v for k, v in filter(lambda x: x[0] in groups, group_list.items())}
        await self._broadcast_on(group_list, msgs, interval_time, limit_count, priority_group)

    async def broadcast(self, msgs, interval_time=5, limit_count=0, priority_group=None):
        if priority_group is None:
            priority_group = []
        if isinstance(msgs, (str, MessageSegment, Message)):
            msgs = (msgs,)
        group_list = await self.get_enable_group_and_bot()
        await self._broadcast_on(group_list, msgs, interval_time, limit_count, priority_group)


_services: dict[str, Service] = dict()
_service_config_path = CONFIG_PATH / 'service'
os.makedirs(_service_config_path, exist_ok=True)


def _load_config(service_name: str):
    path = _service_config_path / f'{service_name.replace(".", "/")}.json'
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text('utf-8'))
    except Exception as e:
        logger.exception(e)
        return {}


def _save_config(service: Service):
    path = _service_config_path / f'{service.name.replace(".", "/")}.json'
    os.makedirs(path.parent, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "name": service.name,
                'default_enable': service.default_enable,
                'enable_group': list(service.enable_group),
                'disable_group': list(service.disable_group)
            },
            ensure_ascii=False, indent=2
        ),
        'utf-8'
    )
    # print(path)


sv_permissions = nb_permission.SUPERUSER | onebot_permission.GROUP_ADMIN | onebot_permission.GROUP_OWNER


@on_startswith(('开启',), permission=sv_permissions).handle()
async def _(bot: Bot, e: GroupMessageEvent):
    text = e.get_plaintext()[2:]
    if text:
        enabled = []
        for k in text.split():
            if k in _services:
                _services[k].set_enable(e.group_id)
                enabled.append(k)
        if enabled:
            await bot.send(e, '已开启: ' + '\n'.join(enabled))
        else:
            await bot.send(e, '未找到相关模块')


@on_startswith(('关闭',), permission=sv_permissions).handle()
async def _(bot: Bot, e: GroupMessageEvent):
    text = e.get_plaintext()[2:]
    if text:
        enabled = []
        for k in text.split():
            if k in _services:
                _services[k].set_disable(e.group_id)
                enabled.append(k)
        if enabled:
            await bot.send(e, '已关闭: ' + '\n'.join(enabled))
        else:
            await bot.send(e, '未找到相关模块')


@on_startswith(('静音',), permission=sv_permissions).handle()
async def _(bot: Bot, e: GroupMessageEvent):
    text = e.get_plaintext()[2:]
    if text.isdigit():
        SILENT.start_cd(e.group_id, int(text))
    elif not text:
        SILENT.start_cd(e.group_id, 60)
    else:
        pass


@on_request().handle()
async def _(bot: Bot, e: GroupRequestEvent):
    if e.sub_type == 'invite':
        await bot.send_private_msg(
            user_id=int(list(bot.config.superusers)[0]),
            message=Message(f'新收到1条群邀请: {e.group_id} from {e.user_id}')
        )


@on_notice().handle()
async def _(bot: Bot, e: GroupBanNoticeEvent):
    if e.sub_type == 'ban' and e.self_id == e.user_id and e.user_id != 0:
        await bot.send_private_msg(
            user_id=int(list(bot.config.superusers)[0]),
            message=Message(f'于群{e.group_id} 被 {e.operator_id} 禁言 {e.duration}s')
        )


@on_notice().handle()
async def _(bot: Bot, e: GroupDecreaseNoticeEvent):
    if e.sub_type == 'kick_me':
        await bot.send_private_msg(
            user_id=int(list(bot.config.superusers)[0]),
            message=Message(f'于群{e.group_id} 被 {e.operator_id} 踢出')
        )
