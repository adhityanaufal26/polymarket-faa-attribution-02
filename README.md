# polymarket-faa-attribution-02 — v3 entry

Forecasts each market's Yes price at every minute of the next 4 hours as five
quantiles (0.05, 0.25, 0.5, 0.75, 0.95), minimising mean pinball loss.

## Model

`main.ts` (Node 22, standard library only) forecasts
`q_tau(h) = clamp(x + Z[level][hbucket][tau] * sigma * sqrt(h), 0, 1)`,
where `x` is the market's last price and `sigma` is a per-market scale:
`0.006 * sqrt(x(1-x))`, floored at `0.004` for markets younger than 120 minutes,
plus `0.2 *` the population standard deviation of the last 60 one-minute moves.

`Z` is not Gaussian. It is the empirical quantiles of the standardised residuals
`(y - x) / (sigma * sqrt(h))` pooled over the practice cases p00–p02
(recency-weighted 1-2-4), split by price level (`x < 0.01`, `0.01–0.05`, `>= 0.05`)
and horizon (`h <= 60`, `61–180`, `181–240`). The median is shrunk 50% toward 0
and the outer quantiles 15% toward 0: the level drift and tail width of the early
practice cases do not fully carry over to later checkpoints.

## Practice scores (local, scored against the next case's price grid)

- All practice cases p00–p04: pinball **0.2903** (house baseline 0.3925, v2 0.2966)
- Held-out p03–p04: pinball **0.2155** (v2 0.2196)

## Run

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out node main.ts
```
