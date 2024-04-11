from mcdreforged.api.all import *
import time

from .config import Config

global __mcdr_server, player_info, stop_status, online_player_list


@new_thread("GetPos")
def getpos_player(reload: bool = False):
    global player_info, online_player_list
    time.sleep(1)
    while True:
        if player_info or reload:
            online_player_list = []
            result = rcon_execute(f"execute as @a run data get entity @s Pos")
            print(player_info)
            if result:
                for i in result.split("]")[:-1]:
                    n_result = i.split()
                    online_player_list.append(n_result[0])
                    edit_player_info(n_result[0], [int(float(n_result[-3][1:-2])), int(float(n_result[-2][:-2])), int(float(n_result[-1][:-1]))])
                for i in list(set(list(player_info.keys())) - set(online_player_list)):
                    del player_info[i]
        if not stop_status: 
            reload = False
            time.sleep(1)
        else:
            break


def edit_player_info(player_name: str, xyz_now: list):
    if player_name in player_info.keys():
        if player_info[player_name][0] == xyz_now:
            if int(time.time()) - player_info[player_name][1] >= config.afk_time and not player_info[player_name][2]:
                player_info[player_name][2] = True
                __mcdr_server.say(f"§7{player_name} 开始 AFK")
        else:
            if player_info[player_name][2]:
                __mcdr_server.say(f"§7{player_name} 退出 AFK 共用时 {int(time.time()) - player_info[player_name][1]} 秒")
            player_info[player_name] = [xyz_now,int(time.time()),False]
    else:
        if config.bot_prefix not in player_name:
            player_info[player_name] = [xyz_now,int(time.time()),False]


# RCON相关
def rcon_execute(command: str):
    global stop_status
    if __mcdr_server.is_rcon_running():
        result = __mcdr_server.rcon_query(command)
        if result == '':
            result = None
    else:
        __mcdr_server.logger.error("服务器未启用RCON！插件无法正常工作！请开启之后重载插件！")
        stop_status = True
        result = None
    return result


def on_load(server: PluginServerInterface, _):
    global __mcdr_server, player_info, stop_status, config
    __mcdr_server = server
    player_info = {}
    stop_status = False
    config = __mcdr_server.load_config_simple(target_class=Config)
    if __mcdr_server.is_server_startup():
        getpos_player(True)


def on_unload(_):
    global stop_status
    stop_status = True


def on_server_startup(_):
    getpos_player()


# 在线玩家检测
def on_player_joined(_, player, __):
    global player_info
    if player not in player_info.keys() and config.bot_prefix not in player:
        player_info[player] = [[0,0,0],int(time.time()),False]


def on_player_left(_, player):
    global player_info
    if player in player_info.keys():
        del player_info[player]