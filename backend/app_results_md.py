import re
from typing import Dict, List


def _parse_time_str(t_str: str) -> float:
    t_str = str(t_str).strip()
    try:
        return float(t_str)
    except ValueError:
        pass
    parts = t_str.split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    raise ValueError(f"Invalid time format: {t_str}")


def parse_md_content(content: str) -> Dict[str, object]:
    sections: Dict[str, object] = {"overview": "", "actions": [], "deep_dive": "", "kaizen": ""}
    lines = (content or "").splitlines()
    current_section = None
    action_table_lines: List[str] = []

    for line in lines:
        if line.strip():
            if line.strip().startswith("|"):
                current_section = "actions_header"
            break

    re_overview = re.compile(r"^##\s+1\.\s*(工序概览|Overview)", re.IGNORECASE)
    re_actions = re.compile(r"^##\s+2\.\s*(详细动作分析表|Motion Breakdown)", re.IGNORECASE)
    re_deep_dive = re.compile(r"^##\s+3\.\s*(深度诊断发现|Deep Dive Findings)", re.IGNORECASE)
    re_kaizen = re.compile(r"^##\s+4\.\s*(改善机会|Kaizen Opportunities)", re.IGNORECASE)

    for line in lines:
        if re_overview.match(line):
            current_section = "overview"
            continue
        if re_actions.match(line):
            current_section = "actions_header"
            continue
        if re_deep_dive.match(line):
            current_section = "deep_dive"
            continue
        if re_kaizen.match(line):
            current_section = "kaizen"
            continue
        if line.strip().startswith("## "):
            current_section = None

        if current_section == "overview":
            sections["overview"] = str(sections.get("overview") or "") + line + "\n"
        elif current_section == "deep_dive":
            sections["deep_dive"] = str(sections.get("deep_dive") or "") + line + "\n"
        elif current_section == "kaizen":
            sections["kaizen"] = str(sections.get("kaizen") or "") + line + "\n"
        elif current_section == "actions_header":
            if line.strip().startswith("|"):
                action_table_lines.append(line)
            elif not line.strip() and action_table_lines:
                current_section = None

    actions: List[Dict[str, object]] = []
    if len(action_table_lines) > 2:
        for row_line in action_table_lines[2:]:
            parts = [p.strip() for p in row_line.split("|")]
            if len(parts) < 9:
                continue
            try:
                time_range = parts[8]
                start_time = 0.0
                end_time = 0.0
                if "-" in time_range:
                    t_parts = time_range.split("-")
                    start_time = _parse_time_str(t_parts[0])
                    end_time = _parse_time_str(t_parts[1])
                action = {
                    "index": parts[1],
                    "label": parts[2],
                    "sop": parts[3],
                    "left_hand": parts[4],
                    "right_hand": parts[5],
                    "duration": parts[6],
                    "value_added": parts[7],
                    "time_range": parts[8],
                    "start_time": start_time,
                    "end_time": end_time,
                }
                actions.append(action)
            except Exception:
                continue

    sections["actions"] = actions
    sections["overview"] = str(sections.get("overview") or "").strip()
    sections["deep_dive"] = str(sections.get("deep_dive") or "").strip()
    sections["kaizen"] = str(sections.get("kaizen") or "").strip()
    return sections


def update_md_content(content: str, new_actions: List[Dict[str, object]]) -> str:
    lines = (content or "").splitlines()
    new_lines: List[str] = []
    re_actions = re.compile(r"^##\s+2\.\s*(详细动作分析表|Motion Breakdown)", re.IGNORECASE)

    is_table_only = False
    if not (content or "").strip():
        is_table_only = True
    else:
        for line in lines:
            if line.strip():
                if line.strip().startswith("|"):
                    is_table_only = True
                break

    if is_table_only:
        new_lines.append("| 序号 | 动作描述 | SOP 操作步骤 | 左手状态 | 右手状态 | 预估耗时(s) | 增值/非增值 | 时间段 |")
        new_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for idx, act in enumerate(new_actions, 1):
            label = act.get("label", "")
            sop = act.get("sop", "") or act.get("type", "")
            left = act.get("left_hand", "")
            right = act.get("right_hand", "")
            duration = act.get("duration", "")
            val = act.get("value_added", "")
            trange = act.get("time_range", "")
            row = f"| {idx} | {label} | {sop} | {left} | {right} | {duration} | {val} | {trange} |"
            new_lines.append(row)
        return "\n".join(new_lines)

    i = 0
    while i < len(lines):
        line = lines[i]
        if re_actions.match(line):
            new_lines.append(line)
            i += 1
            while i < len(lines):
                l = lines[i]
                new_lines.append(l)
                if l.strip().startswith("|"):
                    i += 1
                    if i < len(lines):
                        new_lines.append(lines[i])
                        i += 1
                    for idx, act in enumerate(new_actions, 1):
                        label = act.get("label", "")
                        sop = act.get("sop", "") or act.get("type", "")
                        left = act.get("left_hand", "")
                        right = act.get("right_hand", "")
                        duration = act.get("duration", "")
                        val = act.get("value_added", "")
                        trange = act.get("time_range", "")
                        if "start_time" in act and "end_time" in act:
                            try:
                                s = float(act["start_time"])
                                e = float(act["end_time"])
                                d = max(0, e - s)
                                duration = f"{d:.1f}"
                                trange = f"{s:.2f} - {e:.2f}"
                            except Exception:
                                pass
                        row = f"| {idx} | {label} | {sop} | {left} | {right} | {duration} | {val} | {trange} |"
                        new_lines.append(row)
                    while i < len(lines):
                        next_l = lines[i]
                        if not next_l.strip() or not next_l.strip().startswith("|"):
                            break
                        i += 1
                    break
                i += 1
            continue
        new_lines.append(line)
        i += 1
    return "\n".join(new_lines)

