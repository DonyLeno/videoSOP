#!/usr/bin/env python3
"""阶段 4.2 批次 H：把 web/assets/app.js 机械切分为 ES modules。

切分策略（详见 docs/架构审查与改进计划.md 4.2）：
- 按函数/声明边界切为 i18n/core/format/users/scope/org/detection/review/settings/main 十个模块
- switchTab 归 core（避免 main<->detection/review 循环 import）；fetchVersion 归 main
- getBaseName 从 users 挪到 format（通用工具）
- 所有顶层声明加 export；import 由跨模块标识符 token 扫描自动生成
- main.js 挂 window 桥接（HTML 内联事件需要：switchTab/loadResultList/exportActionsCsv/showRevisionHistory）
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "web", "assets", "app.js")
OUT_DIR = os.path.join(ROOT, "web", "assets", "js")

with open(SRC, encoding="utf-8") as f:
    lines = f.read().split("\n")

N = len(lines)


def seg(start, end):
    """1-based 闭区间 -> 行列表"""
    return lines[start - 1 : end]


# 段定义（1-based 闭区间）：
# i18n 1-641 | core 643-997 + switchTab 1013-1030 | format 1032-1110 + getBaseName 1180-1185
# users 1112-1178 + 1186-1436 | scope 1437-1576 | org 1577-2003 | detection 2004-2648
# review 2649-5288 | settings 5289-5338 | main = fetchVersion 999-1011 + 5339-END
modules = {
    "i18n": seg(1, 641),
    "core": seg(643, 997) + seg(1013, 1030),
    "format": seg(1032, 1110) + seg(1180, 1185),
    "users": seg(1112, 1179) + seg(1186, 1436),
    "scope": seg(1437, 1576),
    "org": seg(1577, 2003),
    "detection": seg(2004, 2648),
    "review": seg(2649, 5288),
    "settings": seg(5289, 5338),
    "main": seg(999, 1011) + seg(5339, N),
}

DECL_RE = re.compile(r"^(async function |function |let |const |class )")


def add_export(mod_lines):
    out = []
    for line in mod_lines:
        if DECL_RE.match(line):
            out.append("export " + line)
        else:
            out.append(line)
    return out


# 1) 收集每个模块的导出名
exported = {}
for name, ml in modules.items():
    names = set()
    for line in ml:
        m = DECL_RE.match(line)
        if m:
            rest = line[len(m.group(1)) :]
            ident = re.match(r"[A-Za-z_$][A-Za-z0-9_$]*", rest)
            if ident:
                names.add(ident.group(0))
    exported[name] = names

# 2) token 扫描生成 import
TOKEN_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
os.makedirs(OUT_DIR, exist_ok=True)

report = []
for name, ml in modules.items():
    body = add_export(ml)
    # main.js 不需要 export（入口）；保留 export 也无害，但保持入口干净
    if name == "main":
        body = ml  # 不加 export
    text = "\n".join(body)
    tokens = set(TOKEN_RE.findall(text))
    imports = []
    for dep, dep_names in exported.items():
        if dep == name:
            continue
        used = sorted(tokens & dep_names)
        if used:
            imports.append(f"import {{ {', '.join(used)} }} from './{dep}.js';")
    header = "\n".join(imports)
    if name == "main":
        # window 桥接：HTML 内联事件（partials）引用的全局函数
        bridge = (
            "\n// HTML 内联事件桥接：模块作用域函数挂到 window（partials 页面内联 onclick/onchange 需要）\n"
            "Object.assign(window, {\n"
            "  switchTab,\n"
            "  loadResultList,\n"
            "  exportActionsCsv,\n"
            "  showRevisionHistory,\n"
            "});\n"
        )
        text = header + "\n\n" + text + "\n" + bridge
    else:
        text = header + "\n\n" + text
    out_path = os.path.join(OUT_DIR, f"{name}.js")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    report.append((name, len(ml), imports))

for name, nlines, imports in report:
    print(f"{name:10s} {nlines:5d} lines, {len(imports)} imports:")
    for imp in imports:
        print(f"    {imp}")

# 3) 顶层非声明行审查（检测意外的模块级立即执行代码）
print("\n--- 顶层非声明/非空/非注释行（应为空或安全字面量）---")
for name, ml in modules.items():
    for i, line in enumerate(ml):
        if not line.strip() or line.strip().startswith("//") or line.strip().startswith("*"):
            continue
        if DECL_RE.match(line):
            continue
        # 顶层即第 0 列开始的行
        if not line[0].isspace():
            print(f"  [{name}] L{i+1}: {line[:80]}")
