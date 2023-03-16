import hashlib
import json
import os
from pathlib import Path

from PIL import Image

from anise_core import RES_PATH
from anise_core.worldflipper import WorldflipperObject, Unit, Armament

ICON_REPLACES: dict = {
    '火属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'fire.png',
    '水属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'water.png',
    '雷属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'thunder.png',
    '风属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'wind.png',
    '光属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'light.png',
    '暗属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'dark.png',
    '作为主要角色编成：': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'main.png'
}


class WikiPageGenerator:
    def __init__(self, obj: WorldflipperObject, make_icon: bool = True, awaken: bool = False):
        self.obj: WorldflipperObject = obj
        self.make_icon: bool = make_icon
        self.awaken: bool = awaken

        self.replace_dict_local: dict = {
            '火属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'fire.png',
            '水属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'water.png',
            '雷属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'thunder.png',
            '风属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'wind.png',
            '光属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'light.png',
            '暗属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'dark.png',
            '作为主要角色编成：': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'main.png'
        }
        self.role2name: dict = {
            0: '剑士',
            1: '格斗',
            2: '射击',
            3: '辅助',
            4: '特殊',
        }
        self.race2name: dict = {
            'Human': '人',
            'Beast': '兽',
            'Mystery': '妖',
            'Element': '精灵',
            'Dragon': '龙',
            'Machine': '机械',
            'Devil': '魔',
            'Plants': '植物',
            'Aquatic': '水栖',
            'Undead': '不死',
            'Breakableblock': '可破坏的障碍',
        }

    @staticmethod
    def _make_enter(s: str):
        s = s.replace('\n', '</p><p>')
        return s

    def _make_icon(self, s: str):
        for k, v in self.replace_dict_local.items():
            s = s.replace(
                k,
                f''' <img class="desc-icon" src="file:///{v}"> '''
            )
        return s

    def get_code(self) -> str:
        """
        TODO 在Lite版中转用直接图版，需要时自行实现
        """
        h = ''
        if isinstance(self.obj, Unit):
            template = (RES_PATH / 'worldflipper' / 'unit_info.html').read_text('utf-8')
            kwargs = dict()
            kwargs['{{ LeaderAbility }}'] = self.obj.leader_ability
            kwargs['{{ Skill }}'] = self.obj.skill_description
            kwargs['{{ Ability1 }}'] = self.obj.ability1
            kwargs['{{ Ability2 }}'] = self.obj.ability2
            kwargs['{{ Ability3 }}'] = self.obj.ability3
            for k, v in kwargs.items():
                template = template.replace(k, self._make_enter(str(v)))
            kwargs.clear()
            if self.obj.ability4:
                kwargs['{{ Ability4 }}'] = f'''
                <tr class="extra_ab">
                    <td class="text-center" rowspan="1" colspan="2" style="vertical-align: middle;">
                        <p style="line-height: 39px; margin-bottom: 0;">
                            能力4
                        </p>
                    </td>
                    <td rowspan="1" colspan="6">
                        <p>
                            {self._make_enter(self.obj.ability4)}
                        </p>
                    </td>
                </tr>'''
            else:
                kwargs['{{ Ability4 }}'] = ''

            if self.obj.ability5:
                kwargs['{{ Ability5 }}'] = f'''
                <tr class="extra_ab">
                    <td class="text-center" rowspan="1" colspan="2" style="vertical-align: middle;">
                        <p style="line-height: 39px; margin-bottom: 0;">
                            能力5
                        </p>
                    </td>
                    <td rowspan="1" colspan="6">
                        <p>
                            {self._make_enter(self.obj.ability5)}
                        </p>
                    </td>
                </tr>'''
            else:
                kwargs['{{ Ability5 }}'] = ''

            if self.obj.ability6:
                kwargs['{{ Ability6 }}'] = f'''
                <tr class="extra_ab">
                    <td class="text-center" rowspan="1" colspan="2" style="vertical-align: middle;">
                        <p style="line-height: 39px; margin-bottom: 0;">
                            能力6
                        </p>
                    </td>
                    <td rowspan="1" colspan="6">
                        <p>
                            {self._make_enter(self.obj.ability6)}
                        </p>
                    </td>
                </tr>'''
            else:
                kwargs['{{ Ability6 }}'] = ''
            for k, v in kwargs.items():
                template = template.replace(k, str(v))
            kwargs.clear()
            if self.make_icon:
                template = self._make_icon(template)

            icon_url = RES_PATH / 'worldflipper' / 'unit' / 'square212x' / 'base' / f'{self.obj.extractor_id}.png'
            icon_url = f'file:///{icon_url}'
            rarity_url = RES_PATH / 'worldflipper' / 'ui' / 'star' / f'star{self.obj.rarity}.png'
            rarity_url = f'file:///{rarity_url}'
            element_url = RES_PATH / 'worldflipper' / 'ui' / 'icon' / 'normal' / f'{self.obj.element.en_name}.png'
            element_url = f'file:///{element_url}'
            kwargs['{{ unit_id }}'] = ''
            kwargs['{{ unit_url }}'] = icon_url
            kwargs['{{ rarity_url }}'] = rarity_url
            kwargs['{{ element_url }}'] = element_url
            kwargs['{{ Sever }}'] = self.obj.source_id
            kwargs['{{ Role }}'] = self.role2name.get(self.obj.pf_type, self.obj.pf_type)
            kwargs['{{ Race }}'] = ' / '.join([self.race2name.get(x, x) for x in self.obj.race.split(',')])
            kwargs['{{ SubName }}'] = self.obj.sub_name
            kwargs['{{ JPName }}'] = self.obj.jp_name
            kwargs['{{ ZHName }}'] = self.obj.zh_name

            kwargs['{{ LeaderAbilityName }}'] = self.obj.leader_ability_name
            kwargs['{{ SkillName }}'] = self.obj.skill_name
            kwargs['{{ SkillWeight }}'] = self.obj.skill_weight

            mhp, atk = self.obj.get_status(self.obj.nature_max_level)
            mmhp, matk = self.obj.get_status(100)

            kwargs['{{ Mhp }}'] = mhp
            kwargs['{{ Atk }}'] = atk
            kwargs['{{ MhpMax }}'] = mmhp
            kwargs['{{ AtkMax }}'] = matk

            kwargs['{{ Cv }}'] = '无' if self.obj.cv == '(None)' else self.obj.cv
            # print(template)
            for k, v in kwargs.items():
                template = template.replace(k, str(v))
            kwargs.clear()
            bg_url = RES_PATH / 'worldflipper' / 'ui' / 'wikipage_background.png'
            bg_url = f'file:///{bg_url}'.replace('\\', '/')
            template = '''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Title</title>
                <link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/3.4.1/css/bootstrap.min.css" crossorigin="anonymous">
                <script src="https://cdn.bootcdn.net/ajax/libs/jquery/3.6.1/jquery.min.js" crossorigin="anonymous"></script>
                <script src="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/3.4.1/js/bootstrap.js" crossorigin="anonymous"></script>
                <style>
                    .testa p{
                        margin: 1px 0;
                        align-self: center;
                    }
                    p{
                        margin-bottom: 0;
                        line-height: 20px;
                        font-size: 14px;
                    }
                    .desc-icon{
                        width: 16px;
                        vertical-align: text-bottom;
                    }
                    body{
                        font-family: "Microsoft YaHei",sans-serif;
                        background:url(''' + bg_url + ''') repeat;
                    }
                    .extra_ab{
                        color: gray;
                    }
                </style>
            </head>
            <body>
            <div class="container-fluid" style="padding-top: 15px;">
            ''' + template + '''
            </div>
            </body>
            </html>
            '''
            h += template
        elif isinstance(self.obj, Armament):
            # TODO 这是Legacy版本
            template = (RES_PATH / 'worldflipper' / 'armament_info.html').read_text('utf-8')
            kwargs = dict()

            for k, v in kwargs.items():
                template = template.replace(k, self._make_enter(str(v)))
            kwargs.clear()

            for k, v in kwargs.items():
                template = template.replace(k, str(v))
            kwargs.clear()

            bg_url = RES_PATH / 'worldflipper' / 'ui' / 'wikipage_background.png'
            bg_url = f'file:///{bg_url}'.replace('\\', '/')
            template = '''
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <title>Title</title>
                            <link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/3.4.1/css/bootstrap.min.css" crossorigin="anonymous">
                            <script src="https://cdn.bootcdn.net/ajax/libs/jquery/3.6.1/jquery.min.js" crossorigin="anonymous"></script>
                            <script src="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/3.4.1/js/bootstrap.js" crossorigin="anonymous"></script>
                            <style>
                                .testa p{
                                    margin: 1px 0;
                                    align-self: center;
                                }
                                p{
                                    margin-bottom: 0;
                                    line-height: 20px;
                                    font-size: 14px;
                                }
                                .desc-icon{
                                    width: 16px;
                                    vertical-align: text-bottom;
                                }
                                body{
                                    font-family: "Microsoft YaHei",sans-serif;
                                    background:url(''' + bg_url + ''') repeat;
                                }
                                .extra_ab{
                                    color: gray;
                                }
                            </style>
                        </head>
                        <body>
                        <div class="container-fluid" style="padding-top: 15px;">
                        ''' + template + '''
                        </div>
                        </body>
                        </html>
                        '''
            h += template
        else:
            pass
        return h

    def is_need_new(self) -> bool:
        """
        TODO 在Lite版中转用直接图版，需要自动生成的话自行实现
        检查数据哈希是否匹配，
        若匹配时返回Ture
        """
        hash_path = \
            RES_PATH / 'worldflipper' / 'wikipage' / self.obj.source_id / \
            ('unit' if isinstance(self.obj, Unit) else 'armament') / f'hash_data.json'
        os.makedirs(hash_path.parent, exist_ok=True)
        if not hash_path.exists():
            hash_path.write_text(json.dumps({}, ensure_ascii=False, indent=2))
        hash_data: dict = json.loads(hash_path.read_text('utf-8'))
        data_hash = hashlib.md5(str(self.obj.data()).encode()).hexdigest()
        # hash_data = {int(k): v for k, v in hash_data.items()}
        return hash_data.get(str(self.obj.id)) != data_hash

    def get_pic_path(self) -> Path:
        """
        获取图片路径
        """
        return RES_PATH / 'worldflipper' / 'wikipage' / \
            self.obj.source_id / ('unit' if isinstance(self.obj, Unit) else 'armament') / f'{self.obj.extractor_id}.png'

    async def get_pic(self, save=False) -> Image.Image:
        """
        在Lite版中转用直接图版
        """
        img = Image.open(self.get_pic_path())

        if save:
            img.save(
                RES_PATH / 'worldflipper' / 'wikipage' / self.obj.source_id /
                ('unit' if isinstance(self.obj, Unit) else 'armament') / f'{self.obj.extractor_id}.png'
            )
        return img
