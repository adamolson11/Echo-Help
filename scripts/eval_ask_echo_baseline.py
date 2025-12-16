#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Confusion:
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    def accuracy(self) -> float:
        return (self.tp + self.tn) / self.total if self.total else 0.0

    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    def f1(self) -> float:
        p = self.precision()
        r = self.recall()
        return (2 * p * r) / (p + r) if (p + r) else 0.0


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and not math.isnan(float(x))


def _get(d: dict, path: list[str], default: Any = None) -> Any:
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def predict_helped(row: dict, *, ticket_threshold: float, snippet_threshold: float) -> bool:
    """A simple baseline classifier.

    Predict helpful if:
    - top snippet echo_score >= snippet_threshold OR
    - top ticket similarity score >= ticket_threshold
    """
    features = row.get("features") if isinstance(row.get("features"), dict) else {}

    top_ticket_score = _get(features, ["ticket", "top_score"], 0.0)
    top_snippet_echo = _get(features, ["snippet", "top_echo_score"], 0.0)

    t = float(top_ticket_score) if _is_number(top_ticket_score) else 0.0
    s = float(top_snippet_echo) if _is_number(top_snippet_echo) else 0.0

    return (s >= snippet_threshold) or (t >= ticket_threshold)


def confusion_for(rows: list[dict], *, ticket_threshold: float, snippet_threshold: float) -> Confusion:
    tp = fp = tn = fn = 0
    for row in rows:
        y = bool(row.get("label_helped"))
        yhat = predict_helped(row, ticket_threshold=ticket_threshold, snippet_threshold=snippet_threshold)
        if yhat and y:
            tp += 1
        elif yhat and not y:
            fp += 1
        elif not yhat and not y:
            tn += 1
        else:
            fn += 1
    return Confusion(tp=tp, fp=fp, tn=tn, fn=fn)


def grid_search_threshold(rows: list[dict]) -> tuple[float, float, Confusion]:
    """Pick thresholds that maximize F1 on the dataset (rough, deterministic)."""
    best: Confusion | None = None
    best_t = 0.6
    best_s = 0.0

    ticket_grid = [i / 20 for i in range(0, 21)]  # 0.00 .. 1.00
    snippet_grid = [i / 20 for i in range(0, 21)]

    for t in ticket_grid:
        for s in snippet_grid:
            c = confusion_for(rows, ticket_threshold=t, snippet_threshold=s)
            if best is None or c.f1() > best.f1():
                best = c
                best_t = t
                best_s = s

    assert best is not None
    return best_t, best_s, best


def calibration_by_kb_confidence(rows: list[dict], *, bins: int = 5) -> list[dict]:
    """Bucket by kb_confidence and report empirical helpful rate."""
    if bins <= 0:
        bins = 5

    buckets: list[list[bool]] = [[] for _ in range(bins)]
    for row in rows:
        kb = row.get("kb_confidence")
        if not _is_number(kb):
            continue
        v = float(kb)
        # Clamp to [0,1] for bucketing (kb_confidence can exceed 1.0 depending on scoring).
        v = max(0.0, min(1.0, v))
        idx = min(bins - 1, int(v * bins))
        buckets[idx].append(bool(row.get("label_helped")))

    out = []
    for i, ys in enumerate(buckets):
        lo = i / bins
        hi = (i + 1) / bins
        n = len(ys)
        rate = (sum(1 for y in ys if y) / n) if n else 0.0
        out.append({"bin": f"[{lo:.2f},{hi:.2f})", "n": n, "helped_rate": rate})
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Evaluate simple baselines on Ask Echo training export JSON")
    p.add_argument("--data", required=True, help="Path to JSON list from export_ask_echo_training_data.py")
    p.add_argument("--ticket-threshold", type=float, default=0.6)
    p.add_argument("--snippet-threshold", type=float, default=0.0)
    p.add_argument("--grid-search", action="store_true", help="Search thresholds that maximize F1")
    args = p.parse_args()

    rows = json.loads(Path(args.data).read_text())
    if not isinstance(rows, list):
        raise SystemExit("--data must be a JSON list")

    rows = [r for r in rows if isinstance(r, dict) and "label_helped" in r]
    if not rows:
        raise SystemExit("No labeled rows found")

    if args.grid_search:
        bt, bs, best = grid_search_threshold(rows)
        print(json.dumps({"best": {"ticket_threshold": bt, "snippet_threshold": bs, "metrics": best.__dict__}}, indent=2))
        print(
            f"best: acc={best.accuracy():.3f} p={best.precision():.3f} r={best.recall():.3f} f1={best.f1():.3f} "
            f"(ticket>={bt:.2f}, snippet>={bs:.2f})"
        )
    else:
        c = confusion_for(rows, ticket_threshold=args.ticket_threshold, snippet_threshold=args.snippet_threshold)
        print(
            f"acc={c.accuracy():.3f} p={c.precision():.3f} r={c.recall():.3f} f1={c.f1():.3f} "
            f"tp={c.tp} fp={c.fp} tn={c.tn} fn={c.fn} "
            f"(ticket>={args.ticket_threshold:.2f}, snippet>={args.snippet_threshold:.2f})"
        )

    calib = calibration_by_kb_confidence(rows, bins=5)
    print("\ncalibration_by_kb_confidence:")
    print(json.dumps(calib, indent=2))


if __name__ == "__main__":
    main()
