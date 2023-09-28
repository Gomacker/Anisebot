from manager import manager
from object import GameObject
from resource import ResourceGroup, ResourceType

manager.register_type(GameObject)

manager.res.register(GameObject, ResourceGroup('square212x', ResourceType.PNG))
manager.res.register(GameObject, ResourceGroup('full', ResourceType.PNG))
manager.res.register(GameObject, ResourceGroup('full_resized', ResourceType.PNG))
manager.res.register(GameObject, ResourceGroup('party_main', ResourceType.PNG))
manager.res.register(GameObject, ResourceGroup('party_unison', ResourceType.PNG))
manager.res.register(GameObject, ResourceGroup('pixelart/special', ResourceType.GIF))
manager.res.register(GameObject, ResourceGroup('pixelart/walk_front', ResourceType.GIF))
