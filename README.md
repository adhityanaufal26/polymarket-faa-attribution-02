# polymarket-faa-attribution-02 — v2

Forecast the Yes price of each market of Polymarket's FAA outage
attribution family, 240 minutes ahead, as five quantiles
(5%, 25%, 50%, 75%, 95%) per market per minute. Score: mean pinball
loss, lower is better.

## Model

Persistence median with a locally calibrated, asymmetric spread
(`main.py`, Python 3.13 stdlib only, deterministic, no network):

```
q_tau(h) = clamp(x + Z[tau] * sigma * sqrt(h), 0, 1)   # 6 decimals
```

- `x` = the market's Yes price at the checkpoint.
- `sigma` = mean absolute 1-minute change over the last 120 minutes
  blended 85/15 with the last 720 minutes, x1.8, floored 0.0004,
  capped 0.005 per sqrt-minute. A quiet market gets a tight forecast;
  a jumping market gets a wide one.
- `Z = [-1.8, -0.75, 0, 0.25, 1.6]`, asymmetric: the 5% tail sits
  further out than the 95% tail, and the 25% quantile sits closer to
  the median than the 75% one. These prices are probabilities of
  mutually exclusive outcomes, and the short-horizon move distribution
  is a point mass at "no move" with occasional jumps.

## What was tried and rejected

Everything below was scored with a local scorer that reproduces the
v1 entry's per-case pinball exactly (p00 0.432115, p01 0.305225,
p02 0.354811, p03 0.251082, p04 0.201250; actuals for a case taken
from the following case's input file, p05's actuals not in the kit).

- Drift / trend-following medians (constant drift, linear-slope
  extrapolation, mean reversion to the trailing mean, reversion of the
  cross-market price sum toward 1.0): all worse on held-out cases.
  The median is plain persistence.
- Empirical quantiles of historical forward changes (pooled, and
  matched on price level): much worse (0.44–0.50) — pooled history
  is dominated by the early regime when markets decayed from their
  0.485 opening midpoint; only the recent realised volatility is
  regime-current.
- Volatility variants (EWMA, 60/240-min MAD, 90th-percentile |move|,
  level-dependent multipliers, horizon exponents 0.3–0.7,
  horizon-dependent inner/outer z shaping): all within noise of v1,
  none better on both splits.

## Practice results (mean pinball, item-weighted)

| model | p00 | p01 | p02 | p03 | p04 | mean (p00–p04) |
|---|---|---|---|---|---|---|
| v1 (Z=[-2.5,-0.75,0,0.45,1.6]) | 0.432115 | 0.305225 | 0.354811 | 0.251082 | 0.201250 | 0.3015 |
| **v2 (this entry)** | **0.424345** | **0.299179** | **0.356786** | **0.245086** | **0.195238** | **0.2966** |

Tuned on p00–p02 (0.3641 → 0.3601), confirmed on held-out p03–p04
(0.2256 → 0.2196). The improvement is small but real and consistent
(4 of 5 cases better); the ≤0.20 target was not reachable — most of
the loss is irreducible price movement over 240 minutes, and every
structurally different model tested scored worse.

## Run

```
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `<id>.in` in the input directory, writes `<id>.out`
(`{"forecasts": [{"id", "q": [[...5 quantiles...] x 240]}]}`) per case.
