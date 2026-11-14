# Polymarket FAA attribution forecast — quantile forecaster

Entry for make.fun's `polymarket-faa-attribution-02` (and `-01`) competition:
forecast the Yes price of every market of Polymarket's FAA outage attribution
family at every minute of the 4 hours after a checkpoint, as five quantiles
(5%, 25%, 50%, 75%, 95%) per minute.

## Run

```
python3 main.py
```

Reads every `<id>.in` in `$MAKEFUN_INPUT_DIR` (default `/input`) and writes
`<id>.out` to `$MAKEFUN_OUTPUT_DIR` (default `/output`). Python 3.13,
standard library only, no network, deterministic, ~0.05 s per case.

## Model

See the docstring in `main.py`. In short, per market:

- **Median: the last price** (persistence). Recent trends do not extrapolate.
- **Spread: the market's own recent realised volatility** — mean absolute
  1-minute change over the last 120 minutes (85%) blended with the last
  720 minutes (15%), times 1.8, floored at 0.0004 and capped at 0.005
  price units per sqrt-minute. The 72-hour window's long-run changes are
  deliberately not used: they are dominated by rare multi-day regime moves
  and make the forecast far too wide.
- **Shape: asymmetric offsets widening with sqrt(h)** —
  `z = [-2.5, -0.75, 0, 0.45, 1.6]`. Middle quantiles sit close to the last
  price (the price usually does not move), tails reach far out (jumps
  happen), and the downside tail is wider than the upside (in a
  multi-candidate event most markets decay toward 0 and only one rises
  toward 1).
- All quantiles are clamped to `[0, 1]`, rows are non-decreasing, values
  rounded to 6 decimals.

## Practice score (local, p00–p04)

Actuals for p00–p04 are recovered from the following case's input file
(each case is 240 minutes after the previous one).

| model | mean pinball loss |
|---|---|
| this entry | **0.301498** |
| house persistence baseline (σ = 0.0025) | 0.392518 |

Per case: p00 0.432115, p01 0.305225, p02 0.354811, p03 0.251082,
p04 0.201250 — the entry beats the baseline on every case. (The house
reports the baseline at 0.363589 over all six practice cases; p05's
actuals are not in the kit.)

## License

MIT — see `LICENSE`.
