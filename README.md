# DON Futures v1 — Failed Test Strategy for ES/MES

## The Edge
Fade liquidity sweeps. When price breaks a channel level and immediately reverses back inside, 
stop hunters have trapped traders. We enter the opposite direction with tight trailing stops.

## Validated Results (5-min ES, 2021-2025)
- **Win Rate:** 84-86% across all years
- **All 5 years profitable**
- **Survives 1pt slippage:** Still 70% WR, $263K/year
- **Out-of-sample validated:** Train 84.3% → Test 84.7%

## Strategy Logic
1. Calculate 10-bar Donchian channel (support/resistance)
2. Detect "failed test" — price breaks channel then closes back inside
3. Enter opposite direction at close of reversal bar
4. Tight trailing stop (1pt activation, 0.5pt trail)
5. 4pt stop loss, 4pt target

## Entry Types (configurable)
- **Failed Test** (primary) — fade liquidity sweeps
- **Bounce** — fade rejection at channel
- **Breakout** — follow strong breaks (disabled by default)

## Architecture
```
don-futures-v1/
├── bot/
│   ├── strategy.py      # Core strategy logic
│   ├── data_feed.py     # Live data (ProjectX priority)
│   ├── executor.py      # Order execution
│   └── logger.py        # Comprehensive logging
├── logs/                # All logs go here
├── config.py            # Configuration
├── run_live.py          # Live trading entry
├── run_shadow.py        # Paper trading mode
└── backtest.py          # Backtesting
```

## Quick Start
```bash
# Shadow mode (paper trading)
python run_shadow.py

# Live mode (real orders)
python run_live.py --live
```

## Logging
Every signal, entry, exit, and state change is logged to:
- Console (real-time)
- `logs/don_futures_YYYY-MM-DD.log` (daily files)
- `logs/trades.jsonl` (structured trade log)
- `logs/signals.jsonl` (all signals, even unfilled)
