import json
import urllib.parse
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from anise_core import MAIN_URL, DATA_PATH
from ..anise.manager import manager
from ..anise.object import GameObject
from ..anise.resource import ResourceTypeImage, ResourceGroupNetwork, ResourceGroupLocal


def _url_getter_worldflipper(suffix: str):
    def temp(id_: str, obj: GameObject):
        url = urllib.parse.urljoin(
            MAIN_URL, f"/static/{obj.type_id()}/{id_}/{obj.resource_id}.{suffix}"
        )
        print(url)
        return url

    return temp


class Element(Enum):
    ALL = -1
    FIRE = 0
    WATER = 1
    THUNDER = 2
    WIND = 3
    LIGHT = 4
    DARK = 5


class SpecialityType(Enum):
    KNIGHT = 0
    FIGHTER = 1
    RANGED = 2
    SUPPORTER = 3
    SPECIAL = 4


class Race(Enum):
    HUMAN = 0
    BEAST = 1
    MYSTERY = 2
    ELEMENT = 3
    DRAGON = 4
    MACHINE = 5
    DEVIL = 6
    PLANTS = 7
    AQUATIC = 8
    UNDEAD = 9


class LeaderAbilityInfo(BaseModel):
    name: str
    description: str


class SkillBase(BaseModel):
    name: str
    weight: int
    description: str


class Character(GameObject):
    @classmethod
    def type_id(cls) -> str:
        return "worldflipper/character"

    class Res:
        square212x_0__ = ResourceGroupNetwork(
            "square212x/base", ResourceTypeImage, _url_getter_worldflipper("png")
        )
        square212x_0 = ResourceGroupLocal("square212x/base", ResourceTypeImage, "png")
        square212x_1 = ResourceGroupLocal(
            "square212x/awakened", ResourceTypeImage, "png"
        )
        full_0 = ResourceGroupLocal("full/base", ResourceTypeImage, "png")
        full_1 = ResourceGroupLocal("full/awakened", ResourceTypeImage, "png")
        full_resized_0 = ResourceGroupLocal(
            "full_resized/base", ResourceTypeImage, "png"
        )
        full_resized_1 = ResourceGroupLocal(
            "full_resized/awakened", ResourceTypeImage, "png"
        )
        party_main = ResourceGroupLocal("party_main", ResourceTypeImage, "png")
        party_unison = ResourceGroupLocal("party_unison", ResourceTypeImage, "png")
        pixelart_special = ResourceGroupLocal(
            "pixelart/special", ResourceTypeImage, "gif"
        )
        pixelart_walk_front = ResourceGroupLocal(
            "pixelart/walk_front", ResourceTypeImage, "gif"
        )

    id: str
    names: list[str]
    rarity: int
    element: Element
    type: SpecialityType
    # race: list[Race]
    race: str
    # gender: Gender
    gender: str  # 因为莉莉的原因，暂时不做枚举

    status_data: str

    leader_ability: LeaderAbilityInfo
    skill: SkillBase

    abilities: list[str]
    cv: str
    description: str
    obtain: str
    tags: list[str]

    server: Optional[str] = None


class Equipment(GameObject):
    @classmethod
    def type_id(cls) -> str:
        return 'worldflipper/equipment'

    class Res:
        pass

    id: str
    names: list[str]
    rarity: int
    element: Element
    status_data: str

    abilities: list[str]

    description: str
    obtain: str
    tags: list[str]

    server: Optional[str] = None


def load_from_json(path: Path, type_: type[GameObject]):
    manager.register_type(type_)
    data: dict = json.loads(path.read_text('utf-8'))
    for id_, item_data in data.items():
        obj = type_.parse_obj({'id': id_, **item_data})
        manager.register(id_, obj)


def load_all():
    character_path = DATA_PATH / 'object' / 'os' / 'character.json'
    equipment_path = DATA_PATH / 'object' / 'os' / 'equipment.json'

    load_from_json(character_path, Character)
    load_from_json(equipment_path, Equipment)


load_all()
