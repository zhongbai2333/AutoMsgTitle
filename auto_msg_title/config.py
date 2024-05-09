from typing import Dict, Tuple

from mcdreforged.api.all import Serializable


class Config(Serializable):
    # 0:guest 1:user 2:helper 3:admin 4:owner
    permission: Dict[str, int] = {
        "help": 0,
        "list": 0,
        "add": 3,
        "del": 3,
        "move": 2,
        "msg": 2,
        "info": 1,
    }
    debug: bool = False
    afk_time: float = 300  # second
    back_region: float = 30  # second
    refresh_pos_time: float = 1 # second
    bot_prefix: str = "bot_"
