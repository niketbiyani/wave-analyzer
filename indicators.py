"""Technical indicator calculations for wave detection."""

import pandas as pd
import numpy as np


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI using exponential moving average method."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26,
                   signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD line, signal line, and histogram."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_all_indicators(df: pd.DataFrame, rsi_period: int = 14,
                           rsi_ema_period: int = 50, macd_fast: int = 12,
                           macd_slow: int = 26, macd_signal: int = 9,
                           ema_fast: int = 50, ema_slow: int = 100) -> pd.DataFrame:
    """Compute all indicators and add them as columns to the dataframe.

    Expects df to have at minimum a 'close' column. Optionally 'high' and 'low'.
    """
    df = df.copy()

    # RSI
    df["rsi"] = calculate_rsi(df["close"], rsi_period)
    df["rsi_ema"] = calculate_ema(df["rsi"].dropna(), rsi_ema_period)
    # Reindex rsi_ema to match df index (dropna may shift it)
    df["rsi_ema"] = calculate_ema(df["rsi"], rsi_ema_period)

    # MACD
    df["macd"], df["macd_signal"], df["macd_hist"] = calculate_macd(
        df["close"], macd_fast, macd_slow, macd_signal
    )

    # Price EMAs
    df["ema_fast"] = calculate_ema(df["close"], ema_fast)
    df["ema_slow"] = calculate_ema(df["close"], ema_slow)

    # EMA crossover state: True when fast > slow (bullish)
    df["ema_bullish"] = df["ema_fast"] > df["ema_slow"]

    return df
