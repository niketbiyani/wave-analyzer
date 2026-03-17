"""Generate synthetic Nifty-like data for testing the wave detector.

Also supports loading real data from CSV files.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def load_csv(filepath: str, timestamp_col: str = "timestamp",
             date_format: str = None) -> pd.DataFrame:
    """Load OHLCV data from a CSV file.

    Expected columns: timestamp/date, open, high, low, close, volume.

    Args:
        filepath: Path to the CSV file.
        timestamp_col: Name of the timestamp column.
        date_format: Optional datetime format string for parsing.

    Returns:
        DataFrame with standardized column names.
    """
    df = pd.read_csv(filepath)

    # Normalize column names to lowercase
    df.columns = [c.strip().lower() for c in df.columns]

    # Handle common timestamp column names
    ts_candidates = ["timestamp", "date", "datetime", "time", "date/time"]
    ts_col = None
    for candidate in ts_candidates:
        if candidate in df.columns:
            ts_col = candidate
            break

    if ts_col is None:
        raise ValueError(
            f"Could not find timestamp column. Available columns: {list(df.columns)}"
        )

    df["timestamp"] = pd.to_datetime(df[ts_col], format=date_format)
    if ts_col != "timestamp":
        df = df.drop(columns=[ts_col])

    # Ensure required columns exist
    required = ["open", "high", "low", "close"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    if "volume" not in df.columns:
        df["volume"] = 0

    df = df.sort_values("timestamp").reset_index(drop=True)
    return df[["timestamp", "open", "high", "low", "close", "volume"]]


def generate_synthetic_data(n_bars: int = 5000, base_price: float = 23500.0,
                            volatility: float = 0.0003,
                            start_time: datetime = None,
                            bar_seconds: int = 1) -> pd.DataFrame:
    """Generate synthetic OHLCV data that mimics Nifty 50 intraday behavior.

    Creates data with trends, mean-reversion, and momentum patterns to
    test the wave detector.

    Args:
        n_bars: Number of bars to generate.
        base_price: Starting price level.
        volatility: Per-bar volatility (as fraction of price).
        start_time: Starting timestamp.
        bar_seconds: Seconds per bar (1 for tick-level data).

    Returns:
        OHLCV DataFrame.
    """
    if start_time is None:
        start_time = datetime(2025, 3, 17, 9, 15, 0)

    np.random.seed(42)

    # Generate price path with regime changes
    prices = [base_price]
    regime_length = np.random.randint(100, 500)
    regime_drift = np.random.choice([-1, 1]) * np.random.uniform(0.0001, 0.0005)
    bars_in_regime = 0

    for i in range(1, n_bars):
        bars_in_regime += 1
        if bars_in_regime >= regime_length:
            # Switch regime
            regime_length = np.random.randint(100, 500)
            regime_drift = np.random.choice([-1, 1]) * np.random.uniform(0.0001, 0.0005)
            bars_in_regime = 0

        # Add momentum waves within regimes
        wave_component = np.sin(2 * np.pi * i / np.random.uniform(50, 200)) * volatility * 0.3
        noise = np.random.normal(0, volatility)
        change = regime_drift + wave_component + noise
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)

    prices = np.array(prices)

    # Generate OHLCV from close prices
    spread = prices * volatility * 0.5
    highs = prices + np.abs(np.random.normal(0, spread))
    lows = prices - np.abs(np.random.normal(0, spread))
    opens = np.roll(prices, 1)
    opens[0] = prices[0]

    # Ensure OHLC consistency
    highs = np.maximum(highs, np.maximum(opens, prices))
    lows = np.minimum(lows, np.minimum(opens, prices))

    volumes = np.random.randint(100, 10000, size=n_bars)

    timestamps = [start_time + timedelta(seconds=i * bar_seconds) for i in range(n_bars)]

    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": np.round(opens, 2),
        "high": np.round(highs, 2),
        "low": np.round(lows, 2),
        "close": np.round(prices, 2),
        "volume": volumes,
    })

    return df
