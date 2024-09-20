import time
from typing import List, Tuple
from mcdreforged.api.all import *

from .config import Config
from .command_actions import CommandActions

global __mcdr_server, player_info, stop_status, online_player_list


@new_thread("GetPos")
def getpos_player(reload: bool = False):
    # 全局变量声明
    global player_info, online_player_list
    time.sleep(1)

    # 持续运行直到外部stop_status变量指示停止
    while not stop_status:
        # 如果有在线玩家信息或者触发了重载
        if player_info or reload:
            # 执行RCON命令获取所有玩家的位置
            result_pos = rcon_execute("execute as @a run data get entity @s Pos")
            # 执行RCON命令获取所有玩家的维度
            result_dimension = rcon_execute("execute as @a run data get entity @s Dimension")
            update_player_positions(result_pos, result_dimension)
        # 重置重载标志
        reload = False
        time.sleep(config.refresh_pos_time)


def update_player_positions(result_pos, result_dimension):
    global online_player_list
    online_player_list = []

    # 如果获取维度成功
    if result_dimension:
        dimensions = parse_dimensions(result_dimension)
        update_player_info_from_results(result_pos, dimensions)


def parse_dimensions(raw_dimension_data: str) -> List[str]:
    # 解析维度数据
    return raw_dimension_data.split('"')[:-1]


def update_player_info_from_results(position_data: str, dimensions: List[str]):
    online_player_names = []

    # 解析位置信息
    for player_count, position_info in enumerate(position_data.split("]")[:-1]):
        name, xyz = parse_position_info(position_info)
        online_player_names.append(name)
        xyz_as_int = list(map(lambda coord: int(float(coord)), xyz))
        dimension = dimensions[2 * (player_count + 1) - 1]
        edit_player_info(name, xyz_as_int, dimension)

    # 清除不再在线的玩家信息
    clear_offline_players(online_player_names)
    debug_print(f"PlayerInfo: {player_info}")


def parse_position_info(position_info: str) -> Tuple[str, List[str]]:
    parts = position_info.split()
    player_name = parts[0]
    xyz = [parts[-3][1:-2], parts[-2][:-2], parts[-1][:-1]]
    return player_name, xyz


def clear_offline_players(online_player_names: List[str]):
    # 对于不在在线列表中的玩家，从全局信息中删除
    for player in set(player_info.keys()) - set(online_player_names):
        del player_info[player]


def is_player_in_any_region(xyz, dimension):
    from .storage import global_data_json

    px, py, pz = xyz
    for region_name, region_data in global_data_json.items():
        if dimension != region_data["dimension_id"]:
            continue

        # 判断 2D 还是 3D
        if region_data["shape"] == 0:  # 2D
            x1, z1 = region_data["pos"]["from"]
            x2, z2 = region_data["pos"]["to"]
            # Check if player is within the 2D x-z plane bounds
            if min(x1, x2) <= px <= max(x1, x2) and min(z1, z2) <= pz <= max(z1, z2):
                return region_name
        elif region_data["shape"] == 1:  # 3D
            x1, y1, z1 = region_data["pos"]["from"]
            x2, y2, z2 = region_data["pos"]["to"]
            # Check if player is within the 3D x-y-z volume
            if (
                min(x1, x2) <= px <= max(x1, x2)
                and min(y1, y2) <= py <= max(y1, y2)
                and min(z1, z2) <= pz <= max(z1, z2)
            ):
                return region_name
    return None


def edit_player_info(player_name: str, xyz_now: List[int], dimension_now: str):
    current_time = int(time.time())
    player_data = player_info.get(
        player_name,
        {
            "position": None,
            "dimension": None,
            "last_update_time": current_time,
            "is_afk": False,
            "last_region": {},
        },
    )

    # 检查玩家位置是否未变更
    if player_data["position"] == xyz_now:
        if current_time - player_data["last_update_time"] >= config.afk_time:
            if not player_data["is_afk"]:
                player_data["is_afk"] = True
                __mcdr_server.say(f"§7{player_name} 开始 AFK")
    else:
        # 区域检查
        last_region = player_data["last_region"]
        in_region_now = is_player_in_any_region(xyz_now, dimension_now)
        if in_region_now not in last_region.keys() and in_region_now:
            print_title(in_region_now, player_name)
        for i in list(last_region.keys()):
            if current_time - last_region[i] > config.back_region:
                del last_region[i]
        if in_region_now:
            last_region[in_region_now] = current_time

        # AFK 检查
        if player_data["is_afk"]:
            __mcdr_server.say(
                f"§7{player_name} 退出 AFK 共用时 {current_time - player_data['last_update_time']} 秒"
            )

        # 更新变量
        player_data["position"] = xyz_now
        player_data["dimension"] = dimension_now
        player_data["last_update_time"] = current_time
        player_data["is_afk"] = False
        player_data["last_region"] = last_region

    player_info[player_name] = player_data


def print_title(region_name, player_name):
    from .storage import global_data_json

    region_msg = global_data_json[region_name]["msg"]
    if region_msg['title']:
        rcon_execute(f"title \"{player_name}\" title \"{region_msg['title']}\"")
        if region_msg['subtitle']:
            rcon_execute(f"title \"{player_name}\" subtitle \"{region_msg['subtitle']}\"")
    if region_msg['actionbar']:
        rcon_execute(f"title \"{player_name}\" actionbar \"{region_msg['actionbar']}\"")
    if region_msg['msg']:
        for i in region_msg['msg']:
            __mcdr_server.tell(player_name, i)


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
        if not stop_status:
            __mcdr_server.logger.error(
                "服务器未启用RCON或服务器核心已关闭！"
            )
        stop_status = True
        result = None
    return result


# 插件入口
def on_load(server: PluginServerInterface, _):
    global __mcdr_server, player_info, stop_status, config
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
    stop_status = False
    getpos_player()


# 在线玩家检测
def on_player_joined(_, player, __):
    global player_info
    if player not in player_info.keys() and config.bot_prefix not in player:
        player_info[player] = {
            "position": None,
            "dimension": None,
            "last_update_time": int(time.time()),
            "is_afk": False,
            "last_region": {},
        }


def on_player_left(_, player):
    global player_info
    if player in player_info.keys():
        del player_info[player]
