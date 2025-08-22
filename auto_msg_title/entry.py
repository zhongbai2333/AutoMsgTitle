import time
import threading
from typing import List, Dict, Any
from mcdreforged.api.all import *

from .config import Config
from .command_actions import CommandActions
from zhongbais_data_api import zbDataAPI
from .tools import (
    normalize_dimension_id,
    extract_position,
    extract_dimension,
    to_component_json,
)

# ===== 全局状态 =====
__mcdr_server: PluginServerInterface | None = None
config: Config | None = None
player_info: Dict[str, Dict[str, Any]] = {}
stop_status: bool = False

# 可视化状态
_viz_viewers: Dict[str, Dict[str, Any]] = {}
_viz_thread: threading.Thread | None = None
_viz_running: bool = False

# 每玩家 mark 状态
_mark_points: Dict[str, Dict[str, Any]] = {}


# ===== API 回调（由 zhongbaisDataAPI 驱动） =====

def _on_api_player_info(name: str, info: dict):
    pos = extract_position(info)
    dim_raw = extract_dimension(info)
    dim = normalize_dimension_id(dim_raw)
    if pos is None or dim is None:
        return
    edit_player_info(name, pos, dim)


def _on_api_player_list(player_name: str, player_list: list):
    now = int(time.time())
    online_set = set(player_list or [])

    # 清理离线
    for name in list(player_info.keys()):
        if name not in online_set:
            del player_info[name]

    # 补充在线占位
    for name in online_set:
        if name not in player_info:
            player_info[name] = {
                "position": None,
                "dimension": None,
                "last_update_time": now,
                "is_afk": False,
                "last_region": {},
            }


# ===== 业务逻辑 =====

def is_player_in_any_region(xyz, dimension):
    from .storage import global_data_json

    px, py, pz = xyz
    for region_name, region_data in global_data_json.items():
        if dimension != region_data.get("dimension_id"):
            continue
        if region_data.get("shape", 0) == 0:
            x1, z1 = region_data["pos"]["from"]
            x2, z2 = region_data["pos"]["to"]
            if min(x1, x2) <= px <= max(x1, x2) and min(z1, z2) <= pz <= max(z1, z2):
                return region_name
        else:
            x1, y1, z1 = region_data["pos"]["from"]
            x2, y2, z2 = region_data["pos"]["to"]
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

    # 位置未变：AFK 计时
    if player_data["position"] == xyz_now:
        if current_time - player_data["last_update_time"] >= (config.afk_time if config else 120):
            if not player_data["is_afk"]:
                player_data["is_afk"] = True
                if __mcdr_server:
                    __mcdr_server.say(f"§7{player_name} 开始 AFK")
    else:
        # 区域进入提示
        last_region = player_data.get("last_region", {})
        in_region_now = is_player_in_any_region(xyz_now, dimension_now)
        if in_region_now not in last_region.keys() and in_region_now:
            print_title(in_region_now, player_name)
        for k in list(last_region.keys()):
            if current_time - last_region[k] > (config.back_region if config else 15):
                del last_region[k]
        if in_region_now:
            last_region[in_region_now] = current_time

        # AFK 恢复提示
        if player_data.get("is_afk"):
            if __mcdr_server:
                __mcdr_server.say(
                    f"§7{player_name} 退出 AFK 共用时 {current_time - player_data['last_update_time']} 秒"
                )

        # 更新状态
        player_data["position"] = xyz_now
        player_data["dimension"] = dimension_now
        player_data["last_update_time"] = current_time
        player_data["is_afk"] = False
        player_data["last_region"] = last_region

    player_info[player_name] = player_data


def print_title(region_name, player_name):
    from .storage import global_data_json

    region_msg = global_data_json[region_name]["msg"]
    if region_msg.get("title"):
        title_json = to_component_json(region_msg.get("title"))
        exec_command(f'title "{player_name}" title {title_json}')
        if region_msg.get("subtitle"):
            subtitle_json = to_component_json(region_msg.get("subtitle"))
            exec_command(f'title "{player_name}" subtitle {subtitle_json}')
    if region_msg.get("actionbar"):
        actionbar_json = to_component_json(region_msg.get("actionbar"))
        exec_command(f'title "{player_name}" actionbar {actionbar_json}')
    if region_msg.get("msg"):
        for i in region_msg["msg"]:
            if __mcdr_server:
                __mcdr_server.tell(player_name, i)


def debug_print(msg: str):
    try:
        if config and getattr(config, "debug", False) and __mcdr_server is not None:
            __mcdr_server.logger.info(msg)
    except Exception:
        pass


# ===== 命令执行（不经 RCON） =====

def exec_command(command: str):
    if __mcdr_server is None:
        return
    try:
        __mcdr_server.execute(command)
    except Exception as e:
        debug_print(f"[AMT] execute error: {e} :: {command}")


# ===== 插件生命周期 =====

def on_load(server: PluginServerInterface, _):
    global __mcdr_server, player_info, stop_status, config, _viz_viewers, _viz_thread, _viz_running
    __mcdr_server = server
    player_info = {}
    stop_status = False
    _viz_viewers = {}
    _viz_thread = None
    _viz_running = False

    # 加载设置
    loaded = __mcdr_server.load_config_simple(target_class=Config)
    if isinstance(loaded, Config) or loaded is not None:
        globals()["config"] = loaded  # type: ignore
    else:
        globals()["config"] = Config()  # type: ignore

    # 创建命令系统，提供获取玩家当前坐标+维度的回调
    def _get_player_state(name: str):
        info = player_info.get(name)
        if not info:
            return None
        return {
            "position": info.get("position"),
            "dimension": info.get("dimension"),
        }

    CommandActions(__mcdr_server, config.permission, get_player_state=_get_player_state)

    # 注册 zhongbaisDataAPI 回调
    try:
        zbDataAPI.register_player_info_callback(_on_api_player_info)
        zbDataAPI.register_player_list_callback(_on_api_player_list)
        zbDataAPI.refresh_getpos()
    except Exception as e:
        __mcdr_server.logger.error(f"注册 zhongbaisDataAPI 回调失败: {e}")


def on_unload(_):
    global stop_status, _viz_running, _viz_thread
    stop_status = True
    _viz_running = False
    if _viz_thread and _viz_thread.is_alive():
        try:
            _viz_thread.join(timeout=1.0)
        except Exception:
            pass


def on_server_startup(_):
    global stop_status
    stop_status = False
    try:
        zbDataAPI.refresh_getpos()
    except Exception:
        pass


# ================= 可视化区域（粒子边框） =================


def _iter_line_points(p1, p2, step=0.5):
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
    length = max(1.0, (dx * dx + dy * dy + dz * dz) ** 0.5)
    n = max(1, int(length / step))
    for i in range(n + 1):
        t = i / n
        yield (x1 + dx * t, y1 + dy * t, z1 + dz * t)


def _emit_region_particles_for_player(player: str, region_name: str, region_data: dict, y_hint: float):
    shape = region_data.get("shape", 0)
    dim = region_data.get("dimension_id")

    def emit_corner(x, y, z, r=0.0, g=1.0, b=1.0, scale=1.8, dx=0.12, dy=0.12, dz=0.12, count=10):
        cmd = (
            f"particle minecraft:dust {r} {g} {b} {scale} "
            f"{x:.2f} {y:.2f} {z:.2f} {dx} {dy} {dz} 0 {count} force {player}"
        )
        if config and getattr(config, 'debug', False):
            debug_print(f"[EXEC] {cmd}")
        exec_command(cmd)

    if shape == 0:
        # 2D: 仅四个角
        x1, z1 = region_data["pos"]["from"]
        x2, z2 = region_data["pos"]["to"]
        y = y_hint
        for (x, z) in [(x1, z1), (x2, z1), (x1, z2), (x2, z2)]:
            emit_corner(x, y, z)
    else:
        # 3D: 仅八个角
        x1, y1, z1 = region_data["pos"]["from"]
        x2, y2, z2 = region_data["pos"]["to"]
        corners = [
            (x1, y1, z1), (x2, y1, z1), (x1, y2, z1), (x2, y2, z1),
            (x1, y1, z2), (x2, y1, z2), (x1, y2, z2), (x2, y2, z2)
        ]
        for (x, y, z) in corners:
            emit_corner(x, y, z)


def _emit_box_for_player(player: str, p_from: list, p_to: list):
    """绘制任意两点定义的 2D/3D 角标（不画边），颜色橙色，随 mark 跟随。"""
    x1, y1, z1 = p_from
    x2, y2, z2 = p_to
    same_y = int(y1) == int(y2)

    def emit_corner(x, y, z, r=1.0, g=0.5, b=0.0, scale=1.8, dx=0.12, dy=0.12, dz=0.12, count=10):
        cmd = (
            f"particle minecraft:dust {r} {g} {b} {scale} "
            f"{x:.2f} {y:.2f} {z:.2f} {dx} {dy} {dz} 0 {count} force {player}"
        )
        if config and getattr(config, 'debug', False):
            debug_print(f"[EXEC] {cmd}")
        exec_command(cmd)

    if same_y:
        y = float(y1)
        for (x, z) in [(x1, z1), (x2, z1), (x1, z2), (x2, z2)]:
            emit_corner(x, y, z)
    else:
        corners = [
            (x1, y1, z1), (x2, y1, z1), (x1, y2, z1), (x2, y2, z1),
            (x1, y1, z2), (x2, y1, z2), (x1, y2, z2), (x2, y2, z2)
        ]
        for (x, y, z) in corners:
            emit_corner(x, y, z)


def _viz_loop():
    global _viz_running, _viz_viewers
    from .storage import global_data_json

    debug_print("[AMT] Viz loop started")
    while _viz_running and not stop_status:
        try:
            # 渲染选中区域
            viewers = dict(_viz_viewers)
            for name, sel in viewers.items():
                info = player_info.get(name)
                if not info:
                    continue
                y_hint = float((info.get("position") or [0, 64, 0])[1] or 64)
                dim_now = info.get("dimension")
                if dim_now is None:
                    continue
                def show_region(k, v):
                    if v.get("dimension_id") == dim_now:
                        _emit_region_particles_for_player(name, k, v, y_hint)
                if sel and sel.get("region"):
                    rn = sel["region"]
                    data = global_data_json.get(rn)
                    if data:
                        show_region(rn, data)
                else:
                    for k, v in global_data_json.items():
                        show_region(k, v)

            # 渲染 mark 跟随框
            for name, m in list(_mark_points.items()):
                info = player_info.get(name)
                if not info:
                    continue
                pos_now = info.get("position")
                dim_now = info.get("dimension")
                if not pos_now or dim_now is None:
                    continue
                if dim_now != m.get("dim"):
                    continue
                _emit_box_for_player(name, m.get("pos"), pos_now)
        except Exception as e:
            debug_print(f"[AMT] viz loop error: {e}")
        time.sleep(1.0)


def _start_viz_if_needed():
    global _viz_running, _viz_thread
    if _viz_running:
        return
    _viz_running = True
    debug_print("[AMT] starting viz thread")
    _viz_thread = threading.Thread(target=_viz_loop, name="AMT-Viz", daemon=True)
    _viz_thread.start()


def viz_set_viewer(player: str, region_name: str | None):
    global _viz_viewers
    _viz_viewers[player] = {"region": region_name}
    debug_print(f"[AMT] viz set viewer={player}, region={region_name}")
    _start_viz_if_needed()


def viz_remove_viewer(player: str):
    global _viz_viewers, _viz_running
    if player in _viz_viewers:
        del _viz_viewers[player]
    debug_print(f"[AMT] viz remove viewer={player}")
    if not _viz_viewers and not _mark_points:
        _viz_running = False
        debug_print("[AMT] no viewers/marks, stopping viz loop")


def mark_set(player: str, pos: list, dim: str):
    _mark_points[player] = {"pos": pos, "dim": dim}
    _start_viz_if_needed()


def mark_clear(player: str):
    global _viz_running
    if player in _mark_points:
        del _mark_points[player]
    if not _viz_viewers and not _mark_points:
        _viz_running = False
        debug_print("[AMT] no viewers/marks, stopping viz loop")


def mark_get(player: str):
    return _mark_points.get(player)


def get_viz_status():
    return {"running": _viz_running, "viewers": list(_viz_viewers.keys())}


# ===== 在线玩家事件（留空，状态由 API 回调维护） =====

def on_player_joined(_, player, __):
    pass


def on_player_left(_, player):
    pass
