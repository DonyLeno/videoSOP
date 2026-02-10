import os
import re

def _parse_timestamp_to_seconds(ts_str: str) -> float:
    try:
        parts = ts_str.strip().split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
    except Exception:
        pass
    return 0.0


def _seconds_to_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    # 2FPS means 0.5s precision. Let's use 3 decimal places to be safe and match prompt example.
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _merge_batches_python(result_dir: str) -> str:
    final_lines = []
    global_seq = 1
    
    # Standard columns as per prompt.md
    STANDARD_HEADERS = [
        "序号", "动作描述", "SOP 操作步骤", "左手状态", "右手状态", 
        "预估耗时(s)", "增值/非增值", "时间段"
    ]
    
    # Keywords to identify columns in source files (fuzzy match)
    COL_KEYWORDS = {
        "序号": ["序号", "No", "Seq"],
        "动作描述": ["动作描述", "动作", "Element", "Description"],
        "SOP 操作步骤": ["SOP", "步骤", "Step"],
        "左手状态": ["左手", "Left"],
        "右手状态": ["右手", "Right"],
        "预估耗时(s)": ["耗时", "Time", "Duration"],
        "增值/非增值": ["增值", "VA", "NVA", "Value"],
        "时间段": ["时间段", "Range", "Timestamp"]
    }

    # 1. Scan and Sort Files
    all_files = [f for f in os.listdir(result_dir) if f.endswith(".md") and not f.startswith(".")]
    
    def get_sort_key_and_offset(fname):
        # Try to match "batch_N.md"
        m_batch = re.match(r"batch_(\d+)\.md", fname)
        if m_batch:
            idx = int(m_batch.group(1))
            # Assuming 60 frames per batch.
            # If 2FPS, duration is 30s. If 1FPS, duration is 60s.
            # User said "Reference now each action is sampled at 2FPS".
            # So we default to 30s offset for batch_N files.
            return idx, (idx - 1) * 30.0
            
        # Try to match "start_end.md" e.g. "0.00.jpg_59.00.jpg.md"
        # Extract first float
        m_float = re.match(r"^(\d+(?:\.\d+)?)", fname)
        if m_float:
            val = float(m_float.group(1))
            return val, val
            
        return 999999, 0.0

    # Sort files
    # Store tuples: (filename, offset)
    files_with_offset = []
    for f in all_files:
        key, offset = get_sort_key_and_offset(f)
        files_with_offset.append((f, offset))
    
    # Sort by key (which is effectively the offset or batch index)
    files_with_offset.sort(key=lambda x: get_sort_key_and_offset(x[0])[0])

    print(f"Found {len(files_with_offset)} batch files to merge:")
    for f, off in files_with_offset:
        print(f"  - {f} (offset={off})")

    for i, (fname, offset) in enumerate(files_with_offset):
        batch_path = os.path.join(result_dir, fname)
            
        with open(batch_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # State: 0=Searching Header, 1=Header Found, 2=Separator Found, 3=Rows, 4=Finished
        state = 0
        
        # Accumulator for time within this batch
        # Start at the batch offset (e.g. 0.0, 60.0, etc.)
        current_batch_time = offset

        # Mapping from Standard Index -> Source Index
        col_map = {} 
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            is_pipe = stripped.startswith("|")
            is_sep = "---" in stripped and is_pipe
            
            if state == 0: # Searching for header
                if is_pipe and not is_sep:
                    # Check if it looks like a header (contains "序号" or "动作")
                    if "序号" in line or "动作" in line:
                        state = 1
                        
                        # Parse source headers
                        # Split by pipe and strip whitespace
                        # | col1 | col2 | -> ['', 'col1', 'col2', '']
                        raw_parts = [p.strip() for p in stripped.split("|")]
                        src_headers = []
                        src_indices = []
                        
                        for idx, p in enumerate(raw_parts):
                            if p: # Keep non-empty parts
                                src_headers.append(p)
                                src_indices.append(idx) # Keep track of original index in split array
                        
                        # Build column map
                        col_map = {}
                        used_src_indices = set()
                        
                        for std_idx, std_name in enumerate(STANDARD_HEADERS):
                            keywords = COL_KEYWORDS.get(std_name, [])
                            found_idx = -1
                            
                            # Try to find a matching source column
                            for h_idx, src_name in enumerate(src_headers):
                                real_idx = src_indices[h_idx]
                                if real_idx in used_src_indices:
                                    continue
                                for kw in keywords:
                                    if kw in src_name:
                                        found_idx = real_idx
                                        break
                                if found_idx != -1:
                                    break
                            
                            if found_idx != -1:
                                col_map[std_idx] = found_idx
                                used_src_indices.add(found_idx)
                            else:
                                pass

                        # If this is the first batch, write the STANDARD header
                        if i == 0:
                            header_line = "| " + " | ".join(STANDARD_HEADERS) + " |\n"
                            final_lines.append(header_line)
            
            elif state == 1: # Header found, looking for separator
                if is_sep:
                    state = 2
                    if i == 0:
                        # Write standard separator
                        sep_line = "| " + " | ".join([":---"] * len(STANDARD_HEADERS)) + " |\n"
                        final_lines.append(sep_line)
                elif is_pipe: 
                    # Another header line? 
                    pass
            
            elif state == 2: # Separator found, expect rows
                state = 3
                # Fall through to process this row
            
            if state == 3: # Processing rows
                if is_pipe and not is_sep:
                    parts = [p.strip() for p in stripped.split("|")]
                    
                    # Basic validation: must have enough parts (accounting for empty start/end)
                    if len(parts) < 3: 
                        continue

                    # Reconstruct row based on col_map
                    new_parts = [""] * len(STANDARD_HEADERS)
                    for std_idx in range(len(STANDARD_HEADERS)):
                        src_idx = col_map.get(std_idx)
                        if src_idx is not None and src_idx < len(parts):
                            new_parts[std_idx] = parts[src_idx]
                        else:
                            new_parts[std_idx] = "-" # Default value
                    
                    # Now apply logic (Sequence, Time, SOP) on the STANDARDIZED row
                    
                    # 1. Update Sequence Number (Index 0: 序号)
                    new_parts[0] = str(global_seq)
                    global_seq += 1
                    
                    # 2. Update Time (Index 7: 时间段)
                    # Recalculate based on Duration and Batch Offset
                    time_idx = 7
                    duration_idx = 5
                    
                    try:
                        duration_str = new_parts[duration_idx].strip()
                        # Extract float
                        match_dur = re.search(r"([\d\.]+)", duration_str)
                        if match_dur:
                            duration_val = float(match_dur.group(1))
                        else:
                            # Default to 0.5s (1 frame) if missing/invalid
                            duration_val = 0.5
                    except Exception:
                        duration_val = 0.5

                    # Quantize duration to nearest 2FPS frame (0.5s)
                    # This ensures alignment with video sampling
                    frames = round(duration_val * 2.0)
                    if frames < 1: frames = 1 # Minimum 1 frame
                    duration_val = frames / 2.0
                    
                    start_t = current_batch_time
                    end_t = start_t + duration_val
                    current_batch_time = end_t
                    
                    new_parts[time_idx] = f"{_seconds_to_timestamp(start_t)} - {_seconds_to_timestamp(end_t)}"

                    # 3. Normalize SOP Column (Index 2: SOP 操作步骤)
                    sop_idx = 2
                    sop_content = new_parts[sop_idx]
                    match = re.search(r'(?i)(?:SOP\s*step|中文步骤|SOP|步骤|step)\s*(\d+)', sop_content)
                    if match:
                        new_parts[sop_idx] = f"SOP {match.group(1)}"
                            
                    # Construct line
                    final_lines.append("| " + " | ".join(new_parts) + " |\n")
                    
                else:
                    # Not a pipe line, likely end of table or remarks
                    state = 4
            
            elif state == 4: # Finished table, ignore rest
                continue

    return "".join(final_lines)

# Configuration
result_dir = "/Users/ph/Documents/trae_projects/gemini 2/result/position1_15-20_09.23.40.00"
output_path = "/Users/ph/Documents/trae_projects/gemini 2/result/position1_15-20_09.23.40.00.md"

try:
    merged_content = _merge_batches_python(result_dir)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(merged_content)
        
    print(f"Merge successful. Written to {output_path}")
    print("\n--- Merged Content Preview ---")
    lines = merged_content.splitlines()
    # Print header and first few rows
    print("\n".join(lines[:10]))
    print("...")

except Exception as e:
    print(f"Merge failed: {e}")
