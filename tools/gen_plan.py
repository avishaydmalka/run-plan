import json, csv, datetime as dt

START = dt.date(2026, 11, 15)  # Sunday
RACE = dt.date(2027, 2, 26)

DEF = """מהיר= תחושת מאמץ סח"ח (דופק ~{{hr:lt}}). הגבול הדק בין מתחיל להיות קשה לנשום לקשה לנשום
בינוני= מתחיל להיות לא נעים לדבר
קל= ללא שום קושי נשימתי. קצב התאוששות קליל"""

EASY = "ריצה בקצב נוח שניתן לדבר בו חופשי ללא שום קושי נשימתי. ניתן לבצע קל ככל שצריך. אין משמעות לקצב באימון מסוג זה. דופק {{hr:easy}}"

def hills(n, length, warm, cool, pace="5:08"):
    pace = "{{p:%s}}" % pace
    return (f'חימום: {warm} ק"מ ריצה קלילה. לקראת הסוף 3 מתגברות עדינות של 10 שניות.\n'
            f'עיקרי: {n} עליות של {length} מטר בשיפוע 5%. עלייה בתחושת מאמץ סח"ח (דופק ~{{hr:lt}}). הגבול הדק בין מתחיל להיות קשה לנשום, לקשה לנשום. קרוב לקצב תחרות 10 ק"מ עדכני ~ {pace} דק\'/ק"מ.\n'
            f'ירידה ריצה קלילה כמו הליכה ויציאה ישר לעליה הבאה.\n'
            f'שחרור: {cool} ק"מ קליל')

def fartlek(warm, sets, last, total_note, variant="A"):
    if variant == "A":
        reps = "0:30 מהיר, 1:30 קל\n0:45 מהיר, 1:15 קל\n1:00 מהיר, 1:00 קל\n1:15 מהיר, 0:45 קל\n1:30 מהיר, 0:30 קל"
    else:
        reps = "0:45 מהיר, 1:15 קל\n1:00 מהיר, 1:00 קל\n1:15 מהיר, 0:45 קל\n1:30 מהיר, 0:30 קל\n1:45 מהיר, 0:15 קל"
    s = (f"חימום: {warm} דקות ריצה קלה, 4 דקות הגברה מדורגת כל דקה מהירה במקצת מהקודמת ועד לקצב בינוני.\n\n"
         f"עיקרי: {sets}*\n{reps}\n")
    if last:
        s += f"לאחר הסט האחרון ריצה אחת בת {last} מהירה ואז\n"
    s += f"שחרור: כ-{warm} דקות ריצה קלילה\n\n{DEF}\n\n{total_note}"
    return s

PROG13 = """ריצה רצופה ומתגברת של 13 ק"מ:
4 ק"מ קצב קליל Z1 (דופק {{hr:easy}}), אין שום קושי נשימתי
4 ק"מ בקצב נוח-בינוני. טווח דופק {{hr:z23}}
2.5 ק"מ על הסח"ח (דופק ~{{hr:lt}}) ~ קצב {{p:5:08}} דק'/ק"מ.
2 ק"מ קל ב-Z1"""

LADDER = """4 ק"מ על קצב קל
1 ק"מ על קצב {{p:5:20}} דק'/ק"מ
1 ק"מ על קצב {{p:5:12}} דק'/ק"מ
1 ק"מ על קצב {{p:5:05}} דק'/ק"מ
1 ק"מ על קצב {{p:5:00}} דק'/ק"מ
1 ק"מ על קצב {{p:4:55}} דק'/ק"מ
1 ק"מ על קצב קל"""

TEST10 = """חימום 2 ק"מ קל, חימום ספציפי קצר, 3 מתגברות של 10 שניות
עיקרי: 10 ק"מ הכי מהר שרק ניתן. הנתון החשוב ביותר הוא דופק ממוצע ל-10 ק"מ האלו (דופק סח"ח מעודכן).
מבחינת קצב נסה לכוון ל-{{p:5:08}} דק'/ק"מ
שחרור: 2 ק"מ קל
👈 אחרי הטסט: עדכן את התוצאה והדופק הממוצע בהגדרות — כל הקצבים והדפקים יתעדכנו אוטומטית."""

def intervals(n, warm=4, cool=4, pace="5:00"):
    pace = "{{p:%s}}" % pace
    return (f'חימום: {warm} ק"מ ריצה קלילה, 3 מתגברות עדינות של 10 שניות.\n'
            f'עיקרי: {n}*1000 על קצב ~{pace} דק\'/ק"מ. בין לבין 400 מטר קליל כמו קצב הליכה, שייקח לפחות 3 דקות.\n'
            f'שחרור: {cool} ק"מ קליל\n\nנא לבצע את האימון במקום שטוח: אצטדיון / פארק הירקון')

def tempo(km, warm=3, cool=2):
    return (f'חימום: {warm} ק"מ ריצה קלה, 1 ק"מ הגברה מדורגת כל 200 מטר.\n\n'
            f'עיקרי: {km} ק"מ בקצב מטרה לחצי מרתון ~{{p:5:38}}-{{p:5:40}} דק\'/ק"מ\n\n'
            f'שחרור: {cool} ק"מ ריצה קלילה')

COMB = "איכות משולב — תלוי אימון (6-7 ק\"מ)"

# day index: 0=Sun .. 6=Sat
W = []
def week(phase, wk_in_phase, cycle, sessions, note=""):
    W.append(dict(phase=phase, wk=wk_in_phase, cycle=cycle, sessions=sessions, note=note))

def S(day, typ, km, desc, extra=""):
    return dict(day=day, type=typ, km=km, desc=desc, extra=extra)

comb = lambda: S(1, "איכות משולב", "6-7", COMB)

week("בסיס 1", 1, "3 - מופחת (2:1)", [
    S(0, "עליות", 8.5, hills(6, 250, 3, 2.5)), comb(),
    S(5, "LSD", 13, EASY)], "שבוע כניסה")
week("בסיס 1", 2, "1 (2:1)", [
    S(0, "עליות", 9, hills(7, 250, 3, 2.5)), comb(),
    S(3, "פרטלק", 12, fartlek(15, 3, "2:00", 'סה"כ אימון של כ-72 דקות. השלמת שחרור עד 12 ק"מ'), 'סה"כ ~16 דקות מצטבר על הסח"ח'),
    S(5, "LSD", 15, EASY)])
week("בסיס 1", 3, "2 (2:1)", [
    S(0, "עליות", 9.5, hills(8, 250, 3, 2.5)), comb(),
    S(3, "פרטלק", 10, fartlek(10, 3, "2:00", 'השלמת שחרור עד 10 ק"מ'), 'סה"כ ~16 דקות מצטבר על הסח"ח'),
    S(5, "LSD", 16, EASY)])
week("בסיס 2", 1, "3 - מופחת (2:1)", [
    S(0, "LSD", 12, EASY), comb(),
    S(3, "Z1", 6, EASY + '\nבסוף: 3 מתגברות עדינות של 10 שניות. שומרים רגליים רעננות לטסט.'),
    S(5, "טסט 10 ק\"מ", 14, TEST10)], "שבוע טסט 10 ק\"מ — עדכון קצבים")
week("בסיס 2", 2, "1 (2:1)", [
    S(0, "עליות", 12, hills(6, 400, 4.2, 5.4)), comb(),
    S(3, "פרטלק", 13, fartlek(20, 3, "", 'סה"כ אימון של כ-70 דקות. השלמת שחרור עד 13 ק"מ', "B"), 'סה"כ ~18 דקות מצטבר על הסח"ח'),
    S(5, "LSD", 18, EASY)])
week("בסיס 2", 3, "2 (2:1)", [
    S(0, "עליות", 12.5, hills(7, 400, 4.3, 5.4)), comb(),
    S(3, "ריצה מתגברת", 10, LADDER, 'סה"כ ~19 דקות מצטבר על הסח"ח'),
    S(4, "Z1", 5, EASY),
    S(5, "LSD", 19, EASY)])
week("בנייה 1", 1, "3 - מופחת (2:1)", [
    S(0, "עליות", 10, hills(5, 400, 4, 3.5)), comb(),
    S(3, "פרטלק", 10, fartlek(10, 3, "2:00", 'השלמת שחרור עד 10 ק"מ')),
    S(5, "LSD", 15, EASY)])
week("בנייה 1", 2, "1 (2:1)", [
    S(0, "עליות", 13, hills(8, 400, 4.4, 5.4)), comb(),
    S(2, "Z1", 5, EASY),
    S(3, "פרטלק", 12, fartlek(15, 4, "1:00", 'סה"כ אימון של כ-72 דקות. השלמת שחרור עד 12 ק"מ'), 'סה"כ ~21 דקות מצטבר על הסח"ח'),
    S(5, "LSD", 20, EASY)])
week("בנייה 1", 3, "2 (2:1)", [
    S(0, "אינטרוולים", 13, intervals(5)), comb(),
    S(3, "ריצה מתגברת", 13.5, PROG13, 'סה"כ ~14 דקות מצטבר על הסח"ח'),
    S(4, "Z1", 5, EASY),
    S(5, "LSD", 21, EASY)])
week("בנייה 2", 1, "3 - מופחת (2:1)", [
    S(0, "עליות", 12, hills(6, 400, 4.2, 5.4)), comb(),
    S(3, "טמפו", 13, tempo(8)),
    S(5, "LSD", 16, EASY)])
week("בנייה 2", 2, "1 (2:1)", [
    S(0, "אינטרוולים", 14, intervals(6, 4, 4)), comb(),
    S(2, "Z1", 6, EASY),
    S(3, "טמפו", 15, tempo(10, 3, 1)),
    S(5, "LSD", 22, EASY)])
week("בנייה 2", 3, "2 (2:1)", [
    S(0, "אינטרוולים", 13, intervals(5)), comb(),
    S(3, "טמפו", 16, tempo(11)),
    S(4, "Z1", 8, EASY),
    S(5, "LSD", 24, EASY)], "שבוע העומס הגבוה בתוכנית")
week("שיא", 1, "3 - מופחת (2:1)", [
    S(0, "עליות", 10, hills(5, 400, 4, 3.5)), comb(),
    S(3, "פרטלק", 10, fartlek(10, 3, "2:00", 'השלמת שחרור עד 10 ק"מ')),
    S(5, "LSD", 16, EASY)])
week("חידוד", 1, "טייפר", [
    S(0, "אינטרוולים", 11, intervals(4, 3.5, 3.5)), comb(),
    S(3, "טמפו", 11, tempo(6)),
    S(5, "LSD", 12, EASY)], "הורדת נפח, שמירה על חדות")
week("תחרות", 1, "תחרות", [
    S(0, "Z1 + קצב מטרה", 8, 'ריצה קלה 8 ק"מ, בתוכה 3*1 ק"מ בקצב מטרה {{p:5:38}}-{{p:5:40}} דק\'/ק"מ עם 2 דקות קל ביניהם.'),
    S(1, "איכות משולב", "5", "איכות משולב קליל — רק אם מרגישים רעננים. לא להעמיס."),
    S(3, "Z1", 5, EASY + '\nבסוף: 3 מתגברות עדינות של 10 שניות.'),
    S(5, "🏁 חצי מרתון", 21.1, 'מרתון תל אביב — חצי מרתון.\nפתיחה שמרנית ב-2-3 ק"מ הראשונים, ואז קצב מטרה ~{{p:5:38}}-{{p:5:40}} דק\'/ק"מ. מים בכל תחנה.\nבהצלחה! 🎉')],
    "שבוע המרוץ")

DAYS = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]

def kmnum(k):
    if isinstance(k, str):
        a = [float(x) for x in k.split("-")]
        return sum(a) / len(a)
    return float(k)

out = []
for i, w in enumerate(W):
    ws = START + dt.timedelta(days=7 * i)
    by = {s["day"]: s for s in w["sessions"]}
    for d in range(7):
        date = ws + dt.timedelta(days=d)
        s = by.get(d)
        out.append(dict(
            date=date.isoformat(), dow=DAYS[d], week=i + 1, phase=w["phase"],
            phaseWeek=w["wk"], cycle=w["cycle"], weekNote=w["note"],
            type=s["type"] if s else "מנוחה",
            km=str(s["km"]) if s else "",
            desc=s["desc"] if s else "",
            extra=s["extra"] if s else ""))

assert out[-2]["date"] == RACE.isoformat() and "חצי" in out[-2]["type"], out[-2]

weeks = []
for i, w in enumerate(W):
    tot = sum(kmnum(s["km"]) for s in w["sessions"])
    weeks.append(dict(week=i + 1, start=(START + dt.timedelta(days=7 * i)).isoformat(),
                      phase=w["phase"], phaseWeek=w["wk"], cycle=w["cycle"], note=w["note"],
                      km=round(tot, 1), sessions=len(w["sessions"]),
                      lsd=max([kmnum(s["km"]) for s in w["sessions"] if s["type"] == "LSD"] or [0])))
    print(i + 1, weeks[-1]["start"], w["phase"], w["wk"], round(tot, 1), weeks[-1]["lsd"])

json.dump(dict(days=out, weeks=weeks, race=RACE.isoformat(), start=START.isoformat()),
          open(str(__import__("pathlib").Path(__file__).resolve().parent.parent/"plan/plan.json"), "w"), ensure_ascii=False)

with open(str(__import__("pathlib").Path(__file__).resolve().parent.parent/"plan/plan.csv"), "w", newline="", encoding="utf-8") as f:
    wr = csv.writer(f)
    wr.writerow(["תאריך", "יום", "שבוע", "שלב", "שבוע בשלב", "מחזוריות", "סוג האימון", "מרחק (ק\"מ)", "תיאור האימון", "הערות", "מרחק בפועל (ק\"מ)", "בוצע"])
    for r in out:
        d = dt.date.fromisoformat(r["date"]).strftime("%d/%m/%Y")
        wr.writerow([d, r["dow"], r["week"], r["phase"], r["phaseWeek"], r["cycle"], r["type"], r["km"], r["desc"], r["extra"], "", ""])
with open(str(__import__("pathlib").Path(__file__).resolve().parent.parent/"plan/weeks.csv"), "w", newline="", encoding="utf-8") as f:
    wr = csv.writer(f)
    wr.writerow(["שבוע", "מתאריך", "שלב", "שבוע בשלב", "מחזוריות", "נפח מתוכנן (ק\"מ)", "LSD", "אימונים", "הערה"])
    for w in weeks:
        wr.writerow([w["week"], dt.date.fromisoformat(w["start"]).strftime("%d/%m/%Y"), w["phase"], w["phaseWeek"], w["cycle"], w["km"], w["lsd"], w["sessions"], w["note"]])

# f-strings above collapse "{{tok}}" to "{tok}" – normalise every token back to "{{tok}}"
import re as _re
_fix = lambda t: _re.sub(r'(?<!\{)\{(hr:\w+|p:\d+:\d\d)\}(?!\})', r'{{\1}}', t)
_P = json.load(open(str(__import__("pathlib").Path(__file__).resolve().parent.parent/"plan/plan.json")))
for _d in _P["days"]:
    _d["desc"] = _fix(_d["desc"])
json.dump(_P, open(str(__import__("pathlib").Path(__file__).resolve().parent.parent/"plan/plan.json"), "w"), ensure_ascii=False)
