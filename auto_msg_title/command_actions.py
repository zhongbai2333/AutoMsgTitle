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
        builder.command(
            "!!amt msg <region_name> addline <line_msg>", self.region_msg_addline
        )
        builder.command(
            "!!amt msg <region_name> addline <line_msg> <line_number>",
            self.region_msg_addline,
        )
        builder.command(
            "!!amt msg <region_name> editline <line_number> <line_msg>",
            self.region_msg_editline,
        )
        builder.command("!!amt msg <region_name> delline", self.region_msg_deline)
        builder.command(
            "!!amt msg <region_name> delline <line_number>", self.region_msg_deline
        )
        builder.command("!!amt del <region_name>", self.del_region)
        builder.command("!!amt move <region_name> <region_number>", self.move_region)

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
        builder.arg("region_number", Integer)

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
§7{0} move §b<区域名称>§r §e<序号>§r 移动区域的序号，当区域重叠时，在先的区域优先级高
§7{0} msg §b<区域名称>§r 显示区域详细的聊天消息
§7{0} msg §b<区域名称>§r §eaddline <聊天消息> §6[<行数>]§r 添加聊天消息，行数默认最后一行
§7{0} msg §b<区域名称>§r §eeditline <行数> <聊天消息>§r 编辑聊天消息
§7{0} msg §b<区域名称>§r §edelline §6[<行数>]§r 删除聊天消息，行数默认最后一行
§7{0} del §b<区域名称>§r 删除区域，要求全字匹配
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
        # 检查权限
        if not source.has_permission_higher_than(self.permission["list"]):
            source.reply(f"§4权限不足！你至少需要 {self.permission['list']} 级及以上！")
            return

        # 获取区域数据
        regions = self.data_editor.list()
        if context:
            page_number = context["page_number"]
        else:
            page_number = 1  # 默认显示第一页

        # 分页处理
        max_page = (len(regions) + 4) // 5  # 每页显示5个，计算最大页数
        if page_number < 1:
            source.reply("已经是第一页了！")
            return
        elif page_number > max_page:
            source.reply("已经是最后一页了！")
            return

        # 展示区域列表
        regions_rtext = self.get_regions_rtext(regions, page_number)
        source.reply(regions_rtext)

    def get_regions_rtext(self, regions: dict, page: int):
        regions_rtext = RTextList()
        start_index = (page - 1) * 5
        end_index = start_index + 5

        regions_rtext.append(f"--------- 区域列表 第 §6{page}/{(len(regions) + 4) // 5} §f页 ---------\n")
        items = list(regions.items())[start_index:min(end_index, len(regions))]

        for num, (name, details) in enumerate(items, start=start_index + 1):
            shape_text = "2D" if details["shape"] == 0 else "3D"
            regions_rtext.append(f"{num}. {name}\n形状：§6{shape_text}\n")

            position_from = ' '.join(map(str, details['pos']['from']))
            position_to = ' '.join(map(str, details['pos']['to']))
            dimension_id = details['dimension_id']
            regions_rtext.append(f"区域：从 §a{position_from} §f到 §a{position_to}§r\n")
            regions_rtext.append(f"维度：§a{dimension_id}§r\n")

            # 组装 reload_command
            reload_command = f"!!amt add {name} {shape_text.lower()} {position_from} {position_to} {dimension_id} "
            if details["msg"]["title"]:
                reload_command += f"[{details['msg']['title']}]"
            if details["msg"]["subtitle"]:
                reload_command += f"({details['msg']['subtitle']})"
            if details["msg"]["actionbar"]:
                reload_command += f"#{details['msg']['actionbar']}#"
            message_lines = details["msg"]["msg"]
            for line in message_lines:
                reload_command += f"{line};;"

            regions_rtext.append(
                f"""消息：
 | 标题：§6{details['msg']['title']}§r
 | 副标题：§6{details['msg']['subtitle']}§r
 | 动作栏：§6{details['msg']['actionbar']}§r
 | 消息栏：\n"""
            )
            for num, msg in enumerate(message_lines):
                if num < 3:
                    regions_rtext.append(f" |  | §6{msg}\n")
                elif num == 3:
                    regions_rtext.append(" |  | §6...\n")

            regions_rtext.append("---")
            regions_rtext.append(
                RText("§7[↺]§r")
                .c(RAction.suggest_command, reload_command[:-2])
                .h("重新键入 §7!!amt add §r命令")
            )
            regions_rtext.append("---")
            regions_rtext.append(
                RText("§b[⇌]§r")
                .c(RAction.suggest_command, f"!!amt move {name} ")
                .h("修改这个区域的序号，键入 §7!!amt move §r命令")
            )
            regions_rtext.append("---")
            regions_rtext.append(
                RText("§6[✏]§r")
                .c(RAction.run_command, f"!!amt msg {name}")
                .h("详细编辑消息栏")
            )
            regions_rtext.append("---")
            regions_rtext.append(
                RText("§4[✕]§r")
                .c(RAction.run_command, f"!!amt del {name}")
                .h("删除这个区域")
            )
            regions_rtext.append("---\n")

        regions_rtext.append("--------- ")
        if page > 1:
            regions_rtext.append(
                RText("<<").c(RAction.run_command, f"!!amt list {page - 1}").h("前一页")
            )
        regions_rtext.append(f" 第 §6{page}/{(len(regions) + 4) // 5} §f页 ")
        if page < (len(regions) + 4) // 5:
            regions_rtext.append(
                RText(">>").c(RAction.run_command, f"!!amt list {page + 1}").h("后一页")
            )
        regions_rtext.append(" ---------")
        return regions_rtext

    # add 命令
    def add_region(self, source: CommandSource, context: CommandContext, dimension_type: str):
        if not source.has_permission_higher_than(self.permission["add"]):
            source.reply(f"§4权限不足！你至少需要 {self.permission['add']} 级及以上！")
            return

        title, subtitle, actionbar, msg = self.parse_region_message(context["msg"])

        position = {
            "from": [context["x1"], context["z1"]] if dimension_type == '2d' else [context["x1"], context["y1"], context["z1"]],
            "to": [context["x2"], context["z2"]] if dimension_type == '2d' else [context["x2"], context["y2"], context["z2"]]
        }

        self.data_editor.add(
            context["region_name"],
            {
                "shape": 0 if dimension_type == '2d' else 1,
                "pos": position,
                "dimension_id": context["dimension_id"],
                "msg": {
                    "title": title,
                    "subtitle": subtitle,
                    "actionbar": actionbar,
                    "msg": msg,
                },
            }
        )
        source.reply(f"区域 §7{context['region_name']} §r添加(修改)成功！")

    def parse_region_message(self, msg):
        title = self.extract_first_match(re.findall(r"\[([^]]+)]", msg))
        subtitle = self.extract_first_match(re.findall(r"\(([^)]+)\)", msg))
        actionbar = self.extract_first_match(re.findall(r"#([^#]+)#", msg))
        cleaned_msg = (
            msg.replace(f"[{title}]", "")
            .replace(f"({subtitle})", "")
            .replace(f"#{actionbar}#", "")
            .strip()
            .split(";;")
        )
        return title, subtitle, actionbar, cleaned_msg

    def extract_first_match(self, matches):
        return matches[0] if matches else ""

    # add 2d
    def add_region_2d(self, source: CommandSource, context: CommandContext):
        self.add_region(source, context, '2d')

    # add 3d
    def add_region_3d(self, source: CommandSource, context: CommandContext):
        self.add_region(source, context, '3d')

    # del 命令
    def del_region(self, source: CommandSource, context: CommandContext):
        if not source.has_permission_higher_than(self.permission["del"]):
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

    def msg_list(self, context):
        msg_rtext = RTextList()
        msg_rtext.append(f"--------- {context['region_name']} ---------\n")
        num = -1
        for num, i in enumerate(
            self.data_editor.list()[context["region_name"]]["msg"]["msg"]
        ):
            msg_rtext.append(
                RText(f"{num + 1}. {i}")
                .c(
                    RAction.suggest_command,
                    f"!!amt msg {context['region_name']} editline {num + 1} {i}",
                )
                .h("修改此条消息")
            )
            msg_rtext.append(
                RText("§4[✕]§r\n")
                .c(
                    RAction.run_command,
                    f"!!amt msg {context['region_name']} delline {num + 1}",
                )
                .h("删除本行")
            )
        msg_rtext.append(
            RText(f"{num + 2}. §a+")
            .c(RAction.suggest_command, f"!!amt msg {context['region_name']} addline ")
            .h("添加新行")
        )
        return msg_rtext

    # msg 命令
    def region_msg(self, source: CommandSource, context: CommandContext):
        if not source.has_permission_higher_than(self.permission["msg"]):
            source.reply(f"§4权限不足！你至少需要 {self.permission['msg']} 级及以上！")
            return
        if context["region_name"] not in self.data_editor.list().keys():
            source.reply(f"§4无法找到区域 {context['region_name']} ！")
            return
        source.reply(self.msg_list(context))

    # msg addline 命令
    def region_msg_addline(self, source: CommandSource, context: CommandContext):
        if not source.has_permission_higher_than(self.permission["msg"]):
            source.reply(f"§4权限不足！你至少需要 {self.permission['msg']} 级及以上！")
            return
        if context["region_name"] not in self.data_editor.list().keys():
            source.reply(f"§4无法找到区域 {context['region_name']} ！")
            return

        def addline(msg: str, line_num: int = 0):
            region = self.data_editor.list()[context["region_name"]]
            if line_num > 0:
                region["msg"]["msg"].insert(line_num - 1, msg)
            else:
                region["msg"]["msg"].append(msg)
            return region

        if "line_number" in context.keys():
            self.data_editor.add(
                context["region_name"],
                addline(context["line_msg"], context["line_number"]),
            )
        else:
            self.data_editor.add(
                context["region_name"],
                addline(context["line_msg"]),
            )
        source.reply(self.msg_list(context))

    # msg editline 命令
    def region_msg_editline(self, source: CommandSource, context: CommandContext):
        if not source.has_permission_higher_than(self.permission["msg"]):
            source.reply(f"§4权限不足！你至少需要 {self.permission['msg']} 级及以上！")
            return
        if context["region_name"] not in self.data_editor.list().keys():
            source.reply(f"§4无法找到区域 {context['region_name']} ！")
            return
        region = self.data_editor.list()[context["region_name"]]
        region["msg"]["msg"][context["line_number"] - 1] = context["line_msg"]
        self.data_editor.add(context["region_name"], region)
        source.reply(self.msg_list(context))

    # msg delline 命令
    def region_msg_deline(self, source: CommandSource, context: CommandContext):
        if not source.has_permission_higher_than(self.permission["msg"]):
            source.reply(f"§4权限不足！你至少需要 {self.permission['msg']} 级及以上！")
            return
        if context["region_name"] not in self.data_editor.list().keys():
            source.reply(f"§4无法找到区域 {context['region_name']} ！")
            return
        region = self.data_editor.list()[context["region_name"]]
        if "line_number" in context.keys():
            region["msg"]["msg"].pop(context["line_number"] - 1)
        else:
            region["msg"]["msg"].pop()
        self.data_editor.add(context["region_name"], region)
        source.reply(self.msg_list(context))

    # move 命令
    def move_region(self, source: CommandSource, context: CommandContext):
        if not source.has_permission_higher_than(self.permission["move"]):
            source.reply(f"§4权限不足！你至少需要 {self.permission['move']} 级及以上！")
            return
        if context["region_name"] not in self.data_editor.list().keys():
            source.reply(f"§4无法找到区域 {context['region_name']} ！")
            return
        if context["region_number"] - 1 >= 0:
            self.data_editor.move(context["region_name"], context["region_number"] - 1)
            source.reply(
                f"已将区域 §7{context['region_name']} §r移至 §7{context['region_number']}"
            )
        else:
            source.reply("§4序列号不能小于 1 ！")
