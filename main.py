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
from display import print_banner, print_data_summary, print_settings
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

    print_banner()

    # Load data
    if args.file:
        source = args.file
        df = load_csv(args.file, date_format=args.timestamp_format)
    else:
        source = "Synthetic demo data"
        df = generate_synthetic_data(n_bars=10000, bar_seconds=1)

    period_start = str(df["timestamp"].iloc[0]) if "timestamp" in df.columns else "N/A"
    period_end = str(df["timestamp"].iloc[-1]) if "timestamp" in df.columns else "N/A"
    print_data_summary(
        bar_count=len(df),
        price_low=df["close"].min(),
        price_high=df["close"].max(),
        period_start=period_start,
        period_end=period_end,
        source=source,
    )

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

    # Settings summary
    print_settings(
        rsi_period=RSI_PERIOD, rsi_ema=RSI_EMA_PERIOD,
        macd_fast=MACD_FAST, macd_slow=MACD_SLOW, macd_signal=MACD_SIGNAL,
        ema_fast=EMA_FAST, ema_slow=EMA_SLOW,
        macd_filter_on=not args.no_macd_filter,
        ema_filter_on=args.require_ema_trend,
    )


if __name__ == "__main__":
    main()
