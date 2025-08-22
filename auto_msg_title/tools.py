import json
from typing import List, Optional, Dict, Any

# 原版维度别名映射（用于规范化常见输入）
_DIM_ALIASES = {
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


def normalize_dimension_id(raw: Optional[str]) -> Optional[str]:
    """将常见原版维度别名规范化，其余保持原样（兼容模组/自定义维度）。"""
    if raw is None:
        return raw
    key = str(raw).strip().lower()
    return _DIM_ALIASES.get(key, raw)


def extract_position(info: Dict[str, Any]) -> Optional[List[int]]:
    """从常见字段中提取玩家坐标，返回 [x, y, z]（int）。"""
    for k in ("position", "pos", "Pos", "xyz", "XYZ"):
        if k in info:
            val = info[k]
            break
    else:
        return None
    try:
        if isinstance(val, (list, tuple)) and len(val) >= 3:
            return [int(float(val[0])), int(float(val[1])), int(float(val[2]))]
        if isinstance(val, str) and val.startswith("[") and "]" in val:
            parts = val.strip("[] ").split(",")
            return [int(float(parts[0])), int(float(parts[1])), int(float(parts[2]))]
    except Exception:
        return None
    return None


def extract_dimension(info: Dict[str, Any]) -> Optional[str]:
    """从常见字段中提取玩家维度字符串。"""
    for k in ("dimension", "Dimension", "dim", "Dim"):
        if k in info:
            return str(info[k])
    return None


# § 颜色/格式码映射
_COLOR_MAP = {
    "0": "black",
    "1": "dark_blue",
    "2": "dark_green",
    "3": "dark_aqua",
    "4": "dark_red",
    "5": "dark_purple",
    "6": "gold",
    "7": "gray",
    "8": "dark_gray",
    "9": "blue",
    "a": "green",
    "b": "aqua",
    "c": "red",
    "d": "light_purple",
    "e": "yellow",
    "f": "white",
}


def to_component_json(text: str) -> str:
    """将§颜色码文本转换为 JSON 文本组件字符串。"""
    comp = to_component(text or "")
    return json.dumps(comp, ensure_ascii=False)


def to_component(text: str) -> Dict[str, Any]:
    """将§颜色/格式码文本转换为 JSON 文本组件对象。"""
    root: Dict[str, Any] = {"text": ""}
    if not text:
        return root

    segments: List[Dict[str, Any]] = []
    state = {
        "color": None,
        "bold": False,
        "italic": False,
        "underlined": False,
        "strikethrough": False,
        "obfuscated": False,
    }
    buf: List[str] = []

    def flush():
        if not buf:
            return
        seg: Dict[str, Any] = {"text": "".join(buf)}
        buf.clear()
        if state["color"]:
            seg["color"] = state["color"]
        for k in ("bold", "italic", "underlined", "strikethrough", "obfuscated"):
            if state[k]:
                seg[k] = True
        segments.append(seg)

    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "§" and i + 1 < n:
            code = text[i + 1]
            # HEX 颜色 §x§R§R§G§G§B§B
            if code.lower() == "x" and i + 13 <= n:
                hex_chars = []
                ok = True
                j = i + 2
                for _ in range(6):
                    if j < n and text[j] == "§" and j + 1 < n:
                        hex_chars.append(text[j + 1])
                        j += 2
                    else:
                        ok = False
                        break
                if ok:
                    flush()
                    state.update({
                        "color": "#" + "".join(hex_chars),
                        "bold": False,
                        "italic": False,
                        "underlined": False,
                        "strikethrough": False,
                        "obfuscated": False,
                    })
                    i = j
                    continue
            # 常规颜色/格式
            code = code.lower()
            i += 2
            if code in _COLOR_MAP:
                flush()
                state.update({
                    "color": _COLOR_MAP[code],
                    "bold": False,
                    "italic": False,
                    "underlined": False,
                    "strikethrough": False,
                    "obfuscated": False,
                })
                continue
            if code == "k":
                flush(); state["obfuscated"] = True; continue
            if code == "l":
                flush(); state["bold"] = True; continue
            if code == "m":
                flush(); state["strikethrough"] = True; continue
            if code == "n":
                flush(); state["underlined"] = True; continue
            if code == "o":
                flush(); state["italic"] = True; continue
            if code == "r":
                flush()
                state.update({
                    "color": None,
                    "bold": False,
                    "italic": False,
                    "underlined": False,
                    "strikethrough": False,
                    "obfuscated": False,
                })
                continue
            # 未识别，按字面添加
            buf.append("§" + code)
            continue
        else:
            buf.append(ch)
            i += 1

    flush()
    if segments:
        root["extra"] = segments
    return root


# &amt& 和 § 的互转（用于输入与存储之间转换）
def amt_to_section(text: str) -> str:
    return text.replace("&amt&", "§") if isinstance(text, str) else text


def section_to_amt(text: str) -> str:
    return text.replace("§", "&amt&") if isinstance(text, str) else text
