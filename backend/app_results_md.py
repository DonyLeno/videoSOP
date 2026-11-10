import re
from typing import Dict, List


def _parse_time_str(t_str: str) -> float:
    t_str = str(t_str).strip()
    t_str = re.sub(r"[^\d:.]+$", "", t_str)
    try:
        return float(t_str)
    except ValueError:
        pass
    parts = t_str.split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        a_raw, b_raw = parts[0].strip(), parts[1].strip()
        a = float(a_raw)
        if "." in b_raw:
            b = float(b_raw)
            return a * 60 + b
        b = float(b_raw)
        if a <= 2 and 0 <= b <= 59:
            return a * 60 + b
        if 0 <= b <= 99:
            return a + b / 100.0
        return a * 60 + b
    raise ValueError(f"Invalid time format: {t_str}")


def normalize_md_content(content: str) -> str:
    """修复模型输出的紧凑 Markdown：拆分行内标题、分隔线与粘连的表格行。"""
    text = str(content or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return ""
    # 行首标题缺少空格，如 “###1.工序概览” -> “### 1.工序概览”
    text = re.sub(r"^(#{1,6})(?=[^\s#])", r"\1 ", text, flags=re.M)
    # 分隔线与标题粘连，如 “---### 5. 浪费识别” -> “---\n### 5. 浪费识别”
    text = re.sub(r"-{2,}[ \t]*(#{1,6})[ \t]*(?=[^\s#])", r"\n---\n\1 ", text)
    text = re.sub(r"-{2,}[ \t]*(#{1,6})[ \t]+", r"\n---\n\1 ", text)
    # 表格数据行被粘连，如 “… || 3 | 5 | …”（需同时满足 Cycle 与序号两列都是数字，避免拆错空单元格）
    text = re.sub(r"\|\|(?=[ \t]*\d{1,2}[ \t]*\|[ \t]*\d{1,3}[ \t]*\|)", "|\n|", text)
    # 表头与分隔行被粘连，如 “… || :--- | …”
    text = re.sub(r"\|\|(?=[ \t]*:?-{3,})", "|\n|", text)
    return text


def parse_md_content(content: str) -> Dict[str, object]:
    sections: Dict[str, object] = {"overview": "", "actions": [], "deep_dive": "", "kaizen": ""}
    lines = normalize_md_content(content).splitlines()
    current_section = None
    action_table_lines: List[str] = []
    preface_lines: List[str] = []
    seen_any_section = False

    for line in lines:
        if line.strip():
            if line.strip().startswith("|"):
                current_section = "actions_header"
            break

    re_overview = re.compile(r"^#{1,6}\s*.*(工序概览|Overview)", re.IGNORECASE)
    re_actions = re.compile(r"^#{1,6}\s*.*(动作分析|Motion Breakdown|Motion Analysis)", re.IGNORECASE)
    re_deep_dive = re.compile(r"^#{1,6}\s*.*(深度诊断|Deep Dive|DeepDive)", re.IGNORECASE)
    re_kaizen = re.compile(r"^#{1,6}\s*.*(改善|Kaizen)", re.IGNORECASE)
    re_waste = re.compile(r"^#{1,6}\s*.*(浪费|Muda)", re.IGNORECASE)
    re_therbligs = re.compile(r"^#{1,6}\s*.*(动素|Therblig)", re.IGNORECASE)
    re_supplement = re.compile(r"^#{1,6}\s*.*(补充|Supplement)", re.IGNORECASE)
    re_notes = re.compile(r"^#{1,6}\s*.*(备注|Notes|Confidence|Limitations|限制|补拍)", re.IGNORECASE)

    for line in lines:
        if not seen_any_section:
            if (
                re_overview.match(line)
                or re_actions.match(line)
                or re_deep_dive.match(line)
                or re_kaizen.match(line)
                or re_waste.match(line)
                or re_therbligs.match(line)
                or re_supplement.match(line)
                or re_notes.match(line)
            ):
                seen_any_section = True
            else:
                if current_section is None:
                    preface_lines.append(line)
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
        if re_waste.match(line) or re_therbligs.match(line):
            current_section = "deep_dive"
            continue
        if re_supplement.match(line) or re_notes.match(line):
            current_section = "kaizen"
            continue
        if re.match(r"^#{1,6}\s*\S", line):
            # 未归类的标题：保留到工序概览，避免正文丢失
            current_section = "overview"
            sections["overview"] = str(sections.get("overview") or "") + line + "\n"
            continue

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
        header_cells = [p.strip() for p in action_table_lines[0].split("|")[1:-1]]
        table_rows: List[List[str]] = []

        def map_header(cell: str) -> str:
            key = re.sub(r"\s+", "", str(cell)).lower()
            if key == "cycle" or "循环" in key or "週期" in key:
                return "cycle"
            if "序号" in key or "index" in key or "no." in key or key == "no":
                return "index"
            if "动作描述" in key or "actiondescription" in key or key == "action" or "motion" in key or "description" in key:
                return "label"
            if "动素" in key or "therblig" in key:
                return "therblig"
            if "是否加工" in key or "processing" in key or "process" in key:
                return "is_process"
            if "是否搬运" in key or "transport" in key or "move" in key or "conveyance" in key:
                return "is_move"
            if "是否检查" in key or "inspection" in key or "check" in key:
                return "is_check"
            if "是否等待" in key or "waiting" in key or "wait" in key:
                return "is_wait"
            if "是否存储" in key or "storage" in key or "store" in key:
                return "is_store"
            if "预估耗时" in key or "耗时" in key or "duration" in key or "estimatedtime" in key:
                return "duration"
            if "增值" in key or key == "va/nva" or "va/nva" in key or "value" in key:
                return "value_added"
            if "左右手" in key or (("hand" in key or "hands" in key) and "left" not in key and "right" not in key):
                return "hands"
            if "左手" in key or "left" in key:
                return "left_hand"
            if "右手" in key or "right" in key:
                return "right_hand"
            if "置信度" in key or key == "confidence":
                return "confidence"
            if "可见性" in key or key == "visibility":
                return "visibility"
            if "证据描述" in key or "evidence" in key:
                return "evidence"
            if (
                "时间段" in key
                or "时间区间" in key
                or "timerange" in key
                or "timesegment" in key
                or ("time" in key and "segment" in key)
                or "time" == key
                or "range" in key
                or "timeinterval" in key
            ):
                return "time_range"
            if "sop" in key:
                return "sop"
            if "波动" in key or "variation" in key:
                return "variation"
            if "备注" in key or "notes" in key:
                return "notes"
            return ""

        header_keys = [map_header(cell) for cell in header_cells]
        try:
            idx_col = header_keys.index("index")
        except ValueError:
            idx_col = 0

        for row_line in action_table_lines[1:]:
            cells = [p.strip() for p in row_line.split("|")[1:-1]]
            if not cells:
                continue
            if len(cells) < len(header_cells):
                cells = cells + [""] * (len(header_cells) - len(cells))

            idx_cell = str(cells[idx_col] if idx_col < len(cells) else "").strip()
            idx_norm = re.sub(r"[^0-9]", "", idx_cell)
            try:
                idx_num = int(idx_norm) if idx_norm != "" else -1
            except Exception:
                idx_num = -1

            is_dashes_row = True
            for c in cells:
                cc = str(c or "").strip()
                if not cc:
                    continue
                if not re.fullmatch(r"[-:\s]+", cc):
                    is_dashes_row = False
                    break

            is_action_row_by_index = idx_num >= 1
            if is_action_row_by_index and not is_dashes_row:
                table_rows.append(cells)

            action: Dict[str, object] = {}
            for idx, cell in enumerate(cells):
                # Map to keys if within header range, otherwise ignore for object mapping
                # (but the row data is preserved in table_rows for display)
                if idx >= len(header_keys):
                    break
                key = header_keys[idx]
                if key:
                    action[key] = cell
                raw_header = re.sub(r"\s+", "", str(header_cells[idx])).lower() if idx < len(header_cells) else ""
                if (
                    ("time" in raw_header and "evidence" in raw_header)
                    or ("时间" in raw_header and "证据" in raw_header)
                ):
                    parts = re.split(r"[｜|]", str(cell), maxsplit=1)
                    left = parts[0].strip() if parts else ""
                    right = parts[1].strip() if len(parts) > 1 else ""
                    if left:
                        action["time_range"] = left
                    if right:
                        action["evidence"] = right
            if "cycle" in action and not str(action.get("cycle") or "").strip():
                action["cycle"] = "1"

            time_range = str(action.get("time_range") or "").strip()
            start_time = 0.0
            end_time = 0.0
            if time_range:
                normalized = (
                    time_range.replace("–", "-")
                    .replace("—", "-")
                    .replace("~", "-")
                    .replace("～", "-")
                    .replace("至", "-")
                    .replace("to", "-")
                )
                if "-" in normalized:
                    t_parts = [p.strip() for p in normalized.split("-") if p.strip()]
                else:
                    t_parts = []
            else:
                t_parts = []
            if len(t_parts) >= 2:
                try:
                    start_time = _parse_time_str(t_parts[0])
                    end_time = _parse_time_str(t_parts[1])
                except Exception:
                    start_time = 0.0
                    end_time = 0.0
            action["start_time"] = start_time
            action["end_time"] = end_time
            idx_cell2 = str(action.get("index") or "").strip()
            idx_norm2 = re.sub(r"[^0-9]", "", idx_cell2)
            is_action_row = bool(idx_norm2) and float(end_time) > float(start_time)
            if is_action_row:
                actions.append(action)

        sections["actions_table"] = {"headers": header_cells, "rows": table_rows}

    sections["actions"] = actions
    preface = "\n".join(preface_lines).strip()
    overview = str(sections.get("overview") or "").strip()
    if preface:
        sections["overview"] = (preface + "\n\n" + overview).strip() if overview else preface
    else:
        sections["overview"] = overview
    sections["deep_dive"] = str(sections.get("deep_dive") or "").strip()
    sections["kaizen"] = str(sections.get("kaizen") or "").strip()
    return sections


def update_md_content(content: str, new_actions: List[Dict[str, object]]) -> str:
    lines = (content or "").splitlines()
    new_lines: List[str] = []
    re_actions = re.compile(r"^#{2,6}\s+(?:\d+\.\s*)?(详细动作分析表|Motion Breakdown)", re.IGNORECASE)

    def split_row_cells(row_line: str) -> List[str]:
        return [p.strip() for p in str(row_line).split("|")[1:-1]]

    def format_row(cells: List[object]) -> str:
        return "| " + " | ".join(str(x or "") for x in cells) + " |"

    def map_header(cell: str) -> str:
        key = re.sub(r"\s+", "", str(cell)).lower()
        if key == "cycle" or "循环" in key or "週期" in key:
            return "cycle"
        if "序号" in key or "index" in key or "no." in key or key == "no":
            return "index"
        if "动作描述" in key or "actiondescription" in key or key == "action" or "motion" in key or "description" in key:
            return "label"
        if "动素" in key or "therblig" in key:
            return "therblig"
        if "是否加工" in key or "processing" in key or "process" in key:
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
        if "增值" in key or key == "va/nva" or "va/nva" in key or "value" in key:
            return "value_added"
        if "左右手" in key or (("hand" in key or "hands" in key) and "left" not in key and "right" not in key):
            return "hands"
        if "左手" in key or "left" in key:
            return "left_hand"
        if "右手" in key or "right" in key:
            return "right_hand"
        if "置信度" in key or key == "confidence":
            return "confidence"
        if "可见性" in key or key == "visibility":
            return "visibility"
        if "证据描述" in key or "evidence" in key:
            return "evidence"
        if (
            "时间段" in key
            or "时间区间" in key
            or "timerange" in key
            or "timesegment" in key
            or ("time" in key and "segment" in key)
            or "time" == key
            or "range" in key
        ):
            return "time_range"
        if "sop" in key:
            return "sop"
        if "波动" in key or "variation" in key:
            return "variation"
        return ""

    def extract_start_end(act: Dict[str, object]):
        s = act.get("start_time")
        e = act.get("end_time")
        try:
            s2 = float(s) if s is not None else None
            e2 = float(e) if e is not None else None
            if s2 is not None and e2 is not None and e2 > s2:
                return s2, e2
        except Exception:
            pass

        for key in ("time_range", "duration"):
            tr = str(act.get(key) or "").strip()
            if not tr:
                continue
            normalized = (
                tr.replace("–", "-")
                .replace("—", "-")
                .replace("~", "-")
                .replace("～", "-")
                .replace("至", "-")
                .replace("to", "-")
            )
            if "-" not in normalized:
                continue
            t_parts = [p.strip() for p in normalized.split("-") if p.strip()]
            if len(t_parts) < 2:
                continue
            try:
                s3 = _parse_time_str(t_parts[0])
                e3 = _parse_time_str(t_parts[1])
                if e3 > s3:
                    return float(s3), float(e3)
            except Exception:
                continue

        return None, None

    def index_col_from_header_line(header_line: str) -> int:
        header_cells = split_row_cells(header_line)
        if not header_cells:
            return 0
        keys = [map_header(c) for c in header_cells]
        try:
            return keys.index("index")
        except ValueError:
            return 0

    def build_table_lines(header_line: str, delim_line: str, extra_row_lines: List[str] = None) -> List[str]:
        header_cells = split_row_cells(header_line)
        if not header_cells:
            header_cells = [
                "序号",
                "动作描述",
                "SOP 操作步骤",
                "左手状态",
                "右手状态",
                "预估耗时(s)",
                "增值/非增值",
                "时间段",
            ]
            header_line2 = format_row(header_cells)
            delim_line2 = "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
            header_line = header_line2
            delim_line = delim_line2

        keys = [map_header(c) for c in header_cells]
        out = [header_line, delim_line]
        for idx, act in enumerate(new_actions or [], 1):
            a = act if isinstance(act, dict) else {}
            s, e = extract_start_end(a)
            duration = a.get("duration", "")
            trange = a.get("time_range", "")
            if s is not None and e is not None:
                duration = f"{max(0.0, e - s):.1f}"
                trange = f"{s:.2f} - {e:.2f}"

            row_cells: List[object] = []
            for k in keys:
                if k == "cycle":
                    row_cells.append(a.get("cycle") or "1")
                elif k == "index":
                    row_cells.append(str(idx))
                elif k == "label":
                    row_cells.append(a.get("label", ""))
                elif k == "sop":
                    row_cells.append(a.get("sop", "") or a.get("type", ""))
                elif k == "left_hand":
                    row_cells.append(a.get("left_hand", ""))
                elif k == "right_hand":
                    row_cells.append(a.get("right_hand", ""))
                elif k == "duration":
                    row_cells.append(duration)
                elif k == "value_added":
                    row_cells.append(a.get("value_added", ""))
                elif k == "time_range":
                    row_cells.append(trange)
                elif k == "hands":
                    row_cells.append(a.get("hands", ""))
                elif k:
                    row_cells.append(a.get(k, ""))
                else:
                    row_cells.append("")
            out.append(format_row(row_cells))
        for r in extra_row_lines or []:
            if str(r).strip().startswith("|"):
                out.append(str(r).rstrip())
        return out

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
        header_line = ""
        delim_line = ""
        extra_rows: List[str] = []
        for j, line in enumerate(lines):
            if line.strip():
                if line.strip().startswith("|"):
                    header_line = line
                    idx_col = index_col_from_header_line(header_line)
                    if j + 1 < len(lines) and str(lines[j + 1]).strip().startswith("|"):
                        delim_line = lines[j + 1]
                        k = j + 2
                        while k < len(lines) and str(lines[k]).strip().startswith("|"):
                            cells = split_row_cells(lines[k])
                            idx_txt = str(cells[idx_col] if idx_col < len(cells) else "").strip()
                            idx_norm = re.sub(r"[^0-9]", "", idx_txt)
                            if not idx_norm:
                                extra_rows.append(lines[k])
                            k += 1
                    break
                break
        if not header_line:
            header_line = "| 序号 | 动作描述 | SOP 操作步骤 | 左手状态 | 右手状态 | 预估耗时(s) | 增值/非增值 | 时间段 |"
            delim_line = "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        return "\n".join(build_table_lines(header_line, delim_line, extra_rows))

    i = 0
    while i < len(lines):
        line = lines[i]
        if re_actions.match(line):
            new_lines.append(line)
            i += 1
            while i < len(lines):
                l = lines[i]
                if l.strip().startswith("|"):
                    header_line = l
                    idx_col = index_col_from_header_line(header_line)
                    delim_line = ""
                    extra_rows: List[str] = []
                    if i + 1 < len(lines) and str(lines[i + 1]).strip().startswith("|"):
                        delim_line = lines[i + 1]
                        i += 2
                    else:
                        delim_line = "| :--- | :--- |"
                        i += 1

                    while i < len(lines) and str(lines[i]).strip().startswith("|"):
                        cells = split_row_cells(lines[i])
                        idx_txt = str(cells[idx_col] if idx_col < len(cells) else "").strip()
                        idx_norm = re.sub(r"[^0-9]", "", idx_txt)
                        if not idx_norm:
                            extra_rows.append(lines[i])
                        i += 1

                    new_lines.extend(build_table_lines(header_line, delim_line, extra_rows))
                    break
                new_lines.append(l)
                i += 1
            continue
        new_lines.append(line)
        i += 1
    return "\n".join(new_lines)
