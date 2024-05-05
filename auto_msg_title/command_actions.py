import re
from mcdreforged.api.all import *


class CommandActions:
    def __init__(self, mcdr_server, permission) -> None:
        from .storage import JsonDataEditor

        self.__mcdr_server = mcdr_server
        self.permission = permission
        self.ready_del = ""
        self.create_command()
        self.data_editor = JsonDataEditor(
            f"{self.__mcdr_server.get_data_folder()}/data.json"
        )
        pass

    # 创建命令
    def create_command(self):
        builder = SimpleCommandBuilder()

        builder.command("!!amt", self.show_help)
        builder.command("!!amt list", self.regions_list)
        builder.command("!!amt list <page_number>", self.regions_list)
        builder.command(
            "!!amt add <region_name> 2d <x1> <z1> <x2> <z2> <dimension_id> <msg>",
            self.add_region_2d,
        )
        builder.command(
            "!!amt add <region_name> 3d <x1> <y1> <z1> <x2> <y2> <z2> <dimension_id> <msg>",
            self.add_region_3d,
        )
        builder.command("!!amt msg <region_name>", self.region_msg)
        builder.command("!!amt msg <region_name> addline <line_msg>", self.show_help)
        builder.command(
            "!!amt msg <region_name> addline <line_msg> <line_number>", self.show_help
        )
        builder.command("!!amt msg <region_name> delline", self.show_help)
        builder.command("!!amt msg <region_name> delline <line_number>", self.show_help)
        builder.command("!!amt del <region_name>", self.del_region)
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

        self.__mcdr_server.register_help_message(
            "!!amt", "获取AutoMsgTitle插件帮助列表"
        )

    # help 列表
    def show_help(self, source: CommandSource):
        help_msg_lines = """
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
小标题必须跟随大标题显示
当§6可选页号§r被指定时，将以每{1}个路标为一页，列出指定页号的路标
§3关键字§r以及§b区域名称§r为不包含空格的一个字符串，或者一个被""括起的字符串
""".format(
            "!!amt", 5, self.__mcdr_server.get_self_metadata().version
        ).splitlines(
            True
        )
        help_msg_rtext = RTextList()
        for line in help_msg_lines:
            result = re.search(r"(?<=§7)!!amt[\w ]*(?=§)", line)
            if result is not None:
                help_msg_rtext.append(
                    RText(line)
                    .c(RAction.suggest_command, result.group())
                    .h("点击以填入 §7{}§r".format(result.group()))
                )
            else:
                help_msg_rtext.append(line)
        source.reply(help_msg_rtext)

    # list 命令
    def regions_list(self, source: CommandSource, context: CommandContext):
        if source.get_permission_level() < self.permission["list"]:
            source.reply(f"§4权限不足！你至少需要 {self.permission['list']} 级及以上！")
            return

        # 制作 list 的 Rtext
        def get_regions_rtext(regions: dict, page: int):
            regions_rtext = RTextList()
            regions_rtext.append(
                f"--------- 区域列表 第 §6{page}/{len(regions) // 5 + 1} §f页 ---------\n"
            )
            for num, i in enumerate(regions.keys()):
                if (num + 1) <= (page - 1) * 5:
                    continue
                elif (num + 1) > page * 5:
                    break
                regions_rtext.append(f"{num + 1}. {i}\n")
                if regions[i]["shape"] == 0:
                    regions_rtext.append(f"形状：§62D\n")
                    reload_command = f"!!amt add {i} 2d "
                else:
                    regions_rtext.append(f"形状：§63D\n")
                    reload_command = f"!!amt add {i} 3d "
                reload_command += f"{str(regions[i]['pos']['from'])[1:-1].replace(',','').strip()} {str(regions[i]['pos']['to'])[1:-1].replace(',','').strip()} {regions[i]['dimension_id']} "
                if regions[i]["msg"]["title"]:
                    reload_command += f"[{regions[i]['msg']['title']}]"
                if regions[i]["msg"]["subtitle"]:
                    reload_command += f"({regions[i]['msg']['subtitle']})"
                if regions[i]["msg"]["actionbar"]:
                    reload_command += f"#{regions[i]['msg']['actionbar']}#"
                regions_rtext.append(
                    f"""区域：从 §a{str(regions[i]['pos']['from'])} §f到 §a{str(regions[i]['pos']['to'])}
维度：§a{regions[i]['dimension_id']}
消息：
 | 标题：§6{regions[i]['msg']['title']}
 | 副标题：§6{regions[i]['msg']['subtitle']}
 | 动作栏：§6{regions[i]['msg']['actionbar']}
 | 消息栏：\n"""
                )
                for j in regions[i]["msg"]["msg"]:
                    regions_rtext.append(f" |  | §6{j}\n")
                    reload_command += f"{j};;"
                regions_rtext.append("---")
                regions_rtext.append(
                    RText("§7[↺]§r")
                    .c(RAction.suggest_command, reload_command[:-2])
                    .h("重新键入 §7!!amt add §r命令")
                )
                regions_rtext.append("---")
                regions_rtext.append(
                    RText("§6[✏]§r")
                    .c(RAction.run_command, f"!!amt msg {i}")
                    .h("详细编辑消息栏")
                )
                regions_rtext.append("---")
                regions_rtext.append(
                    RText("§4[✕]§r")
                    .c(RAction.run_command, f"!!amt del {i}")
                    .h("删除这个区域")
                )
                regions_rtext.append("---\n")
            regions_rtext.append("--------- ")
            regions_rtext.append(
                RText("<<").c(RAction.run_command, f"!!amt list {page - 1}").h("前一页")
            )
            regions_rtext.append(f" 第 §6{page}/{len(regions) // 5 + 1} §f页 ")
            regions_rtext.append(
                RText(">>").c(RAction.run_command, f"!!amt list {page + 1}").h("后一页")
            )
            regions_rtext.append(" ---------")
            return regions_rtext

        if context:
            regions = self.data_editor.list()
            max_page = len(regions) // 5 + 1
            if context["page_number"] < 1:
                source.reply("已经是第一页了！")
            elif context["page_number"] > max_page:
                source.reply("已经是最后一页了！")
            else:
                source.reply(get_regions_rtext(regions, context["page_number"]))
        else:
            regions = self.data_editor.list()
            source.reply(get_regions_rtext(regions, 1))

    # add 2d 命令
    def add_region_2d(self, source: CommandSource, context: CommandContext):
        if source.get_permission_level() < self.permission["add"]:
            source.reply(f"§4权限不足！你至少需要 {self.permission['add']} 级及以上！")
            return

        def no_list(text):
            if text:
                return text[0]
            else:
                return ""

        title = no_list(re.findall(r"\[([^]]+)]", context["msg"]))
        subtitle = no_list(re.findall(r"\(([^)]+)\)", context["msg"]))
        actionbar = no_list(re.findall(r"#([^#]+)#", context["msg"]))
        msg = (
            context["msg"]
            .replace(f"[{title}]", "")
            .strip()
            .replace(f"({subtitle})", "")
            .strip()
            .replace(f"#{actionbar}#", "")
            .strip()
            .split(";;")
        )
        self.data_editor.add(
            context["region_name"],
            {
                "shape": 0,
                "pos": {
                    "from": [context["x1"], context["z1"]],
                    "to": [context["x2"], context["z2"]],
                },
                "dimension_id": context["dimension_id"],
                "msg": {
                    "title": title,
                    "subtitle": subtitle,
                    "actionbar": actionbar,
                    "msg": msg,
                },
            },
        )
        source.reply(f"区域 §7{context['region_name']} §r添加(修改)成功！")

    # add 3d 命令
    def add_region_3d(self, source: CommandSource, context: CommandContext):
        if source.get_permission_level() < self.permission["add"]:
            source.reply(f"§4权限不足！你至少需要 {self.permission['add']} 级及以上！")
            return

        def no_list(text):
            if text:
                return text[0]
            else:
                return ""

        title = no_list(re.findall(r"\[([^]]+)]", context["msg"]))
        subtitle = no_list(re.findall(r"\(([^)]+)\)", context["msg"]))
        actionbar = no_list(re.findall(r"#([^#]+)#", context["msg"]))
        msg = (
            context["msg"]
            .replace(f"[{title}]", "")
            .strip()
            .replace(f"({subtitle})", "")
            .strip()
            .replace(f"#{actionbar}#", "")
            .strip()
            .split(";;")
        )
        self.data_editor.add(
            context["region_name"],
            {
                "shape": 1,
                "pos": {
                    "from": [context["x1"], context["y1"], context["z1"]],
                    "to": [context["x2"], context["y2"], context["z2"]],
                },
                "dimension_id": context["dimension_id"],
                "msg": {
                    "title": title,
                    "subtitle": subtitle,
                    "actionbar": actionbar,
                    "msg": msg,
                },
            },
        )
        source.reply(f"区域 §7{context['region_name']} §r添加(修改)成功！")

    # del 命令
    def del_region(self, source: CommandSource, context: CommandContext):
        if source.get_permission_level() < self.permission["del"]:
            source.reply(f"§4权限不足！你至少需要 {self.permission['del']} 级及以上！")
            return
        if context["region_name"] not in self.data_editor.list().keys():
            source.reply(f"§4无法找到区域 {context['region_name']} ！")
            return
        if self.ready_del != context["region_name"]:
            self.ready_del = context["region_name"]
            del_msg_rtext = RTextList()
            del_msg_rtext.append("你§l确定§r要§4§l删除§r此区域吗？\n")
            del_msg_rtext.append(
                f"重复输入 §7!!amt del {context['region_name']} §r以确认！"
            )
            del_msg_rtext.append(
                RText("§a[✓]")
                .c(RAction.run_command, f"!!amt del {context['region_name']}")
                .h("§a确认删除")
            )
            source.reply(del_msg_rtext)
        else:
            self.data_editor.remove(self.ready_del)
            source.reply(f"成功删除区域 §7{self.ready_del} §r！")
            self.ready_del = ""

    # msg 命令
    def region_msg(self, source: CommandSource, context: CommandContext):
        if source.get_permission_level() < self.permission["msg"]:
            source.reply(f"§4权限不足！你至少需要 {self.permission['msg']} 级及以上！")
            return
        if context["region_name"] not in self.data_editor.list().keys():
            source.reply(f"§4无法找到区域 {context['region_name']} ！")
            return
        msg_rtext = RTextList()
        msg_rtext.append(f"--------- {context['region_name']} ---------\n")
        for num, i in enumerate(
            self.data_editor.list()[context["region_name"]]["msg"]["msg"]
        ):
            msg_rtext.append(f"{num + 1}. {i}")
