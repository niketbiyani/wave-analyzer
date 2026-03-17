"""Core wave detection engine.

Strategy logic:
  SHORT setup (bearish continuation):
    1. RSI hits OB zone (>=70) -> mark swing HIGH on price
    2. RSI retraces back toward its 50 EMA
    3. RSI must stay ABOVE 50 during retrace (still bullish momentum fading)
    4. Price breaks ABOVE that swing high -> but wait, user wants SHORTS
       Actually: RSI hits OS (<=30) -> mark swing LOW, RSI retraces to 50 EMA,
       stays below 50, price breaks BELOW swing low -> SHORT entry

  Re-reading the user's strategy carefully:
    - "rsi hits os zone of 30 or below, i will mark the swing low"
    - "wait for rsi to retrace back to touch the 50ema"
    - "then break that swing low" (price breaks below the swing low)
    - "rsi should not go above 50"
    - "for shorts i also expect macd to be below 0"
    - "vice versa for ob zone" (for long/bullish entries)

  So the pattern is:
    SHORT: RSI<=30 -> mark swing low -> RSI retraces up to RSI's 50EMA
           (but RSI stays <50) -> price breaks below swing low -> ENTER SHORT
           + MACD < 0 + EMA bearish crossover preferred

    LONG:  RSI>=70 -> mark swing high -> RSI retraces down to RSI's 50EMA
           (but RSI stays >50) -> price breaks above swing high -> ENTER LONG
           + MACD > 0 + EMA bullish crossover preferred
"""

import pandas as pd
import numpy as np
from typing import Optional
from config import (
    RSI_OB_LEVEL, RSI_OS_LEVEL, RSI_MIDLINE,
    SWING_LOOKBACK, BREAKOUT_TOLERANCE,
)
from models import Direction, SignalPhase, SwingPoint, WaveSetup, Signal


def find_swing_low(df: pd.DataFrame, idx: int, lookback: int = SWING_LOOKBACK) -> Optional[SwingPoint]:
    """Find the swing low around the given index (where RSI hit oversold)."""
    start = max(0, idx - lookback)
    end = min(len(df), idx + lookback + 1)
    window = df.iloc[start:end]

    if window.empty:
        return None

    low_col = "low" if "low" in df.columns else "close"
    min_idx = window[low_col].idxmin()
    min_pos = df.index.get_loc(min_idx)
    price = df[low_col].iloc[min_pos]
    ts = df["timestamp"].iloc[min_pos] if "timestamp" in df.columns else None

    return SwingPoint(price=price, bar_index=min_pos, timestamp=ts, direction=Direction.SHORT)


def find_swing_high(df: pd.DataFrame, idx: int, lookback: int = SWING_LOOKBACK) -> Optional[SwingPoint]:
    """Find the swing high around the given index (where RSI hit overbought)."""
    start = max(0, idx - lookback)
    end = min(len(df), idx + lookback + 1)
    window = df.iloc[start:end]

    if window.empty:
        return None

    high_col = "high" if "high" in df.columns else "close"
    max_idx = window[high_col].idxmax()
    max_pos = df.index.get_loc(max_idx)
    price = df[high_col].iloc[max_pos]
    ts = df["timestamp"].iloc[max_pos] if "timestamp" in df.columns else None

    return SwingPoint(price=price, bar_index=max_pos, timestamp=ts, direction=Direction.LONG)


def detect_waves(df: pd.DataFrame, timeframe: str = "") -> list[Signal]:
    """Scan a dataframe with computed indicators and detect wave setups.

    Args:
        df: DataFrame with columns: close, rsi, rsi_ema, macd, ema_fast, ema_slow.
            Optionally: high, low, timestamp.
        timeframe: Label for the timeframe (e.g. "1m", "5s").

    Returns:
        List of Signal objects for detected wave breakouts.
    """
    signals: list[Signal] = []
    active_setups: list[WaveSetup] = []

    for i in range(1, len(df)):
        rsi = df["rsi"].iloc[i]
        rsi_prev = df["rsi"].iloc[i - 1]
        rsi_ema = df["rsi_ema"].iloc[i]
        close = df["close"].iloc[i]
        low = df["low"].iloc[i] if "low" in df.columns else close
        high = df["high"].iloc[i] if "high" in df.columns else close
        macd = df["macd"].iloc[i]
        ema_fast = df["ema_fast"].iloc[i]
        ema_slow = df["ema_slow"].iloc[i]

        if pd.isna(rsi) or pd.isna(rsi_ema):
            continue

        # --- Detect new setups ---

        # SHORT setup: RSI just entered OS zone
        if rsi <= RSI_OS_LEVEL and rsi_prev > RSI_OS_LEVEL:
            swing = find_swing_low(df, i)
            if swing:
                setup = WaveSetup(
                    direction=Direction.SHORT,
                    phase=SignalPhase.SWING_MARKED,
                    swing_point=swing,
                    rsi_extreme=rsi,
                    rsi_extreme_bar=i,
                )
                active_setups.append(setup)

        # LONG setup: RSI just entered OB zone
        if rsi >= RSI_OB_LEVEL and rsi_prev < RSI_OB_LEVEL:
            swing = find_swing_high(df, i)
            if swing:
                setup = WaveSetup(
                    direction=Direction.LONG,
                    phase=SignalPhase.SWING_MARKED,
                    swing_point=swing,
                    rsi_extreme=rsi,
                    rsi_extreme_bar=i,
                )
                active_setups.append(setup)

        # --- Update existing setups ---
        remaining_setups = []
        for setup in active_setups:
            if setup.invalidated:
                continue

            if setup.direction == Direction.SHORT:
                _update_short_setup(setup, i, rsi, rsi_ema, close, low, macd,
                                    ema_fast, ema_slow, df, signals, timeframe)
            else:
                _update_long_setup(setup, i, rsi, rsi_ema, close, high, macd,
                                   ema_fast, ema_slow, df, signals, timeframe)

            if not setup.invalidated:
                remaining_setups.append(setup)

        active_setups = remaining_setups

    return signals


def _update_short_setup(setup: WaveSetup, i: int, rsi: float, rsi_ema: float,
                        close: float, low: float, macd: float,
                        ema_fast: float, ema_slow: float,
                        df: pd.DataFrame, signals: list[Signal],
                        timeframe: str):
    """Progress a SHORT wave setup through its phases."""

    # Invalidation: RSI crossed above midline
    if rsi > RSI_MIDLINE:
        setup.invalidate("RSI crossed above 50 - momentum lost")
        return

    # Update swing low if price makes a new low while RSI is still oversold
    if setup.phase == SignalPhase.SWING_MARKED and rsi <= RSI_OS_LEVEL:
        if "low" in df.columns:
            if df["low"].iloc[i] < setup.swing_point.price:
                setup.swing_point.price = df["low"].iloc[i]
                setup.swing_point.bar_index = i
                setup.rsi_extreme = min(setup.rsi_extreme, rsi)
        elif close < setup.swing_point.price:
            setup.swing_point.price = close
            setup.swing_point.bar_index = i
            setup.rsi_extreme = min(setup.rsi_extreme, rsi)
        return

    # Phase: RSI left OS zone, now retracing
    if setup.phase == SignalPhase.SWING_MARKED and rsi > RSI_OS_LEVEL:
        setup.phase = SignalPhase.RSI_RETRACING

    # Phase: RSI touched its 50 EMA during retrace
    if setup.phase == SignalPhase.RSI_RETRACING:
        # Check if RSI crossed up through its EMA or is near it
        rsi_prev = df["rsi"].iloc[i - 1] if i > 0 else rsi
        if rsi >= rsi_ema or (rsi_prev < rsi_ema and rsi >= rsi_ema * 0.98):
            setup.phase = SignalPhase.AWAITING_BREAKOUT

    # Phase: Awaiting price breakout below swing low
    if setup.phase == SignalPhase.AWAITING_BREAKOUT:
        swing_price = setup.swing_point.price
        if low <= swing_price - BREAKOUT_TOLERANCE:
            ts = df["timestamp"].iloc[i] if "timestamp" in df.columns else None
            signal = Signal(
                direction=Direction.SHORT,
                entry_price=close,
                swing_price=swing_price,
                bar_index=i,
                timestamp=ts,
                rsi_at_entry=rsi,
                macd_at_entry=macd,
                ema_fast_at_entry=ema_fast,
                ema_slow_at_entry=ema_slow,
                timeframe=timeframe,
            )
            signals.append(signal)
            setup.invalidate("Signal triggered")


def _update_long_setup(setup: WaveSetup, i: int, rsi: float, rsi_ema: float,
                       close: float, high: float, macd: float,
                       ema_fast: float, ema_slow: float,
                       df: pd.DataFrame, signals: list[Signal],
                       timeframe: str):
    """Progress a LONG wave setup through its phases."""

    # Invalidation: RSI crossed below midline
    if rsi < RSI_MIDLINE:
        setup.invalidate("RSI crossed below 50 - momentum lost")
        return

    # Update swing high if price makes a new high while RSI is still overbought
    if setup.phase == SignalPhase.SWING_MARKED and rsi >= RSI_OB_LEVEL:
        if "high" in df.columns:
            if df["high"].iloc[i] > setup.swing_point.price:
                setup.swing_point.price = df["high"].iloc[i]
                setup.swing_point.bar_index = i
                setup.rsi_extreme = max(setup.rsi_extreme, rsi)
        elif close > setup.swing_point.price:
            setup.swing_point.price = close
            setup.swing_point.bar_index = i
            setup.rsi_extreme = max(setup.rsi_extreme, rsi)
        return

    # Phase: RSI left OB zone, now retracing
    if setup.phase == SignalPhase.SWING_MARKED and rsi < RSI_OB_LEVEL:
        setup.phase = SignalPhase.RSI_RETRACING

    # Phase: RSI touched its 50 EMA during retrace
    if setup.phase == SignalPhase.RSI_RETRACING:
        rsi_prev = df["rsi"].iloc[i - 1] if i > 0 else rsi
        if rsi <= rsi_ema or (rsi_prev > rsi_ema and rsi <= rsi_ema * 1.02):
            setup.phase = SignalPhase.AWAITING_BREAKOUT

    # Phase: Awaiting price breakout above swing high
    if setup.phase == SignalPhase.AWAITING_BREAKOUT:
        swing_price = setup.swing_point.price
        if high >= swing_price + BREAKOUT_TOLERANCE:
            ts = df["timestamp"].iloc[i] if "timestamp" in df.columns else None
            signal = Signal(
                direction=Direction.LONG,
                entry_price=close,
                swing_price=swing_price,
                bar_index=i,
                timestamp=ts,
                rsi_at_entry=rsi,
                macd_at_entry=macd,
                ema_fast_at_entry=ema_fast,
                ema_slow_at_entry=ema_slow,
                timeframe=timeframe,
            )
            signals.append(signal)
            setup.invalidate("Signal triggered")
