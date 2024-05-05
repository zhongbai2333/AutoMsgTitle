import time
from mcdreforged.api.all import *

from .config import Config
from .command_actions import CommandActions

global __mcdr_server, player_info, stop_status, online_player_list


# 创建新线程
@new_thread("GetPos")
def getpos_player(reload: bool = False):
    global player_info, online_player_list
    time.sleep(1)
    while not stop_status:
        # 判断服务器是否有人
        if player_info or reload:
            online_player_list = []
            p_num = 0
            result_pos = rcon_execute("execute as @a run data get entity @s Pos")
            result_dimension = rcon_execute(
                "execute as @a run data get entity @s Dimension"
            )
            # 判断RCON是否有回复
            if result_dimension:
                n_result_dimension = result_dimension.split('"')[:-1]
                for i in result_pos.split("]")[:-1]:
                    p_num += 1
                    n_result_pos = i.split()
                    online_player_list.append(n_result_pos[0])
                    edit_player_info(
                        n_result_pos[0],
                        [
                            int(float(n_result_pos[-3][1:-2])),
                            int(float(n_result_pos[-2][:-2])),
                            int(float(n_result_pos[-1][:-1])),
                        ],
                        n_result_dimension[2 * p_num - 1],
                    )
                # 清除不在在线列表的玩家
                for i in list(set(list(player_info.keys())) - set(online_player_list)):
                    del player_info[i]
        reload = False
        time.sleep(1)


def edit_player_info(player_name: str, xyz_now: list, dimension_now: str):
    if player_name in player_info.keys():
        if player_info[player_name][0] == xyz_now:
            if (
                int(time.time()) - player_info[player_name][2] >= config.afk_time
                and not player_info[player_name][3]
            ):
                player_info[player_name][3] = True
                __mcdr_server.say(f"§7{player_name} 开始 AFK")
        else:
            if player_info[player_name][3]:
                __mcdr_server.say(
                    f"§7{player_name} 退出 AFK 共用时 {int(time.time()) - player_info[player_name][2]} 秒"
                )
            player_info[player_name] = [xyz_now, dimension_now, int(time.time()), False]
    else:
        if config.bot_prefix not in player_name:
            player_info[player_name] = [xyz_now, dimension_now, int(time.time()), False]


def debug_print(msg: str):
    if config.debug:
        __mcdr_server.logger.info(msg)


# RCON相关
def rcon_execute(command: str):
    global stop_status
    if __mcdr_server.is_rcon_running():
        result = __mcdr_server.rcon_query(command)
        if result == "":
            result = None
    else:
        __mcdr_server.logger.error(
            "服务器未启用RCON！插件无法正常工作！请开启之后重载插件！"
        )
        stop_status = True
        result = None
    return result


# 插件入口
def on_load(server: PluginServerInterface, _):
    global __mcdr_server, player_info, stop_status, config, command_actions
    __mcdr_server = server
    player_info = {}
    stop_status = False
    # 加载设置
    config = __mcdr_server.load_config_simple(target_class=Config)
    # 创建命令系统
    CommandActions(__mcdr_server, config.permission)
    if __mcdr_server.is_server_startup():
        getpos_player(True)


# 插件卸载
def on_unload(_):
    global stop_status
    # 退出信号
    stop_status = True


def on_server_startup(_):
    getpos_player()


# 在线玩家检测
def on_player_joined(_, player, __):
    global player_info
    if player not in player_info.keys() and config.bot_prefix not in player:
        player_info[player] = [
            [0, 0, 0],
            "minecraft:overworld",
            int(time.time()),
            False,
        ]


def on_player_left(_, player):
    global player_info
    if player in player_info.keys():
        del player_info[player]
