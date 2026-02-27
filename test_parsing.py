
import re

def map_header(cell: str) -> str:
    key = re.sub(r"\s+", "", str(cell)).lower()
    if "序号" in key or "index" in key:
        return "index"
    if "动作描述" in key or "actiondescription" in key or key == "action":
        return "label"
    if "动素" in key or "therblig" in key:
        return "therblig"
    if "是否加工" in key or "processing" in key:
        return "is_process"
    if "是否搬运" in key or "transport" in key or "move" in key:
        return "is_move"
    if "是否检查" in key or "inspection" in key or "check" in key:
        return "is_check"
    if "是否等待" in key or "waiting" in key or "wait" in key:
        return "is_wait"
    if "是否存储" in key or "storage" in key or "store" in key:
        return "is_store"
    if "预估耗时" in key or "耗时" in key or "duration" in key:
        return "duration"
    if "增值" in key:
        return "value_added"
    if "左右手" in key or (("hand" in key or "hands" in key) and "left" not in key and "right" not in key):
        return "hands"
    if "左手" in key or "left" in key:
        return "left_hand"
    if "右手" in key or "right" in key:
        return "right_hand"
    if "时间段" in key or "时间区间" in key or "timerange" in key or "time" == key:
        return "time_range"
    if "sop" in key:
        return "sop"
    if "波动" in key or "variation" in key:
        return "variation"
    return ""

header_line = "| 序号 | 动作描述 | 动素(Therbligs) | 是否加工 | 是否搬运 | 是否检查 | 是否等待 | 预估耗时(s) | 增值/非增值 | 左右手 | 时间区间 | 波动来源 |"
cells = [p.strip() for p in header_line.split("|")[1:-1]]
print("Cells:", cells)
keys = [map_header(c) for c in cells]
print("Keys:", keys)

row_line = "| 1 | 从左侧料箱抓取底座部件 | 伸手(Reach)+抓取(Grasp) | 否 | 是 | 否 | 否 | 0.7 | NVA | 双手 | 6.3–7.0 | **Yes** (抓取时需在箱内调整角度/寻找) |"
row_cells = [p.strip() for p in row_line.split("|")[1:-1]]
print("Row Cells:", row_cells)

action = {}
for idx, cell in enumerate(row_cells):
    if idx >= len(keys):
        break
    key = keys[idx]
    if key:
        action[key] = cell

print("Action:", action)
