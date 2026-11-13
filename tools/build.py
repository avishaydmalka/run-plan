"""Rebuild index.html from tools/template.html + plan/plan.json.
Run from the repo root:  python3 tools/gen_plan.py  (optional, regenerates the plan)  then  python3 tools/build.py"""
import json, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
tpl = (root / "tools/template.html").read_text(encoding="utf-8")
plan = json.loads((root / "plan/plan.json").read_text(encoding="utf-8"))
data = json.dumps(plan, ensure_ascii=False).replace("</", "<\\/")
(root / "index.html").write_text(tpl.replace("__PLAN__", data), encoding="utf-8")
print("index.html rebuilt")
