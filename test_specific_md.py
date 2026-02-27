
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app_results_md import parse_md_content

file_path = "/Users/ph/Documents/trae_projects/gemini 2/result/工位1_0-1_26.14.17.18.md"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    result = parse_md_content(content)
    
    actions_table = result.get('actions_table', {})
    headers = actions_table.get('headers', [])
    rows = actions_table.get('rows', [])
    
    print(f"Header Count: {len(headers)}")
    print(" | ".join(headers))
    print("-" * 50)
    
    for i, row in enumerate(rows):
        print(f"Row {i+1} (Cols: {len(row)}): " + " | ".join(row))
        
except Exception as e:
    print(f"Error: {e}")
