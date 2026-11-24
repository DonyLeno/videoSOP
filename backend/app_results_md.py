import re
from typing import Dict, List, Optional


def _parse_time_str(t_str: str) -> float:
    t_str = str(t_str).strip()
    # 去掉 Markdown 反引号/引号/括号等包裹字符（如 `0:00`、"0:00"），只保留时间本体
    t_str = re.sub(r"^[^\d]+", "", t_str)
    t_str = re.sub(r"[^\d:.]+$", "", t_str)
    try:
        return float(t_str)
    except ValueError:
        pass
    parts = t_str.split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        # 动作时间段统一按 分:秒 解析（6:05 = 365s）。
        # 旧逻辑对 a>2 走 "a + b/100" 小数兜底，会把 6:05 变成 6.05 秒，导致长视频时间轴被压缩。
        a_raw, b_raw = parts[0].strip(), parts[1].strip()
        return float(a_raw) * 60 + float(b_raw)
    raise ValueError(f"Invalid time format: {t_str}")


_RE_HMS = re.compile(r"(?<!\d)(\d{1,2}):([0-5]\d):([0-5]\d)(?!\d)")
# “墙钟时间”线索：出现这些字样说明时间是画面烧录的真实时刻，而非相对视频起点
_RE_WALLCLOCK_HINT = re.compile(r"(时间戳|墙钟|画面右下角|画面右上角|视频起点|视频开始时间|\d{4}\s*[年/-]\s*\d{1,2}\s*[月/-]\s*\d{1,2})")
_RE_DECLARED_START = (
    # “时间戳 13:38:55 至 13:41:51” / “视频时间：13:38:55”
    re.compile(r"(?:时间戳|时间范围|视频时间|起始时间|开始时间|起点)[^\d\n]{0,12}(\d{1,2}):([0-5]\d):([0-5]\d)"),
    # “13:38:55 至 13:41:51” 这种成对区间
    re.compile(r"(?<!\d)(\d{1,2}):([0-5]\d):([0-5]\d)\s*(?:至|到|–|—|-|~|～)\s*\d{1,2}:[0-5]\d:[0-5]\d"),
)


def _hms_to_seconds(h: str, m: str, s: str) -> float:
    return float(h) * 3600 + float(m) * 60 + float(s)


def _declared_video_start(content: str) -> float:
    """从正文中提取“视频起点墙钟”，找不到返回 -1。"""
    text = str(content or "")
    for pattern in _RE_DECLARED_START:
        m = pattern.search(text)
        if m:
            try:
                return _hms_to_seconds(m.group(1), m.group(2), m.group(3))
            except Exception:
                continue
    return -1.0


def _min_doc_timestamp(content: str) -> float:
    """全文出现的最早 HH:MM:SS，找不到返回 -1。"""
    values = []
    for m in _RE_HMS.finditer(str(content or "")):
        try:
            values.append(_hms_to_seconds(m.group(1), m.group(2), m.group(3)))
        except Exception:
            continue
    return min(values) if values else -1.0


def normalize_wallclock_actions(content: str, actions: List[Dict[str, object]]) -> Dict[str, object]:
    """把“墙钟绝对时间”的时间段归一化为“相对视频起点”的秒数（原地修改）。

    模型有时把画面右下角烧录的墙钟时间（如 13:40:18）直接写进时间段，按 HH:MM:SS
    解析后会变成 49218 秒，远超视频时长，导致时间轴量程与播放头全部越界。
    这里以正文声明的视频起点（兜底：全文最早时间戳 / 首个动作起点）为基准做平移。
    """
    info: Dict[str, object] = {"applied": False, "offset": 0.0, "basis": ""}
    valid: List[Dict[str, object]] = []
    for act in actions or []:
        try:
            s = float(act.get("start_time") or 0)
            e = float(act.get("end_time") or 0)
        except (TypeError, ValueError):
            continue
        if e > s:
            valid.append(act)
    if not valid:
        return info

    min_start = min(float(a["start_time"]) for a in valid)
    # 起点都不到 1 小时，说明本来就是相对时间，无需处理
    if min_start < 3600:
        return info

    candidates = []
    declared = _declared_video_start(content)
    if declared >= 0:
        candidates.append((declared, "declared_start"))
    doc_min = _min_doc_timestamp(content)
    if doc_min >= 0:
        candidates.append((doc_min, "doc_min"))
    # 基准必须早于首个动作，且相差不超过 1 小时（超过则判定为无关时间戳，弃用）
    accepted = [c for c in candidates if 0 < c[0] <= min_start and (min_start - c[0]) <= 3600]
    if accepted:
        offset, basis = min(accepted, key=lambda c: c[0])
    else:
        # 无可靠基准时，仅在文档确有“墙钟时间”线索时才兜底平移，
        # 避免把超过 1 小时的超长视频（相对时间本就 >3600s）误判成墙钟。
        if not _RE_WALLCLOCK_HINT.search(str(content or "")):
            return info
        offset, basis = min_start, "first_action"

    if offset <= 0:
        return info

    for act in valid:
        act["start_time"] = max(0.0, float(act["start_time"]) - offset)
        act["end_time"] = max(0.0, float(act["end_time"]) - offset)

    info.update({"applied": True, "offset": float(offset), "basis": basis})
    return info


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
    # 建议条目与子项被粘连成一行，如 “***问题点1: …*****关联动作编号:** …”
    text = re.sub(
        r"(?<!\n)\*{2,}\s*(问题点|建议点|改善点|关联动作|改善对策|预期收益|实施难度|验证方法|优先级|推荐)",
        r"\n* \1",
        text,
    )
    # 行首多余星号，如 “***问题点2: …”
    text = re.sub(r"(?m)^\*{2,}(?=\S)", "* ", text)
    # 只剩列表符号的空行（模型把 “*   **问题点” 拆开后残留）
    text = re.sub(r"(?m)^[ \t]*[*•+][ \t]*$\n?", "", text)
    return text


_ADVICE_SECTION_RE = re.compile(
    r"(改善建议|改进建议|优化建议|建议|对策|Kaizen|Recommendation|Improvement|Opportunit)",
    re.IGNORECASE,
)
_ADVICE_WEAK_RE = re.compile(r"(改善|改进|优化|提升)", re.IGNORECASE)
# 报告标题、概览/诊断/浪费识别等章节虽含「改善」字样，但不是建议正文，需排除
_ADVICE_TITLE_EXCLUDE_RE = re.compile(
    r"(报告|分析|概览|Overview|诊断|识别|动作|Motion|Therblig|浪费|Muda)",
    re.IGNORECASE,
)
_ADVICE_EXCLUDE_RE = re.compile(
    r"(限制|补拍|备注|置信度|证据|Notes|Limitations|Confidence|Evidence)", re.IGNORECASE
)
_ADVICE_ITEM_RE = re.compile(
    r"^(问题点|建议点|改善点|改善建议|改善措施|优化措施|对策|问题\s*\d|建议\s*\d|改善\s*\d|\d+[).、]\s*\S)",
    re.IGNORECASE,
)


def _strip_md_marks(text: str) -> str:
    cleaned = re.sub(r"\*\*|__|`", "", str(text or "")).strip()
    return re.sub(r"^[\s*]+|[\s*]+$", "", cleaned)


def extract_advice_items(content: str) -> List[str]:
    """模糊提取「改进建议」条目，不依赖模型输出的具体标题层级或符号。

    策略：
    1. 按标题切块，找出标题含 改善/建议/优化/Kaizen 等关键词的章节；
    2. 章节内以子标题或顶层 bullet 作为条目边界，子项并入当前条目；
    3. 若整篇找不到该类章节，退化为扫描含「建议/改善/优化/对策」的 bullet。
    """
    text = normalize_md_content(content)
    lines = text.splitlines()
    headings: List[tuple] = []
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s*(\S.*)$", line)
        if m:
            headings.append((i, len(m.group(1)), m.group(2).strip()))
    if not headings:
        return []

    blocks: List[tuple] = []
    for pos, (idx, level, title) in enumerate(headings):
        end = len(lines)
        for idx2, level2, _title2 in headings[pos + 1 :]:
            if level2 <= level:
                end = idx2
                break
        blocks.append((level, title, idx, end))

    def collect(base_level: int, start: int, end: int) -> List[str]:
        items: List[str] = []
        title: Optional[str] = None
        body: List[str] = []

        def flush() -> None:
            nonlocal title, body
            if title is None and not body:
                return
            if title and _ADVICE_EXCLUDE_RE.search(title):
                title, body = None, []
                return
            head = _strip_md_marks(title) if title else ""
            content_text = "\n".join(body).strip()
            merged = f"**{head}**\n{content_text}".strip() if head else content_text
            merged = merged.strip()
            # 跳过章节引导语，如「基于 ECRS 原则提出以下建议：」
            if title is None and _strip_md_marks(merged).rstrip().endswith(("：", ":")):
                title, body = None, []
                return
            if len(_strip_md_marks(merged)) >= 8:
                items.append(merged)
            title, body = None, []

        for line in lines[start:end]:
            trimmed = line.strip()
            if not trimmed:
                if body:
                    body.append("")
                continue
            heading = re.match(r"^(#{1,6})\s*(.*)$", trimmed)
            if heading and len(heading.group(1)) > base_level:
                flush()
                title = heading.group(2).strip()
                continue
            bullet = re.match(r"^[-*•+]\s+(.*)$", trimmed)
            if bullet:
                bullet_text = bullet.group(1).strip()
                if _ADVICE_ITEM_RE.search(_strip_md_marks(bullet_text)):
                    flush()
                    title = bullet_text
                elif title is None and not body and len(_strip_md_marks(bullet_text)) >= 8:
                    title = bullet_text
                else:
                    body.append(bullet_text)
                continue
            body.append(trimmed)
        flush()
        return items

    result: List[str] = []
    seen = set()
    # 只把二级及以下的标题当作建议章节（一级标题通常是整篇报告名，会把全文误当成一个章节）；
    # 同时优先「改善建议/建议/对策」类强关键词，避免选中「改善方向」这类概述章节
    candidates: List[tuple] = []
    for base_level, title, start, end in blocks:
        if base_level < 2 or end - start < 2:
            continue
        title_clean = _strip_md_marks(title)
        if _ADVICE_EXCLUDE_RE.search(title_clean) or _ADVICE_TITLE_EXCLUDE_RE.search(title_clean):
            continue
        strong = bool(_ADVICE_SECTION_RE.search(title_clean))
        weak = bool(_ADVICE_WEAK_RE.search(title_clean))
        if not (strong or weak):
            continue
        collected = collect(base_level, start + 1, end)
        if not collected:
            continue
        candidates.append((0 if strong else 1, -len(collected), collected))

    if candidates:
        candidates.sort(key=lambda x: (x[0], x[1]))
        for item in candidates[0][2]:
            key = _strip_md_marks(item)[:40]
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
    if result:
        return result[:20]

    # 兜底：全篇扫描含建议类关键词的 bullet
    for line in lines:
        m = re.match(r"^\s*[-*•+]\s+(.*)$", line)
        if not m:
            continue
        item = _strip_md_marks(m.group(1))
        if len(item) < 8:
            continue
        if not re.search(r"(改善对策|改善建议|建议|推荐|优化措施|对策|实施)", item):
            continue
        if item[:40] in seen:
            continue
        seen.add(item[:40])
        result.append(f"**{item}**")
        if len(result) >= 20:
            break
    return result


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
    re_sub_point = re.compile(r"^#{3,6}\s*(问题点|建议点|改善点)")
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
        # 「问题点」等子标题归属当前章节（改善机会/深度诊断），必须先于
        # 「浪费」「动素」等关键词正则判断，否则含「浪费」的问题点会被误切走
        if re_sub_point.match(line):
            if current_section in ("kaizen", "deep_dive"):
                sections[current_section] = str(sections.get(current_section) or "") + line + "\n"
                continue
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
            # 未归类的子标题（###~######）跟随当前章节，避免「问题点」「1) 稳定性」
            # 等子标题把内容切回工序概览；未归类的一级/二级标题仍归入概览兜底
            if current_section in ("kaizen", "deep_dive") and re.match(r"^#{3,6}\s", line):
                sections[current_section] = str(sections.get(current_section) or "") + line + "\n"
                continue
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
    sections["time_normalization"] = normalize_wallclock_actions(
        normalize_md_content(content), actions
    )
    preface = "\n".join(preface_lines).strip()
    overview = str(sections.get("overview") or "").strip()
    if preface:
        sections["overview"] = (preface + "\n\n" + overview).strip() if overview else preface
    else:
        sections["overview"] = overview
    sections["deep_dive"] = str(sections.get("deep_dive") or "").strip()
    sections["kaizen"] = str(sections.get("kaizen") or "").strip()
    # 改进建议：对整篇 Markdown 做模糊提取，不依赖具体章节名与标记格式
    sections["advice"] = extract_advice_items(content)
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
