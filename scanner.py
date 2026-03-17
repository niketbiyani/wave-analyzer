"""Multi-timeframe wave scanner.

Scans price data across multiple timeframes and detects wave setups.
Can work with both historical CSV data and real-time data feeds.
"""

import pandas as pd
from typing import Optional
from indicators import compute_all_indicators
from wave_detector import detect_waves
from models import Signal, Direction
from config import (
    RSI_PERIOD, RSI_EMA_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    EMA_FAST, EMA_SLOW, TIMEFRAMES,
)


def resample_to_timeframe(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample tick/second data to a higher timeframe.

    Args:
        df: DataFrame with 'timestamp', 'open', 'high', 'low', 'close', 'volume' columns.
        timeframe: Target timeframe string (e.g. "5s", "15s", "1m", "3m").

    Returns:
        Resampled OHLCV DataFrame.
    """
    tf_map = {
        "5s": "5s",
        "15s": "15s",
        "1m": "1min",
        "3m": "3min",
        "5m": "5min",
        "15m": "15min",
    }

    rule = tf_map.get(timeframe, timeframe)
    df = df.copy()

    if "timestamp" in df.columns:
        df = df.set_index("timestamp")

    resampled = df.resample(rule).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()

    resampled = resampled.reset_index()
    resampled = resampled.rename(columns={"index": "timestamp"})
    if resampled.columns[0] != "timestamp":
        # Handle case where reset_index uses the index name
        first_col = resampled.columns[0]
        if first_col != "timestamp" and pd.api.types.is_datetime64_any_dtype(resampled[first_col]):
            resampled = resampled.rename(columns={first_col: "timestamp"})

    return resampled


def scan_timeframe(df: pd.DataFrame, timeframe: str) -> list[Signal]:
    """Run wave detection on a single timeframe.

    Args:
        df: OHLCV DataFrame for this timeframe.
        timeframe: Timeframe label.

    Returns:
        List of detected signals.
    """
    df_indicators = compute_all_indicators(
        df,
        rsi_period=RSI_PERIOD,
        rsi_ema_period=RSI_EMA_PERIOD,
        macd_fast=MACD_FAST,
        macd_slow=MACD_SLOW,
        macd_signal=MACD_SIGNAL,
        ema_fast=EMA_FAST,
        ema_slow=EMA_SLOW,
    )

    return detect_waves(df_indicators, timeframe=timeframe)


def scan_all_timeframes(df: pd.DataFrame,
                        timeframes: Optional[list[str]] = None) -> dict[str, list[Signal]]:
    """Scan across multiple timeframes for wave setups.

    Args:
        df: Base OHLCV DataFrame (should be at the lowest timeframe resolution).
            Must have 'timestamp' as a column with datetime values.
        timeframes: List of timeframes to scan. Defaults to config.TIMEFRAMES.

    Returns:
        Dict mapping timeframe -> list of signals.
    """
    if timeframes is None:
        timeframes = TIMEFRAMES

    results: dict[str, list[Signal]] = {}

    for tf in timeframes:
        resampled = resample_to_timeframe(df, tf)
        if len(resampled) < 100:
            # Not enough data for reliable indicator calculation
            continue
        signals = scan_timeframe(resampled, tf)
        results[tf] = signals

    return results


def filter_signals(signals: list[Signal],
                   require_macd: bool = True,
                   require_ema_trend: bool = False) -> list[Signal]:
    """Filter signals by additional confirmation criteria.

    Args:
        signals: Raw signals from wave detection.
        require_macd: If True, SHORT signals need MACD < 0, LONG need MACD > 0.
        require_ema_trend: If True, require EMA crossover alignment.

    Returns:
        Filtered list of signals.
    """
    filtered = []
    for sig in signals:
        if require_macd:
            if sig.direction == Direction.SHORT and sig.macd_at_entry >= 0:
                continue
            if sig.direction == Direction.LONG and sig.macd_at_entry <= 0:
                continue

        if require_ema_trend and not sig.trend_aligned:
            continue

        filtered.append(sig)

    return filtered


def print_scan_results(results: dict[str, list[Signal]],
                       require_macd: bool = True,
                       require_ema_trend: bool = False):
    """Print scan results in a readable format."""
    total = 0
    for tf, signals in sorted(results.items()):
        filtered = filter_signals(signals, require_macd, require_ema_trend)
        if not filtered:
            continue
        print(f"\n{'='*80}")
        print(f"  Timeframe: {tf} — {len(filtered)} signal(s) "
              f"({len(signals)} raw, {len(signals) - len(filtered)} filtered out)")
        print(f"{'='*80}")
        for sig in filtered:
            marker = " ** TREND ALIGNED **" if sig.trend_aligned else ""
            print(f"  {sig.summary()}{marker}")
            total += 1

    if total == 0:
        print("\nNo signals detected across any timeframe.")
    else:
        print(f"\nTotal: {total} confirmed signal(s)")
