#!/usr/bin/env python3
"""Forecast Polymarket Yes prices, 4 hours ahead, as five quantiles a minute.

make.fun competition polymarket-faa-attribution-02 (and -01): program/v1 entry.
Python 3.13, standard library only, no network, deterministic.

Reads every <id>.in in $MAKEFUN_INPUT_DIR (else /input) and writes
<id>.out to $MAKEFUN_OUTPUT_DIR (else /output):
  {"forecasts": [{"id": <market id>, "q": [[q05, q25, q50, q75, q95] x 240]}]}

Model (per market, fit from that market's own prices only)
-----------------------------------------------------------
Polymarket Yes prices are step functions: most minutes they do not move at
all, then they tick, and now and then they jump. The conditional distribution
of the price h minutes ahead therefore has a point mass at the last price and
heavy, asymmetric tails -- it is not Gaussian. This forecaster uses:

  * Median: the last price (persistence). Recent trends do not extrapolate:
    on the practice cases every drift term we tried made the loss worse.
  * Spread: per-market, from the market's own recent realised volatility --
    the mean absolute 1-minute change over the last 120 minutes, blended
    with 15% weight on the last 720 minutes for stability, times 1.8, with
    a floor of 0.0004 and a cap of 0.005 price units per sqrt-minute.
    A market that has been moving lately gets a wider forecast; a quiet one
    gets a narrow one. The 72-hour window's long-run changes are NOT used:
    they are dominated by rare multi-day regime moves and make the forecast
    far too wide.
  * Shape: asymmetric quantile offsets that widen with sqrt(h):
    z = [-2.5, -0.75, 0, 0.45, 1.6]. The middle quantiles sit close to the
    last price (the price usually does not move), the tails reach far out
    (jumps happen), and the downside tail is wider than the upside: in a
    multi-candidate event most markets decay toward 0 and only one rises
    toward 1, so a random market is more likely to fall than to rise.
  * Every quantile is clamped to [0, 1], rows are enforced non-decreasing,
    and values are rounded to 6 decimals.

Practice (p00-p04, actuals recovered from the following case's input):
  this model  mean pinball loss 0.3015 (p00 0.4321, p01 0.3052, p02 0.3548,
  p03 0.2511, p04 0.2013) vs house persistence baseline 0.3925 on the same
  five cases (house reports 0.363589 over all six practice cases).
"""

import json
import math
import os
from pathlib import Path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]

# Asymmetric quantile offsets (see module docstring).
Z = [-2.5, -0.75, 0.0, 0.45, 1.6]

# Recent-volatility window: 120 minutes, blended with 720 minutes.
WIN_SHORT = 120
WIN_LONG = 720
W_SHORT = 0.85
VOL_MULT = 1.8
SIGMA_FLOOR = 0.0004
SIGMA_CAP = 0.005


def _mean_abs_change(prices, window):
    """Mean absolute 1-minute change over the last `window` minutes."""
    n = len(prices)
    w = min(window, n - 1)
    if w <= 0:
        return 0.0
    total = 0.0
    for i in range(n - w - 1, n - 1):
        d = prices[i + 1] - prices[i]
        total += d if d >= 0.0 else -d
    return total / w


def _round6(x):
    """Clamp to [0, 1] and round to 6 decimals (0, never -0)."""
    if x < 0.0:
        x = 0.0
    elif x > 1.0:
        x = 1.0
    return round(x, 6) + 0.0


def forecast_market(prices, horizon):
    """240 rows of five quantiles for one market's prices (last = checkpoint)."""
    if not prices:
        raise ValueError("market has no prices")
    if horizon <= 0:
        # Degenerate horizon: no minutes to forecast. (The grader always
        # asks for 240, but a zero/negative horizon must not produce rows.)
        return []
    x = prices[-1]
    sigma = (
        W_SHORT * _mean_abs_change(prices, WIN_SHORT)
        + (1.0 - W_SHORT) * _mean_abs_change(prices, WIN_LONG)
    ) * VOL_MULT
    if sigma < SIGMA_FLOOR:
        sigma = SIGMA_FLOOR
    elif sigma > SIGMA_CAP:
        sigma = SIGMA_CAP
    rows = []
    for h in range(1, horizon + 1):
        spread = sigma * math.sqrt(h)
        row = [_round6(x + z * spread) for z in Z]
        # Enforce monotonicity (clamping can only break it at the bounds).
        for j in range(1, 5):
            if row[j] < row[j - 1]:
                row[j] = row[j - 1]
        rows.append(row)
    return rows


def main():
    in_dir = Path(INPUT_DIR)
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in sorted(p.name for p in in_dir.iterdir() if p.name.endswith(".in")):
        case_id = name[: -len(".in")]
        with open(in_dir / name, "r", encoding="utf-8") as fh:
            case = json.load(fh)
        if list(case["quantiles"]) != QUANTILES:
            raise ValueError(f"{name} asks for quantiles {case['quantiles']}")
        horizon = int(case["horizon_minutes"])
        forecasts = [
            {"id": m["id"], "q": forecast_market(m["prices"], horizon)}
            for m in case["markets"]
        ]
        with open(out_dir / f"{case_id}.out", "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"forecasts": forecasts}) + "\n")


if __name__ == "__main__":
    main()
