"""Build public/index.html and public/coach.html from the templates + plan/plan.json.
Run from the repo root:  python3 tools/gen_plan.py  (optional)  &&  python3 tools/build.py"""
import json, pathlib, datetime
root = pathlib.Path(__file__).resolve().parent.parent
plan = json.loads((root / "plan/plan.json").read_text(encoding="utf-8"))
data = json.dumps(plan, ensure_ascii=False).replace("</", "<\\/")
(root / "public").mkdir(exist_ok=True)
for src, dst in [("tools/template.html", "public/index.html"), ("tools/coach_template.html", "public/coach.html")]:
    build = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2))).strftime("%d.%m %H:%M")
    (root / dst).write_text((root / src).read_text(encoding="utf-8").replace("__PLAN__", data).replace("__BUILD__", build), encoding="utf-8")
    print("built", dst)
