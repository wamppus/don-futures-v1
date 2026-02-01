# DON Futures v1 — Architecture

## Strategy Overview

### The Edge: Failed Test (Liquidity Sweep Fade)
When price breaks a channel level and immediately reverses back inside:
1. Stop hunters have triggered stops above/below the channel
2. Trapped traders are now on the wrong side
3. Smart money reverses the move
4. We enter opposite direction with tight trail

### Validated Results (5-min ES, 2021-2025)
- **Win Rate:** 84-86% (consistent all years)
- **P&L:** $358K-$620K/year depending on trail settings
- **All 5 years profitable**
- **Survives 1pt slippage**

## Entry Logic

```
Bar N:
  - Calculate 10-bar Donchian channel (high/low)
  - Check if price breaks channel by > tolerance
  - Track: last_broke_high, last_broke_low

Bar N+1:
  - If last_broke_high AND close < channel_high:
      → FAILED TEST SHORT (price reclaimed, longs trapped)
  - If last_broke_low AND close > channel_low:
      → FAILED TEST LONG (price reclaimed, shorts trapped)
```

## Exit Logic

```
1. TARGET: 4 points profit
2. TRAIL STOP (primary exit):
   - Activate at 1 point profit
   - Trail 0.5 points behind
   - Locks in gains before reversal
3. INITIAL STOP: 4 points
4. TIME: 5 bars max
```

## Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  ProjectX   │────▶│  DataFeed   │────▶│  Strategy   │
│    API      │     │  (bars)     │     │  (signals)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   Logger    │◀────│  Executor   │
                    │ (EVERYTHING)│     │  (orders)   │
                    └─────────────┘     └─────────────┘
```

## File Structure

```
don-futures-v1/
├── bot/
│   ├── __init__.py      # Package exports
│   ├── strategy.py      # Core strategy logic
│   ├── data_feed.py     # Live data (ProjectX priority)
│   ├── logger.py        # Comprehensive logging
│   └── executor.py      # Order execution (TODO)
│
├── logs/                # All logs (gitignored)
│   ├── don_futures_YYYY-MM-DD.log  # Daily human-readable
│   ├── trades.jsonl     # Structured trade log
│   ├── signals.jsonl    # All signals
│   └── state.jsonl      # Position state changes
│
├── data/                # Historical data (gitignored)
│
├── run_shadow.py        # Paper trading mode
├── run_live.py          # Live trading (TODO)
├── backtest.py          # Historical backtesting
│
├── README.md            # Quick start guide
├── ARCHITECTURE.md      # This file
└── .gitignore
```

## Configuration

### VALIDATED_CONFIG (DO NOT CHANGE WITHOUT TESTING)
```python
DonFuturesConfig(
    channel_period=10,
    enable_failed_test=True,
    enable_bounce=False,       # Disabled — doesn't add value
    enable_breakout=False,     # Disabled — failed test is the edge
    trail_activation_pts=1.0,  # Early activation
    trail_distance_pts=0.5,    # Tight trail
    stop_pts=4.0,
    target_pts=4.0
)
```

### Why These Settings?
- **Channel 10 bars**: Captures recent S/R, not too noisy
- **Trail 1.0/0.5**: Early + tight = locks profits before reversal
- **Stop 4 pts**: Wide enough to avoid noise, tight enough to limit damage
- **Failed test only**: This IS the edge. Bounces and breakouts dilute it.

## Logging Philosophy

**LOG EVERYTHING.**

Every bar, every signal (even non-triggered), every state change.
This allows:
1. Post-session analysis
2. Bug detection
3. Strategy validation
4. Regulatory compliance (if needed)

Logs are:
- Human-readable (console + daily files)
- Machine-readable (JSONL for analysis)
- Timestamped and sourced

## Risk Management

### Position Sizing
- One contract at a time (scale up after validation)
- Max risk per trade: 4 points ($200 ES, $20 MES)

### Daily Limits (recommended)
- Max loss/day: 8 points ($400 ES)
- Max trades/day: 30 (if all stop out = $1200 ES)

### Session Management
- Only trade RTH (9:30-16:00 ET)
- Avoid first 5 minutes (opening volatility)
- Flatten before close

## TODO

- [ ] Order executor (ProjectX order API)
- [ ] Position flattening on shutdown
- [ ] Daily P&L limits
- [ ] Multiple contract scaling
- [ ] Telegram alerts
- [ ] Dashboard/GUI
