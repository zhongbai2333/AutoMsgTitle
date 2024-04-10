from typing import Any, Dict, Optional

from mcdreforged.api.all import PluginServerInterface, Serializable

class Config(Serializable):
    afk_time: int = 300
    debug: bool = False