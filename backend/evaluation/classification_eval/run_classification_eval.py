# -*- coding: utf-8 -*-
"""사람이 단 정답과 PASSBOX 분류 결과를 비교해 정확도와 등급별 정밀도·재현율을 낸다.

사용 (backend 폴더에서, 분류 서비스가 떠 있어야 한다):
  python evaluation/classification_eval/run_classification_eval.py            # labels.csv 채점
  python evaluation/classification_eval/run_classification_eval.py --predict  # 정답 없이 예측만 확인

두 가지 결과를 같이 낸다.
  - 모델 단독: 분류 모델(KLUE-RoBERTa)의 추천 그대로
  - 하이브리드: 실제 서비스와 같은 순서로 보정한 최종 추천(기밀 상한 -> 탐지 바닥)
labels.csv는 labels_template.csv를 복사해 '정답등급(C/S/O)' 열을 채운 것이다.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from app.classifier import apply_confidential_ceiling, apply_designation_floor, apply_findings_floor, classifier  # noqa: E402
from app.security_scan import scan_text  # noqa: E402

GRADES = ["C", "S", "O"]
RANK = {"O": 0, "S": 1, "C": 2}


def predict(text: str) -> tuple[str | None, str | None]:
    findings = scan_text(text)
    raw = classifier.recommend(text, findings)
    final = apply_designation_floor(apply_findings_floor(apply_confidential_ceiling(raw, findings, text), findings), text)
    return raw.recommended_grade, final.recommended_grade


def confusion(pairs):
    m = {t: Counter() for t in GRADES}
    for truth, pred in pairs:
        m[truth][pred or "없음"] += 1
    return m


def report(title, pairs):
    n = len(pairs)
    correct = sum(1 for t, p in pairs if t == p)
    print(f"\n[{title}]  정확도 {correct}/{n} = {100 * correct / n:.1f}%")
    m = confusion(pairs)
    print("  실제\\예측   C   S   O")
    for t in GRADES:
        print(f"  {t:>6}  " + "".join(f"{m[t][p]:>4}" for p in GRADES))
    stats = {}
    for g in GRADES:
        tp = m[g][g]
        fn = sum(m[g][p] for p in GRADES if p != g) + m[g]["없음"]
        fp = sum(m[t][g] for t in GRADES if t != g)
        prec = tp / (tp + fp) if tp + fp else None
        rec = tp / (tp + fn) if tp + fn else None
        stats[g] = {"precision": prec, "recall": rec, "support": tp + fn}
        f = lambda v: "-" if v is None else f"{100 * v:.0f}%"  # noqa: E731
        print(f"  {g}: 정밀도 {f(prec)} · 재현율 {f(rec)} · 실제 {tp + fn}건")
    # 새는 쪽(더 높은 등급을 낮게 판정) vs 막는 쪽(낮은 등급을 높게 판정)을 따로 센다.
    leak = sum(1 for t, p in pairs if p and RANK[p] < RANK[t])
    over = sum(1 for t, p in pairs if p and RANK[p] > RANK[t])
    print(f"  위험한 오류(실제보다 낮게 판정): {leak}건 · 과잉 통제(실제보다 높게 판정): {over}건")
    return {"accuracy": correct / n, "n": n, "per_grade": stats, "under_graded": leak, "over_graded": over}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predict", action="store_true", help="정답 없이 예측만 출력")
    ap.add_argument("--labels", default=str(HERE / "labels.csv"))
    args = ap.parse_args()

    docs = sorted((HERE / "candidates").glob("doc_*.txt"))
    preds = {}
    for p in docs:
        preds[p.name] = predict(p.read_text(encoding="utf-8"))

    if args.predict:
        for name, (raw, final) in preds.items():
            print(f"{name}  모델 {raw}  → 최종 {final}")
        return

    labels = {}
    with open(args.labels, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            g = (row.get("정답등급(C/S/O)") or "").strip().upper()
            if g in GRADES:
                labels[row["file"]] = g
    missing = [n for n in preds if n not in labels]
    if missing:
        print(f"정답이 비어 있는 문서 {len(missing)}건은 제외합니다: {', '.join(missing[:5])}...")
    names = [n for n in preds if n in labels]
    if not names:
        sys.exit("채점할 정답이 없습니다. labels.csv를 채워 주세요.")

    print(f"채점 대상 {len(names)}건 · 정답 분포 {dict(Counter(labels[n] for n in names))}")
    out = {
        "model_only": report("모델 단독", [(labels[n], preds[n][0]) for n in names]),
        "hybrid": report("하이브리드(실제 서비스)", [(labels[n], preds[n][1]) for n in names]),
    }
    print("\n[틀린 문서]")
    for n in names:
        raw, final = preds[n]
        if final != labels[n] or raw != labels[n]:
            print(f"  {n}: 정답 {labels[n]} · 모델 {raw} · 최종 {final}")
    (HERE / "result.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
