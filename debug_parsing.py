
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from backend.app_results_md import parse_md_content

file_path = "/Users/ph/Documents/trae_projects/gemini 2/result/工位1_0-1_26.14.17.18.md"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

parsed = parse_md_content(content)
headers = parsed.get("actions_table", {}).get("headers", [])
rows = parsed.get("actions_table", {}).get("rows", [])

print(f"Headers count: {len(headers)}")
print(f"Headers: {headers}")
if rows:
    print(f"First row count: {len(rows[0])}")
    print(f"First row: {rows[0]}")
    
    # Check for empty items in the middle
    print("Row items:")
    for idx, item in enumerate(rows[0]):
        print(f"{idx}: '{item}'")
