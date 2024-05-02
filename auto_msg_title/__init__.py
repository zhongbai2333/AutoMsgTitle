import re
from mcdreforged.api.all import *
import time

from .config import Config

global __mcdr_server, player_info, stop_status, online_player_list


@new_thread("GetPos")
def getpos_player(reload: bool = False):
    global player_info, online_player_list
    time.sleep(1)
    while not stop_status:
        if player_info or reload:
            online_player_list = []
            result = rcon_execute(f"execute as @a run data get entity @s Pos")
            debug_print(player_info)
            if result:
                for i in result.split("]")[:-1]:
                    n_result = i.split()
                    online_player_list.append(n_result[0])
                    edit_player_info(n_result[0], [int(float(n_result[-3][1:-2])), int(float(n_result[-2][:-2])), int(float(n_result[-1][:-1]))])
                for i in list(set(list(player_info.keys())) - set(online_player_list)):
                    del player_info[i]
        reload = False
        time.sleep(1)


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


def show_help(source: CommandSource):
	help_msg_lines = '''
--------- MCDR 自动消息插件 v{2} ---------
一个用于在一个区域自动显示题目或消息的插件
§7{0}§r 显示此帮助信息
§7{0} list §6[<可选页号>]§r 列出所有消息区域
§7{0} add §b<区域名称> §e2d <x1> <z1> <x2> <z2> <维度id> §6[<大标题>](<小标题>)#<物品栏消息>#<聊天消息>§r 加入一个区域
§7{0} add §b<区域名称> §e3d <x1> <y1> <z1> <x2> <y2> <z2> <维度id> §6[<大标题>](<小标题>)#<物品栏消息>#<聊天消息>§r 加入一个区域
§7{0} msg §b<区域名称>§r 显示区域详细的聊天消息
§7{0} msg §b<区域名称>§r §eaddline <聊天消息> <行数> 添加聊天消息，行数默认最后一行
§7{0} msg §b<区域名称>§r §delline <行数> 删除聊天消息，行数默认最后一行
§7{0} del §b<区域名称>§r 删除区域，要求全字匹配
§7{0} info §b<区域名称>§r 显示区域的详情等信息
其中：
当§6可选页号§r被指定时，将以每{1}个路标为一页，列出指定页号的路标
§3关键字§r以及§b区域名称§r为不包含空格的一个字符串，或者一个被""括起的字符串
'''.format("!!amt", 1, __mcdr_server.get_self_metadata().version).splitlines(True)
	help_msg_rtext = RTextList()
	for line in help_msg_lines:
		result = re.search(r'(?<=§7)!!amt[\w ]*(?=§)', line)
		if result is not None:
			help_msg_rtext.append(RText(line).c(RAction.suggest_command, result.group()).h('点击以填入 §7{}§r'.format(result.group())))
		else:
			help_msg_rtext.append(line)
	source.reply(help_msg_rtext)


def debug_print(msg: str):
    if config.debug:
        __mcdr_server.logger.info(msg)


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
    create_command()
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


def create_command():
    __mcdr_server.register_command(
        Literal("!!amt").
        runs(show_help)
    )