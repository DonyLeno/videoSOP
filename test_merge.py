import os
import re
import glob

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def extract_section(content, section_header):
    """
    Extracts content of a section starting with `section_header` 
    until the next section (starting with ##) or end of file.
    """
    pattern = re.escape(section_header) + r"(.*?)(?=\n##|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

def clean_section_content(content):
    """
    Removes leading/trailing whitespace and `---` separators.
    """
    content = content.strip()
    # Remove trailing --- if present
    if content.endswith("---"):
        content = content[:-3].strip()
    # Remove leading --- if present
    if content.startswith("---"):
        content = content[3:].strip()
    return content

def parse_table(table_text):
    """
    Parses a markdown table into (headers, separator, rows).
    """
    lines = table_text.strip().split('\n')
    lines = [line.strip() for line in lines if line.strip()]
    if not lines:
        return None, None, []
    
    table_lines = [line for line in lines if line.startswith('|')]
    
    if len(table_lines) < 2:
        return None, None, []
    
    header = table_lines[0]
    separator = table_lines[1]
    rows = table_lines[2:]
    return header, separator, rows

def parse_deep_dive_section(content):
    """
    Parses the Deep Dive Findings section into categories.
    """
    findings = {
        "Stability": [],
        "Ergonomics": [],
        "Cognitive Load": [],
        "Material/Environment": []
    }
    
    # Split content by lines starting with * **
    # Pattern: ^\* \*\*(.*?)\:\*\*(.*?)(?=(?:^\*\s+\*\*)|$)
    # Note: Using re.MULTILINE to match start of lines
    
    matches = re.finditer(r"(?m)^\*\s+\*\*(.*?)\:\*\*(.*?)(?=(?:^\*\s+\*\*)|$)", content, re.DOTALL)
    
    for match in matches:
        header = match.group(1).strip() # e.g. "稳定性 (Stability)"
        body = match.group(2).strip()
        
        # Determine category
        if "Stability" in header or "稳定性" in header:
            findings["Stability"].append(body)
        elif "Ergonomics" in header or "人机工程" in header:
            findings["Ergonomics"].append(body)
        elif "Cognitive" in header or "认知" in header:
            findings["Cognitive Load"].append(body)
        elif "Material" in header or "Environment" in header or "物料" in header or "环境" in header:
            findings["Material/Environment"].append(body)
            
    return findings

def main():
    batch_dir = "result/full"
    # Get all batch files
    batch_files = glob.glob(os.path.join(batch_dir, "batch_*.md"))
    batch_files.sort(key=natural_sort_key)
    
    print(f"Found {len(batch_files)} batch files.")
    
    if not batch_files:
        print("No batch files found.")
        return

    # Containers for merged content
    merged_overview_text = ""
    all_cts = []
    all_uphs = []
    merged_rows = []
    
    # Structure for Deep Dive Findings
    merged_findings = {
        "Stability": [],
        "Ergonomics": [],
        "Cognitive Load": [],
        "Material/Environment": []
    }
    
    merged_kaizen = []
    
    table_header = None
    table_separator = None
    
    current_row_index = 1
    kaizen_issue_index = [1]
    
    # Base structure (title etc from first file)
    with open(batch_files[0], 'r', encoding='utf-8') as f:
        first_content = f.read()
    
    # Extract title (everything before first ##)
    title_match = re.search(r"^(.*?)(?=\n## )", first_content, re.DOTALL)
    title_section = title_match.group(1).strip() if title_match else "# AutoIE Analysis Result"

    for batch_file in batch_files:
        print(f"Processing {batch_file}...")
        with open(batch_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 1. 工序概览
        overview = extract_section(content, "## 1. 工序概览")
        if overview:
            merged_overview.append(clean_section_content(overview))
            
        # 2. 详细动作分析表
        motion = extract_section(content, "## 2. 详细动作分析表 (Motion Breakdown)")
        if motion:
            motion = clean_section_content(motion)
            # Find table lines
            header, separator, rows = parse_table(motion)
            if header and separator:
                if table_header is None:
                    table_header = header
                    table_separator = separator
                
                print(f"  Found {len(rows)} rows in {batch_file}")
                for row in rows:
                    # Re-index
                    row = re.sub(r"^\|\s*\d+\s*\|", f"| {current_row_index} |", row)
                    merged_rows.append(row)
                    current_row_index += 1
        
        # 3. 深度诊断发现
        findings_text = extract_section(content, "## 3. 深度诊断发现 (Deep Dive Findings)")
        if findings_text:
            findings_text = clean_section_content(findings_text)
            parsed_findings = parse_deep_dive_section(findings_text)
            for cat, items in parsed_findings.items():
                merged_findings[cat].extend(items)
            
        # 4. 改善机会
        kaizen = extract_section(content, "## 4. 改善机会 (Kaizen Opportunities)")
        if kaizen:
            kaizen_text = clean_section_content(kaizen)
            def _repl_kaizen(m):
                nonlocal kaizen_issue_index
                res = f"* **问题点 {kaizen_issue_index}:"
                kaizen_issue_index += 1
                return res
            kaizen_text = re.sub(r"\* \*\*问题点 \d+:", _repl_kaizen, kaizen_text)
            merged_kaizen.append(kaizen_text)

    # Construct final MD
    final_md_parts = []
    
    final_md_parts.append(title_section)
    final_md_parts.append("\n\n---\n\n")
    
    # Calculate averages for Overview
    if merged_overview_text:
        if all_cts:
            avg_ct = sum(all_cts) / len(all_cts)
            merged_overview_text = re.sub(r"(\* \*\*预估节拍 \(CT\):\*\*).*", f"\\1 约 {avg_ct:.2f} 秒", merged_overview_text)
        if all_uphs:
            avg_uph = sum(all_uphs) / len(all_uphs)
            merged_overview_text = re.sub(r"(\* \*\*理论产能 \(UPH\):\*\*).*", f"\\1 约 {int(avg_uph)} pcs/h (基于多Batch平均值)", merged_overview_text)

    final_md_parts.append("## 1. 工序概览\n")
    final_md_parts.append(merged_overview_text)
    final_md_parts.append("\n\n---\n\n")
    
    final_md_parts.append("## 2. 详细动作分析表 (Motion Breakdown)\n")
    if table_header and table_separator:
        final_md_parts.append(table_header)
        final_md_parts.append(table_separator)
        final_md_parts.append("\n".join(merged_rows))
    else:
        final_md_parts.append("(No table data found)")
    final_md_parts.append("\n\n---\n\n")
    
    final_md_parts.append("## 3. 深度诊断发现 (Deep Dive Findings)\n")
    
    # Output categorized findings
    # 稳定性 (Stability)
    if merged_findings["Stability"]:
        final_md_parts.append("* **稳定性 (Stability):**")
        for item in merged_findings["Stability"]:
            final_md_parts.append(f"  {item}") # Indent sub-bullets
        final_md_parts.append("") # Empty line

    # 人机工程 (Ergonomics)
    if merged_findings["Ergonomics"]:
        final_md_parts.append("* **人机工程 (Ergonomics):**")
        for item in merged_findings["Ergonomics"]:
            final_md_parts.append(f"  {item}")
        final_md_parts.append("")

    # 认知负荷 (Cognitive Load)
    if merged_findings["Cognitive Load"]:
        final_md_parts.append("* **认知负荷 (Cognitive Load):**")
        for item in merged_findings["Cognitive Load"]:
            final_md_parts.append(f"  {item}")
        final_md_parts.append("")

    # 物料/环境 (Material/Environment)
    if merged_findings["Material/Environment"]:
        final_md_parts.append("* **物料/环境 (Material/Environment):**")
        for item in merged_findings["Material/Environment"]:
            final_md_parts.append(f"  {item}")
        final_md_parts.append("")

    final_md_parts.append("\n\n---\n\n")
    
    final_md_parts.append("## 4. 改善机会 (Kaizen Opportunities)\n")
    final_md_parts.append("\n".join(merged_kaizen))
    
    final_content = "\n".join(final_md_parts)
    
    output_filename = "result/full_manual_merge.md"
    
    print(f"Total merged rows: {len(merged_rows)}")
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(final_content)
        
    print(f"Successfully merged {len(batch_files)} files into {output_filename}")

if __name__ == "__main__":
    main()
