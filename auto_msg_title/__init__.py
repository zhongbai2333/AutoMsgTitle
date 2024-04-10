from mcdreforged.api.all import *
import time

from .config import Config

global __mcdr_server, player_info, stop_status


@new_thread("GetPos")
def getpos_player():
    global player_info
    time.sleep(1)
    while True:
        result = rcon_execute(f"execute as @a run data get entity @s Pos")
        if result:
            for i in result.split("]"):
                if i != "":
                    n_result = i.split()
                    player_name = n_result[0]
                    xyz_now = [int(float(n_result[-3][1:-2])), int(float(n_result[-2][:-2])), int(float(n_result[-1][:-1]))]
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
                        player_info[player_name] = [xyz_now,int(time.time()),False]
        if not stop_status: 
            time.sleep(1)
        else:
            break


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
        getpos_player()


def on_unload(_):
    global stop_status
    stop_status = True


def on_server_startup(_):
    getpos_player()


# 在线玩家检测
def on_player_joined(_, player, __):
    global player_info
    if player not in player_info.keys():
        player_info[player] = [[0,0,0],int(time.time()),False]


def on_player_left(_, player):
    global player_info
    if player in player_info.keys():
        del player_info[player]