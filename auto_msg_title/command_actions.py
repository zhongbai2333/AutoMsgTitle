import re
from mcdreforged.api.all import *
from .tools import amt_to_section, section_to_amt


class CommandActions:
    def __init__(self, mcdr_server: PluginServerInterface, permission, get_player_state=None) -> None:
        from .storage import JsonDataEditor

        self.__mcdr_server = mcdr_server
        self.permission = permission
        # 获取玩家状态的回调：传入玩家名，返回 { position: [x,y,z], dimension: str } 或 None
        self._get_player_state = get_player_state
        # 记录玩家“上次标记”的坐标与维度
        self._marks = {}
        self.ready_del = ""
        # 每页显示条数
        self._PAGE_SIZE = 5
        # 原版维度别名映射到规范ID
        self._VANILLA_DIM_ALIASES = {
            "0": "minecraft:overworld",
            "overworld": "minecraft:overworld",
            "minecraft:overworld": "minecraft:overworld",
            "1": "minecraft:the_nether",
            "nether": "minecraft:the_nether",
            "the_nether": "minecraft:the_nether",
            "minecraft:the_nether": "minecraft:the_nether",
            "2": "minecraft:the_end",
            "end": "minecraft:the_end",
            "the_end": "minecraft:the_end",
            "minecraft:the_end": "minecraft:the_end",
        }
        self.create_command()
        self.data_editor = JsonDataEditor(
            f"{self.__mcdr_server.get_data_folder()}/data.json"
        )
        pass

    # 创建命令
    def create_command(self):
        builder = SimpleCommandBuilder()

        # 顶级帮助与列表
        builder.command("!!amt", self.show_help)
        builder.command("!!amt list", self.regions_list)
        builder.command("!!amt list <page_number>", self.regions_list)

        # 标记与基于标记创建区域
        builder.command("!!amt mark", self.mark_here)
        # 新命名：addmark
        builder.command("!!amt addmark 2d <region_name> <msg>", self.add_from_mark_2d)
        builder.command("!!amt addmark 3d <region_name> <msg>", self.add_from_mark_3d)
        # 兼容旧命令名
        builder.command("!!amt add_from_mark 2d <region_name> <msg>", self.add_from_mark_2d)
        builder.command("!!amt add_from_mark 3d <region_name> <msg>", self.add_from_mark_3d)

        # 可视化边界
        builder.command("!!amt viz on", self.viz_on)
        builder.command("!!amt viz off", self.viz_off)
        builder.command("!!amt viz all", self.viz_all)
        builder.command("!!amt viz region <region_name>", self.viz_region)

        # 标记管理
        builder.command("!!amt clearmark", self.clear_mark)

        # 直接添加区域
        builder.command(
            "!!amt add <region_name> 2d <x1> <z1> <x2> <z2> <dimension_id> <msg>",
            self.add_region_2d,
        )
        builder.command(
            "!!amt add <region_name> 3d <x1> <y1> <z1> <x2> <y2> <z2> <dimension_id> <msg>",
            self.add_region_3d,
        )

        # 消息编辑
        builder.command("!!amt msg <region_name>", self.region_msg)
        builder.command("!!amt msg <region_name> addline <line_msg>", self.region_msg_addline)
        builder.command("!!amt msg <region_name> addline <line_msg> <line_number>", self.region_msg_addline)
        builder.command("!!amt msg <region_name> editline <line_number> <line_msg>", self.region_msg_editline)
        builder.command("!!amt msg <region_name> delline", self.region_msg_deline)
        builder.command("!!amt msg <region_name> delline <line_number>", self.region_msg_deline)

        # 删除 / 移动
        builder.command("!!amt del <region_name>", self.del_region)
        builder.command("!!amt move <region_name> <region_number>", self.move_region)

        # 参数定义
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

        # 注册命令
        builder.register(self.__mcdr_server)

        # 帮助入口
        self.__mcdr_server.register_help_message("!!amt", "获取AutoMsgTitle插件帮助列表")

    # help 列表
    def show_help(self, source: CommandSource):
        help_msg_lines = """
--------- MCDR 自动消息插件 v{2} ---------
一个用于在一个区域自动显示题目或消息的插件
§7{0}§r 显示此帮助信息
§7{0} list §6[<可选页号>]§r 列出所有消息区域
§7{0} viz on/off§r 打开/关闭你自己的区域边界可视化
§7{0} viz all§r 显示全部区域边界（仅在你当前维度）
§7{0} viz region §b<区域名称>§r 仅显示该区域边界
§7{0} mark§r 记录你当前脚下坐标（保存到会话内，仅自己可见）
§7{0} clearmark§r 清除你当前脚下坐标的记录
§7{0} addmark §e2d <区域名称> <消息>§r 基于你当前坐标与上次记录在当前维度创建 2D 区域（兼容旧命令名 add_from_mark）
§7{0} addmark §e3d <区域名称> <消息>§r 基于你当前坐标与上次记录在当前维度创建 3D 区域（兼容旧命令名 add_from_mark）
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
维度ID示例（原版）：§6overworld/nether/end§r 或 §60/1/2§r，或完整ID §6minecraft:overworld§r / §6minecraft:the_nether§r / §6minecraft:the_end§r；亦支持模组/自定义维度（例如 §6some_mod:custom_dim§r）
§3关键字§r以及§b区域名称§r为不包含空格的一个字符串，或者一个被""括起的字符串
""".format(
            "!!amt", self._PAGE_SIZE, self.__mcdr_server.get_self_metadata().version
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
        if not regions:
            source.reply("暂无任何区域，使用 §7!!amt add§r 添加一个吧！")
            return
        if context:
            page_number = context["page_number"]
        else:
            page_number = 1  # 默认显示第一页

        # 分页处理
        max_page = (len(regions) + self._PAGE_SIZE - 1) // self._PAGE_SIZE  # 计算最大页数
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
        total_pages = max(1, (len(regions) + self._PAGE_SIZE - 1) // self._PAGE_SIZE)
        start_index = (page - 1) * self._PAGE_SIZE
        end_index = start_index + self._PAGE_SIZE

        regions_rtext.append(f"--------- 区域列表 第 §6{page}/{total_pages} §f页 ---------\n")
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
            disp_title = section_to_amt(details["msg"].get("title", ""))
            disp_subtitle = section_to_amt(details["msg"].get("subtitle", ""))
            disp_actionbar = section_to_amt(details["msg"].get("actionbar", ""))
            if disp_title:
                reload_command += f"[{disp_title}]"
            if disp_subtitle:
                reload_command += f"({disp_subtitle})"
            if disp_actionbar:
                reload_command += f"#{disp_actionbar}#"
            message_lines = details["msg"]["msg"]
            for line in message_lines:
                reload_command += f"{section_to_amt(line)};;"

            regions_rtext.append(
                f"""消息：
 | 标题：§6{disp_title}§r
 | 副标题：§6{disp_subtitle}§r
 | 动作栏：§6{disp_actionbar}§r
 | 消息栏：\n"""
            )
            for num, msg in enumerate(message_lines):
                if num < 3:
                    regions_rtext.append(f" |  | §6{section_to_amt(msg)}\n")
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
        regions_rtext.append(f" 第 §6{page}/{total_pages} §f页 ")
        if page < total_pages:
            regions_rtext.append(
                RText(">>").c(RAction.run_command, f"!!amt list {page + 1}").h("后一页")
            )
        regions_rtext.append(" ---------")
        return regions_rtext

    # ===== 可视化命令处理 =====
    def _viz_guard(self, source: CommandSource):
        if not source.is_player:
            source.reply("§4该命令只能由玩家在游戏内执行！")
            return False
        # 使用可视化专用权限
        if not source.has_permission_higher_than(self.permission.get("viz", 0)):
            source.reply(f"§4权限不足！你至少需要 {self.permission.get('viz', 0)} 级及以上！")
            return False
        return True

    def viz_on(self, source: CommandSource):
        if not self._viz_guard(source):
            return
        from .entry import viz_set_viewer
        viz_set_viewer(source.player, None)
        source.reply("已开启可视化（当前维度：全部区域）")

    def viz_off(self, source: CommandSource):
        if not self._viz_guard(source):
            return
        from .entry import viz_remove_viewer
        viz_remove_viewer(source.player)
        source.reply("已关闭可视化")

    def viz_all(self, source: CommandSource):
        if not self._viz_guard(source):
            return
        from .entry import viz_set_viewer
        viz_set_viewer(source.player, None)
        source.reply("显示全部区域边界（当前维度）")

    def viz_region(self, source: CommandSource, context: CommandContext):
        if not self._viz_guard(source):
            return
        if context["region_name"] not in self.data_editor.list().keys():
            source.reply(f"§4无法找到区域 {context['region_name']} ！")
            return
        from .entry import viz_set_viewer
        viz_set_viewer(source.player, context["region_name"])
        source.reply(f"仅显示区域 §7{context['region_name']} §r 的边界（当前维度）")

    # 记录当前脚下坐标
    def mark_here(self, source: CommandSource):
        if not source.is_player:
            source.reply("§4该命令只能由玩家在游戏内执行！")
            return
        # 使用标记专用权限
        if not source.has_permission_higher_than(self.permission.get("mark", 0)):
            source.reply(f"§4权限不足！你至少需要 {self.permission.get('mark', 0)} 级及以上！")
            return
        if self._get_player_state is None:
            source.reply("§4未能获取玩家坐标，请检查数据源配置！")
            return
        name = source.player
        state = self._get_player_state(name) or {}
        pos = state.get("position")
        dim = state.get("dimension")
        if not pos or dim is None:
            source.reply("§4未获取到你的当前位置，请稍后重试")
            return
        self._marks[name] = {"pos": pos, "dim": dim}
        try:
            from .entry import mark_set
            mark_set(name, pos, dim)
        except Exception:
            pass
        source.reply(f"已记录当前位置：§a{pos[0]} {pos[1]} {pos[2]}§r 维度：§6{dim}§r")

    def clear_mark(self, source: CommandSource):
        if not source.is_player:
            source.reply("§4该命令只能由玩家在游戏内执行！")
            return
        # 使用标记专用权限
        if not source.has_permission_higher_than(self.permission.get("mark", 0)):
            source.reply(f"§4权限不足！你至少需要 {self.permission.get('mark', 0)} 级及以上！")
            return
        name = source.player
        if name in self._marks:
            del self._marks[name]
        try:
            from .entry import mark_clear
            mark_clear(name)
        except Exception:
            pass
        source.reply("已清除你的标记点")

    def _add_from_mark(self, source: CommandSource, context: CommandContext, dim_type: str):
        if not source.is_player:
            source.reply("§4该命令只能由玩家在游戏内执行！")
            return
        if not source.has_permission_higher_than(self.permission["add"]):
            source.reply(f"§4权限不足！你至少需要 {self.permission['add']} 级及以上！")
            return
        if self._get_player_state is None:
            source.reply("§4未能获取玩家坐标，请检查数据源配置！")
            return
        name = source.player
        mark = self._marks.get(name)
        if not mark:
            source.reply("§4没有记录到你的上一次坐标，请先执行 §7!!amt mark§r")
            return
        state = self._get_player_state(name) or {}
        pos_now = state.get("position")
        dim_now = state.get("dimension")
        if not pos_now or dim_now is None:
            source.reply("§4未获取到你的当前位置，请稍后重试")
            return
        if dim_now != mark["dim"]:
            source.reply("§4你当前维度与上次记录的维度不同，请在同一维度内使用")
            return

        # 拼装上下角点
        if dim_type == '2d':
            ctx = {
                "region_name": context["region_name"],
                "x1": int(mark["pos"][0]),
                "z1": int(mark["pos"][2]),
                "x2": int(pos_now[0]),
                "z2": int(pos_now[2]),
                "dimension_id": dim_now,
                "msg": context["msg"],
            }
            self.add_region(source, ctx, '2d')
        else:  # 3d
            ctx = {
                "region_name": context["region_name"],
                "x1": int(mark["pos"][0]),
                "y1": int(mark["pos"][1]),
                "z1": int(mark["pos"][2]),
                "x2": int(pos_now[0]),
                "y2": int(pos_now[1]),
                "z2": int(pos_now[2]),
                "dimension_id": dim_now,
                "msg": context["msg"],
            }
            self.add_region(source, ctx, '3d')

    def add_from_mark_2d(self, source: CommandSource, context: CommandContext):
        self._add_from_mark(source, context, '2d')

    def add_from_mark_3d(self, source: CommandSource, context: CommandContext):
        self._add_from_mark(source, context, '3d')

    # add 命令
    def add_region(self, source: CommandSource, context: CommandContext, dimension_type: str):
        if not source.has_permission_higher_than(self.permission["add"]):
            source.reply(f"§4权限不足！你至少需要 {self.permission['add']} 级及以上！")
            return

        title, subtitle, actionbar, msg = self.parse_region_message(context["msg"])

        # 维度ID规范化：原版别名会被规范化；其他维度保持原样以兼容模组/自定义维度
        raw_dim = str(context["dimension_id"]).strip()
        dim_key = raw_dim.lower()
        dim_id = self._VANILLA_DIM_ALIASES.get(dim_key, raw_dim)

        position = {
            "from": [context["x1"], context["z1"]] if dimension_type == '2d' else [context["x1"], context["y1"], context["z1"]],
            "to": [context["x2"], context["z2"]] if dimension_type == '2d' else [context["x2"], context["y2"], context["z2"]]
        }

        self.data_editor.add(
            context["region_name"],
            {
                "shape": 0 if dimension_type == '2d' else 1,
                "pos": position,
                # 统一保存为规范ID（原版别名会转换）
                "dimension_id": dim_id,
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
        # 用户输入支持 &amt&，保存前先转成 §
        msg = amt_to_section(msg)
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
            display_text = section_to_amt(i)
            msg_rtext.append(
                RText(f"{num + 1}. {display_text}")
                .c(
                    RAction.suggest_command,
                    f"!!amt msg {context['region_name']} editline {num + 1} {display_text}",
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
                region["msg"]["msg"].insert(line_num - 1, amt_to_section(msg))
            else:
                region["msg"]["msg"].append(amt_to_section(msg))
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
        region["msg"]["msg"][context["line_number"] - 1] = amt_to_section(context["line_msg"]) 
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
