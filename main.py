#!/usr/bin/env python3
"""Nifty Wave Analyzer — Detects RSI-driven wave continuation patterns.

Strategy:
  SHORT: RSI hits OS (<=30) -> mark swing low -> RSI retraces to its 50EMA
         (stays <50) -> price breaks below swing low -> SHORT ENTRY
         Confirmation: MACD < 0, EMA 50 < EMA 100 (bearish trend)

  LONG:  RSI hits OB (>=70) -> mark swing high -> RSI retraces to its 50EMA
         (stays >50) -> price breaks above swing high -> LONG ENTRY
         Confirmation: MACD > 0, EMA 50 > EMA 100 (bullish trend)

Usage:
    # Run with synthetic data (demo):
    python main.py

    # Run with your own CSV data:
    python main.py --file data.csv

    # Specify timeframes:
    python main.py --file data.csv --timeframes 1m 3m

    # Require EMA trend alignment:
    python main.py --file data.csv --require-ema-trend

    # Disable MACD filter:
    python main.py --file data.csv --no-macd-filter
"""

import argparse
import sys

from sample_data import generate_synthetic_data, load_csv
from scanner import scan_all_timeframes, scan_timeframe, print_scan_results, filter_signals
from indicators import compute_all_indicators
from config import (
    RSI_PERIOD, RSI_EMA_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    EMA_FAST, EMA_SLOW,
)


def main():
    parser = argparse.ArgumentParser(
        description="Nifty Wave Analyzer — RSI wave continuation detector"
    )
    parser.add_argument(
        "--file", "-f", type=str, default=None,
        help="Path to OHLCV CSV file. If not provided, uses synthetic data."
    )
    parser.add_argument(
        "--timeframes", "-t", nargs="+", default=None,
        help="Timeframes to scan (e.g. 5s 15s 1m 3m). Default: all configured."
    )
    parser.add_argument(
        "--no-macd-filter", action="store_true",
        help="Disable MACD confirmation filter."
    )
    parser.add_argument(
        "--require-ema-trend", action="store_true",
        help="Only show signals where EMA 50/100 crossover aligns with direction."
    )
    parser.add_argument(
        "--single-tf", action="store_true",
        help="Treat input data as already at target timeframe (no resampling)."
    )
    parser.add_argument(
        "--timestamp-format", type=str, default=None,
        help="Explicit timestamp format (e.g. '%%Y-%%m-%%d %%H:%%M:%%S'). "
             "Usually not needed — Unix and ISO are auto-detected."
    )
    parser.add_argument(
        "--show-all-phases", action="store_true",
        help="Show detailed phase progression for debugging."
    )

    args = parser.parse_args()

    # Load data
    if args.file:
        print(f"Loading data from: {args.file}")
        df = load_csv(args.file, date_format=args.timestamp_format)
    else:
        print("No data file provided. Generating synthetic Nifty data for demo...")
        df = generate_synthetic_data(n_bars=10000, bar_seconds=1)

    print(f"Loaded {len(df)} bars")
    print(f"  Range: {df['close'].min():.2f} - {df['close'].max():.2f}")
    if "timestamp" in df.columns:
        print(f"  Period: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    print()

    if args.single_tf:
        # Run on data as-is without resampling
        tf_label = args.timeframes[0] if args.timeframes else "raw"
        signals = scan_timeframe(df, tf_label)
        filtered = filter_signals(
            signals,
            require_macd=not args.no_macd_filter,
            require_ema_trend=args.require_ema_trend,
        )
        results = {tf_label: signals}
        print_scan_results(results, require_macd=not args.no_macd_filter,
                           require_ema_trend=args.require_ema_trend)
    else:
        # Multi-timeframe scan
        results = scan_all_timeframes(df, timeframes=args.timeframes)
        print_scan_results(results, require_macd=not args.no_macd_filter,
                           require_ema_trend=args.require_ema_trend)

    # Summary statistics
    print("\n" + "=" * 80)
    print("  INDICATOR SETTINGS")
    print("=" * 80)
    print(f"  RSI Period: {RSI_PERIOD} | RSI EMA: {RSI_EMA_PERIOD}")
    print(f"  MACD: {MACD_FAST}/{MACD_SLOW}/{MACD_SIGNAL}")
    print(f"  Price EMA: {EMA_FAST}/{EMA_SLOW}")
    print(f"  MACD filter: {'OFF' if args.no_macd_filter else 'ON'}")
    print(f"  EMA trend filter: {'ON' if args.require_ema_trend else 'OFF'}")


if __name__ == "__main__":
    main()
