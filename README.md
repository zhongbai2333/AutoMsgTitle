# Auto Msg & Title

**MCDR Plugin about Auto Show Title.**

## 插件说明

此插件可以为玩家自动弹出标题或消息，如同插件服进入主城后的标题

同时此插件可为一块区域提供自动的说明，如服务器被参观时，参观者进入某区域、机器之后自动弹出此区域、机器的制造者、名字、功能之类的；在玩家进入某一机器时自动为玩家弹出机器说明书……

这个插件时我写的第三个插件，如有技术力不足的地方请大佬多多包涵，如有BUG请向我提供issue！
此插件许多有关玩家坐标检测的代码我已经尽可能写的高效率了，如果有大佬能在此基础上优化我的代码，可以向我提供pr，非常感谢！

## 注意事项

插件命令前缀为 `!!amt`。

- 颜色输入与存储：游戏内无法输入 `§`，本插件支持用 `&amt&` 代替，保存时会自动转换为 `§`。区域消息的输入格式：
  - `[大标题](小标题)#动作栏#聊天行1;;聊天行2;;...`
  - 示例：`[&amt&6主城](&amt&7欢迎)#&amt&e欢迎光临#&amt&a请沿路指引前行;;&amt&b祝你玩得开心`
- 玩家坐标与列表：依赖 zhongbaisDataAPI 提供回调，无需 RCON 轮询。
- 命令执行：显示 title/actionbar 与可视化粒子均通过 `__mcdr_server.execute` 执行，不再依赖 RCON。
- 可视化性能：区域可视化仅绘制角点（2D 四角 / 3D 八角），不再绘制整条边，显著降低性能消耗。

如需彩色与复杂文本，也可直接在 `data.json` 的 `msg` 中编辑，注意保持 JSON/转义正确。

## 配置说明

`config.json` 关键项：

- permission（各命令的最小权限等级，0:guest 1:user 2:helper 3:admin 4:owner）
  - help, list
  - viz（可视化开关/过滤）
  - mark（标记/清除标记/基于标记建区）
  - add, del, move, msg, info
- debug：是否输出调试日志（包括可视化指令）。
- afk_time：AFK 判定秒数（默认 300）。
- back_region：区域消息冷却秒数（默认 30）。

## 命令说明

基础：

- `!!amt` 显示帮助
- `!!amt list [<页号>]` 区域列表（每页 5 条）

可视化：

- `!!amt viz on` 开启你自己的区域可视化（当前维度）
- `!!amt viz off` 关闭可视化
- `!!amt viz all` 显示当前维度全部区域（仅角点）
- `!!amt viz region <区域名>` 仅显示该区域

标记与基于标记建区：

- `!!amt mark` 记录你当前脚下坐标（仅自己会话内可见）
- `!!amt clearmark` 清除标记
- `!!amt addmark 2d <区域名> <消息>` 基于标记与当前位置创建 2D 区域
- `!!amt addmark 3d <区域名> <消息>` 基于标记与当前位置创建 3D 区域
  - 兼容：`!!amt add_from_mark 2d/3d ...`

直接建区：

- `!!amt add <区域名> 2d <x1> <z1> <x2> <z2> <维度id> <消息>`
- `!!amt add <区域名> 3d <x1> <y1> <z1> <x2> <y2> <z2> <维度id> <消息>`
  - 维度 ID 支持：`overworld/nether/end`、`0/1/2`、完整 ID，如 `minecraft:overworld`；模组/自定义维度同样支持。

消息编辑：

- `!!amt msg <区域名>`
- `!!amt msg <区域名> addline <聊天消息> [<行号>]`
- `!!amt msg <区域名> editline <行号> <聊天消息>`
- `!!amt msg <区域名> delline [<行号>]`

维护：

- `!!amt del <区域名>` 删除区域（需确认）
- `!!amt move <区域名> <序号>` 调整区域优先级（序号从 1 起）

提示：

- 进入区域时将按配置显示 Title、Subtitle、Actionbar 与聊天消息。
- 文本中的颜色/格式请用 `&amt&` 书写，插件会自动转换与保存。
