#!/usr/bin/env python3
"""
DON Futures v1 — Backtesting

Run historical backtests to validate strategy.

Usage:
    python backtest.py                    # Default: 1 year, 5-min
    python backtest.py --years 2          # 2 years of data
    python backtest.py --interval 15      # 15-minute bars
    python backtest.py --slippage 0.5     # Add slippage
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from bot import DonFuturesStrategy, DonFuturesConfig, VALIDATED_CONFIG, get_logger


def load_es_data(interval_minutes: int = 5, years: float = 1.0) -> pd.DataFrame:
    """Load and resample ES data"""
    
    # Try multiple data sources
    data_paths = [
        '/home/ubuntu/clawd/topstep/data/ES_continuous_RTH_1m.csv',
        'data/ES_1m.csv',
        '../topstep/data/ES_continuous_RTH_1m.csv'
    ]
    
    df = None
    for path in data_paths:
        if os.path.exists(path):
            df = pd.read_csv(path)
            print(f"Loaded data from: {path}")
            break
    
    if df is None:
        raise FileNotFoundError("No ES data found. Expected 1-minute OHLCV CSV.")
    
    # Parse timestamps
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.set_index('timestamp')
    
    # Resample if needed
    if interval_minutes > 1:
        df = df.resample(f'{interval_minutes}min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
    
    # Filter to requested timeframe
    bars_per_year = int(252 * 6.5 * 60 / interval_minutes)  # Trading days * hours * minutes
    bars_needed = int(bars_per_year * years)
    df = df.tail(bars_needed)
    
    print(f"Data: {len(df)} bars, {df.index.min().date()} to {df.index.max().date()}")
    return df


def run_backtest(df: pd.DataFrame, config: DonFuturesConfig, 
                 slippage_pts: float = 0) -> dict:
    """Run backtest and return results"""
    
    # Create strategy (suppress logging for backtest)
    strategy = DonFuturesStrategy(config, "logs/backtest")
    
    trades = []
    
    for _, row in df.iterrows():
        bar = {
            'timestamp': row.name,
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row.get('volume', 0)
        }
        
        signal = strategy.add_bar(bar, 'backtest')
        
        if signal and signal['action'] == 'exit':
            # Apply slippage
            adj_pnl = signal['pnl_pts'] - slippage_pts
            trades.append({
                'timestamp': signal['timestamp'],
                'direction': signal['direction'],
                'entry_type': signal['entry_type'],
                'entry_price': signal['entry_price'],
                'exit_price': signal['exit_price'],
                'pnl_pts': adj_pnl,
                'pnl_dollars': adj_pnl * config.point_value,
                'reason': signal['reason']
            })
    
    if not trades:
        return {'trades': 0, 'win_rate': 0, 'pnl_pts': 0, 'pnl_dollars': 0}
    
    wins = [t for t in trades if t['pnl_pts'] > 0]
    losses = [t for t in trades if t['pnl_pts'] <= 0]
    
    return {
        'trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': len(wins) / len(trades) * 100,
        'pnl_pts': sum(t['pnl_pts'] for t in trades),
        'pnl_dollars': sum(t['pnl_dollars'] for t in trades),
        'avg_win': np.mean([t['pnl_pts'] for t in wins]) if wins else 0,
        'avg_loss': np.mean([t['pnl_pts'] for t in losses]) if losses else 0,
        'trades_list': trades
    }


def main():
    parser = argparse.ArgumentParser(description='DON Futures Backtest')
    parser.add_argument('--interval', type=int, default=5, help='Bar interval (minutes)')
    parser.add_argument('--years', type=float, default=1.0, help='Years of data')
    parser.add_argument('--slippage', type=float, default=0, help='Slippage in points')
    parser.add_argument('--full', action='store_true', help='Run full multi-year breakdown')
    args = parser.parse_args()
    
    print("="*60)
    print("DON FUTURES v1 — BACKTEST")
    print("="*60)
    
    # Load data
    df = load_es_data(args.interval, args.years)
    
    # Run backtest
    print(f"\nRunning backtest (slippage: {args.slippage} pts)...")
    result = run_backtest(df, VALIDATED_CONFIG, args.slippage)
    
    # Print results
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"Trades:    {result['trades']}")
    print(f"Win Rate:  {result['win_rate']:.1f}%")
    print(f"Total P&L: {result['pnl_pts']:.1f} pts (${result['pnl_dollars']:,.0f})")
    print(f"Avg Win:   {result['avg_win']:.2f} pts")
    print(f"Avg Loss:  {result['avg_loss']:.2f} pts")
    
    # Exit reason breakdown
    if result.get('trades_list'):
        print("\nExit Reasons:")
        for reason in ['target', 'trail_stop', 'stop', 'time']:
            count = len([t for t in result['trades_list'] if t['reason'] == reason])
            pnl = sum(t['pnl_pts'] for t in result['trades_list'] if t['reason'] == reason)
            if count > 0:
                print(f"  {reason:<12} {count:>5} trades  {pnl:>8.1f} pts")
    
    # Year-by-year breakdown
    if args.full and result.get('trades_list'):
        print("\n" + "="*60)
        print("YEAR-BY-YEAR BREAKDOWN")
        print("="*60)
        
        trades_df = pd.DataFrame(result['trades_list'])
        trades_df['year'] = pd.to_datetime(trades_df['timestamp']).dt.year
        
        for year, group in trades_df.groupby('year'):
            wins = len(group[group['pnl_pts'] > 0])
            wr = wins / len(group) * 100
            pnl = group['pnl_dollars'].sum()
            print(f"{year}: {len(group):>5} trades | {wr:>5.1f}% WR | ${pnl:>10,.0f}")


if __name__ == '__main__':
    main()
