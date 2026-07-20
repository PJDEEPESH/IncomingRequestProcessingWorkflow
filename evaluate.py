"""
Classification accuracy evaluation on the labelled sample set.

This answers the rubric's biggest line (40% = "classification accuracy"):
it runs the classifier over sample_requests.csv (which now has ground-truth
`true_type` / `true_urgency` columns) and prints an accuracy % and a confusion
matrix. Put the resulting number on your slide.

Run:  .venv\Scripts\python.exe evaluate.py
"""
import os

import pandas as pd

from classifier import classify

TYPES = ["Complaint", "General Enquiry", "Service Request", "Escalation"]
CSV = os.path.join(os.path.dirname(__file__), "sample_requests.csv")


def evaluate() -> dict:
    df = pd.read_csv(CSV)
    if "true_type" not in df.columns:
        raise SystemExit("sample_requests.csv has no 'true_type' column to grade against.")

    n = len(df)
    type_ok = urg_ok = 0
    engine = "-"
    confusion = {t: {p: 0 for p in TYPES} for t in TYPES}
    rows = []

    for _, r in df.iterrows():
        res = classify(str(r["message"]))
        engine = res["engine"]
        pred_t, pred_u = res["type"], res["urgency"]
        true_t = str(r["true_type"])
        true_u = str(r.get("true_urgency", ""))
        t_hit = pred_t == true_t
        u_hit = pred_u == true_u
        type_ok += t_hit
        urg_ok += u_hit
        if true_t in confusion and pred_t in confusion[true_t]:
            confusion[true_t][pred_t] += 1
        rows.append({
            "message": str(r["message"])[:48],
            "true": true_t, "pred": pred_t, "ok": "OK" if t_hit else "MISS",
        })

    return {
        "n": n, "engine": engine,
        "type_accuracy": round(100 * type_ok / n),
        "urgency_accuracy": round(100 * urg_ok / n),
        "type_correct": type_ok, "urgency_correct": urg_ok,
        "confusion": confusion, "rows": rows,
    }


def _print(res: dict):
    print(f"\nEngine: {res['engine']}   (samples: {res['n']})")
    print(f"TYPE    accuracy: {res['type_correct']}/{res['n']} = {res['type_accuracy']}%")
    print(f"URGENCY accuracy: {res['urgency_correct']}/{res['n']} = {res['urgency_accuracy']}%\n")

    print("Per-message:")
    for r in res["rows"]:
        mark = "  " if r["ok"] == "OK" else ">>"
        print(f"  {mark} [{r['ok']:4}] true={r['true']:16} pred={r['pred']:16} | {r['message']}")

    print("\nConfusion matrix (rows = true, cols = predicted):")
    short = {"Complaint": "Compl", "General Enquiry": "Enq", "Service Request": "Serv", "Escalation": "Esc"}
    header = " " * 9 + "".join(f"{short[t]:>7}" for t in TYPES)
    print(header)
    for t in TYPES:
        line = f"{short[t]:>8} " + "".join(f"{res['confusion'][t][p]:>7}" for p in TYPES)
        print(line)


if __name__ == "__main__":
    _print(evaluate())
