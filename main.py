"""Polymarket FAA attribution forecast, v2 (Python 3.13, standard library only).

Model: persistence median with a locally calibrated, asymmetric spread.

For each market, let x be the Yes price at the checkpoint.  For minute
h = 1..240 after the checkpoint the forecast quantiles are

    q_tau(h) = clamp(x + Z[tau] * sigma * sqrt(h), 0, 1),

rounded to 6 decimals and forced non-decreasing across tau.

sigma is the market's own recent realised volatility: the mean absolute
1-minute price change over the last 120 minutes blended 85/15 with the
mean over the last 720 minutes, times 1.8, floored at 0.0004 and capped
at 0.005 per sqrt-minute.  A market that has barely moved lately gets a
tight forecast; one that has been jumping gets a wide one.

Z = [-1.8, -0.75, 0, 0.25, 1.6] is deliberately asymmetric.  These
prices are probabilities of mutually exclusive outcomes: a market can
crash a long way down (its candidate fades) but can only rise as far as
the room the other markets leave, and the short-horizon move
distribution is a point mass at "no move" with occasional jumps, so the
5% tail sits much further out than the 95% tail and the 25% quantile
sits closer to the median than the 75% one does not -- the lower inner
quantile is the wider of the two.  The offsets were chosen by
grid search on practice cases p00-p02 and confirmed on held-out cases
p03-p04 (see README.md); the median is plain persistence, because
drift, trend-following and trailing-mean reversion all made held-out
pinball worse.

Program contract: reads every <id>.in in $MAKEFUN_INPUT_DIR (default
/input), writes <id>.out to $MAKEFUN_OUTPUT_DIR (default /output).
Deterministic, no network, no randomness.
"""

import json
import math
import os
from pathlib import Path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)
# Asymmetric quantile offsets (see module docstring).
Z = (-1.8, -0.75, 0.0, 0.25, 1.6)
VOL_MULT = 1.8
VOL_FLOOR = 0.0004
VOL_CAP = 0.005
W120 = 0.85  # weight on the last-120-minute realised volatility


def _price6(x):
    """Clamp to [0, 1] and round to 6 decimals (0, never -0)."""
    return round(min(1.0, max(0.0, x)) * 1e6) / 1e6 + 0.0


def _sigma(prices):
    """Realised volatility per sqrt-minute from the price history."""
    n = len(prices)
    if n < 2:
        return VOL_FLOOR
    # Mean absolute 1-minute change over the last 120 and last 720 minutes.
    # One backwards pass keeps both window sums exact.
    s120 = 0.0
    s720 = 0.0
    c120 = 0
    c720 = 0
    for i in range(n - 1, 0, -1):
        d = abs(prices[i] - prices[i - 1])
        age = n - i  # minutes before the checkpoint this change ends
        if age <= 720:
            s720 += d
            c720 += 1
            if age <= 120:
                s120 += d
                c120 += 1
        else:
            break
    mad120 = s120 / c120 if c120 else 0.0
    mad720 = s720 / c720 if c720 else mad120
    sig = VOL_MULT * (W120 * mad120 + (1.0 - W120) * mad720)
    return min(VOL_CAP, max(VOL_FLOOR, sig))


def forecast_market(prices, horizon):
    """240 (or horizon) rows of five quantiles for one market."""
    if not prices:
        raise ValueError("market has no prices")
    x = prices[-1]
    sig = _sigma(prices)
    rows = []
    for h in range(1, horizon + 1):
        spread = sig * math.sqrt(h)
        row = []
        prev = -1.0
        for z in Z:
            q = _price6(x + z * spread)
            if q < prev:  # keep rows non-decreasing after clamping
                q = prev
            row.append(q)
            prev = q
        rows.append(row)
    return rows


def main():
    in_dir = Path(INPUT_DIR)
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(in_dir.glob("*.in"))
    for path in inputs:
        case_id = path.name[: -len(".in")]
        with path.open("r", encoding="utf-8") as fh:
            case = json.load(fh)
        if list(case["quantiles"]) != list(QUANTILES):
            raise ValueError(f"{path.name} asks for quantiles {case['quantiles']}")
        horizon = int(case["horizon_minutes"])
        forecasts = [
            {"id": m["id"], "q": forecast_market(m["prices"], horizon)}
            for m in case["markets"]
        ]
        out_path = out_dir / f"{case_id}.out"
        with out_path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps({"forecasts": forecasts}) + "\n")


if __name__ == "__main__":
    main()
