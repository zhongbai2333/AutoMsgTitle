from typing import Any, Dict, Optional

from mcdreforged.api.all import PluginServerInterface, Serializable

class Config(Serializable):
    debug: bool = False
    afk_time: int = 300
    bot_prefix: str = "bot_"