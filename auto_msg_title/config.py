from typing import Any, Dict, Optional

from mcdreforged.api.all import Serializable


class Config(Serializable):
    # 0:guest 1:user 2:helper 3:admin 4:owner
    permission: Dict[str, int] = {
        "help": 0,
        "list": 0,
        "add": 3,
        "del": 3,
        "msg": 2,
        "info": 1,
    }
    debug: bool = False
    afk_time: int = 300
    bot_prefix: str = "bot_"
