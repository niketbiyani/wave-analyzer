"""Data models for wave detection signals."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class SignalPhase(Enum):
    """Tracks where we are in the wave setup."""
    IDLE = "IDLE"                          # No setup in progress
    SWING_MARKED = "SWING_MARKED"          # RSI hit OB/OS, swing point marked
    RSI_RETRACING = "RSI_RETRACING"        # RSI moving back toward 50 EMA
    RSI_TOUCHED_EMA = "RSI_TOUCHED_EMA"    # RSI touched its 50 EMA
    AWAITING_BREAKOUT = "AWAITING_BREAKOUT" # Waiting for price to break swing


@dataclass
class SwingPoint:
    """A marked swing high or low."""
    price: float
    bar_index: int
    timestamp: Optional[datetime] = None
    direction: Optional[Direction] = None  # SHORT setup marks swing HIGH, LONG marks swing LOW


@dataclass
class WaveSetup:
    """Tracks an in-progress wave setup."""
    direction: Direction
    phase: SignalPhase
    swing_point: SwingPoint
    rsi_extreme: float              # The RSI value when OB/OS was hit
    rsi_extreme_bar: int            # Bar index when RSI hit OB/OS
    invalidated: bool = False
    invalidation_reason: str = ""

    def invalidate(self, reason: str):
        self.invalidated = True
        self.invalidation_reason = reason


@dataclass
class Signal:
    """A completed wave signal (entry trigger)."""
    direction: Direction
    entry_price: float
    swing_price: float              # The swing point that was broken
    bar_index: int
    timestamp: Optional[datetime] = None
    rsi_at_entry: float = 0.0
    macd_at_entry: float = 0.0
    ema_fast_at_entry: float = 0.0
    ema_slow_at_entry: float = 0.0
    timeframe: str = ""

    @property
    def trend_aligned(self) -> bool:
        """Check if EMA crossover aligns with direction."""
        if self.direction == Direction.SHORT:
            return self.ema_fast_at_entry < self.ema_slow_at_entry
        return self.ema_fast_at_entry > self.ema_slow_at_entry

    def summary(self) -> str:
        trend = "ALIGNED" if self.trend_aligned else "COUNTER-TREND"
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else f"bar_{self.bar_index}"
        return (
            f"[{self.timeframe}] {self.direction.value} @ {self.entry_price:.2f} | "
            f"Swing: {self.swing_price:.2f} | RSI: {self.rsi_at_entry:.1f} | "
            f"MACD: {self.macd_at_entry:.2f} | EMA trend: {trend} | {ts}"
        )
