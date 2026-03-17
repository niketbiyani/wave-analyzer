"""Configuration for the Nifty wave detection system."""

# Indicator parameters
RSI_PERIOD = 14
RSI_EMA_PERIOD = 50  # EMA applied on RSI values
RSI_OB_LEVEL = 70    # Overbought threshold
RSI_OS_LEVEL = 30    # Oversold threshold
RSI_MIDLINE = 50     # RSI must not cross this during retrace

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

EMA_FAST = 50
EMA_SLOW = 100

# Supported timeframes (in seconds for sub-minute)
TIMEFRAMES = ["5s", "15s", "1m", "3m"]

# Wave detection parameters
MIN_SWING_BARS = 3        # Minimum bars to confirm a swing point
SWING_LOOKBACK = 5        # Bars to look back/forward for swing detection
BREAKOUT_TOLERANCE = 0.0  # Price must break swing by this amount (0 = exact break)
