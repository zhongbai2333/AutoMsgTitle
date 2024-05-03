from mcdreforged.api.all import *
import re


class CommandActions():
    def __init__(self, mcdr_server) -> None:
        from .storage import JsonDataEditor
        self.__mcdr_server = mcdr_server
        self.create_command()
        self.data_editor = JsonDataEditor(f"{self.__mcdr_server.get_data_folder()}/data.json")
        pass

    # 创建命令
    def create_command(self):
        builder = SimpleCommandBuilder()

        builder.command("!!amt", self.show_help)
        builder.command("!!amt list", self.regions_list)
        builder.command("!!amt list <page_number>", self.regions_list)
        builder.command("!!amt add <region_name> 2d <x1> <z1> <x2> <z2> <dimension_id> <msg>", self.add_region_2d)
        builder.command("!!amt add <region_name> 3d <x1> <y1> <z1> <x2> <y2> <z2> <dimension_id> <msg>", self.show_help)
        builder.command("!!amt msg <region_name>", self.show_help)
        builder.command("!!amt msg <region_name> addline <line_msg>", self.show_help)
        builder.command("!!amt msg <region_name> addline <line_msg> <line_number>", self.show_help)
        builder.command("!!amt msg <region_name> delline", self.show_help)
        builder.command("!!amt msg <region_name> delline <line_number>", self.show_help)
        builder.command("!!amt del <region_name>", self.show_help)
        builder.command("!!amt info <region_name>", self.show_help)

        builder.arg("page_number", Integer)
        builder.arg("region_name", Text)
        builder.arg("x1", Integer)
        builder.arg("y1", Integer)
        builder.arg("z1", Integer)
        builder.arg("x2", Integer)
        builder.arg("y2", Integer)
        builder.arg("z2", Integer)
        builder.arg("dimension_id", Text)
        builder.arg("msg", GreedyText)
        builder.arg("line_msg", Text)
        builder.arg("line_number", Integer)

        builder.register(self.__mcdr_server)


    def show_help(self, source: CommandSource):
        help_msg_lines = '''
--------- MCDR 自动消息插件 v{2} ---------
一个用于在一个区域自动显示题目或消息的插件
§7{0}§r 显示此帮助信息
§7{0} list §6[<可选页号>]§r 列出所有消息区域
§7{0} add §b<区域名称>§r §e2d <x1> <z1> <x2> <z2> <维度id> §6[<大标题>](<小标题>)#<物品栏消息>#<聊天消息>§r 加入一个区域
§7{0} add §b<区域名称>§r §e3d <x1> <y1> <z1> <x2> <y2> <z2> <维度id> §6[<大标题>](<小标题>)#<物品栏消息>#<聊天消息>§r 加入一个区域
§7{0} msg §b<区域名称>§r 显示区域详细的聊天消息
§7{0} msg §b<区域名称>§r §eaddline <聊天消息> §6[<行数>]§r 添加聊天消息，行数默认最后一行
§7{0} msg §b<区域名称>§r §edelline §6[<行数>]§r 删除聊天消息，行数默认最后一行
§7{0} del §b<区域名称>§r 删除区域，要求全字匹配
§7{0} info §b<区域名称>§r 显示区域的详情等信息
其中：
当§6可选页号§r被指定时，将以每{1}个路标为一页，列出指定页号的路标，小标题必须跟随大标题显示
§3关键字§r以及§b区域名称§r为不包含空格的一个字符串，或者一个被""括起的字符串
'''.format("!!amt", 1, self.__mcdr_server.get_self_metadata().version).splitlines(True)
        help_msg_rtext = RTextList()
        for line in help_msg_lines:
            result = re.search(r'(?<=§7)!!amt[\w ]*(?=§)', line)
            if result is not None:
                help_msg_rtext.append(RText(line).c(RAction.suggest_command, result.group()).h('点击以填入 §7{}§r'.format(result.group())))
            else:
                help_msg_rtext.append(line)
        source.reply(help_msg_rtext)
    
    
    def regions_list(self, source: CommandSource, context: CommandContext):
        if context:
            pass
        else:
            pass

    
    def add_region_2d(self, source: CommandSource, context: CommandContext):
        def no_list(text):
            if text:
                return text[0]
            else:
                return ""
        title = no_list(re.findall(r'\[([^\]]+)\]', context['msg']))
        subtitle = no_list(re.findall(r'\(([^\)]+)\)', context['msg']))
        actionbar = no_list(re.findall(r'#([^#]+)#', context['msg']))
        msg = context['msg'].replace(f"[{title}]", '').strip().replace(f"({subtitle})", '').strip().replace(f"#{actionbar}#", '').strip()
        self.data_editor.add(context['region_name'], {
            "shape": 0,
            "pos": {
                "from": [context['x1'],context['z1']],
                "to": [context['x2'],context['z2']]
            },
            "dimension_id": context['dimension_id'],
            "msg": {
                "title": title,
                "subtitle": subtitle,
                "actionbar": actionbar,
                "msg": msg
            }
        })
