"""Terminal display with colors and box-drawing for wave analyzer output."""

from models import Signal, Direction


# ANSI color codes
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"

    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


# Box-drawing characters
class Box:
    TL = "\u250c"  # top-left
    TR = "\u2510"  # top-right
    BL = "\u2514"  # bottom-left
    BR = "\u2518"  # bottom-right
    H = "\u2500"   # horizontal
    V = "\u2502"   # vertical
    LT = "\u251c"  # left-tee
    RT = "\u2524"  # right-tee
    TT = "\u252c"  # top-tee
    BT = "\u2534"  # bottom-tee
    X = "\u253c"   # cross

    # Double line for headers
    DH = "\u2550"
    DV = "\u2551"
    DTL = "\u2554"
    DTR = "\u2557"
    DBL = "\u255a"
    DBR = "\u255d"
    DLT = "\u2560"
    DRT = "\u2563"


WIDTH = 78


def _hline(left=Box.LT, right=Box.RT, char=Box.H):
    return f"  {left}{char * WIDTH}{right}"


def _dline(left, right, char=Box.DH):
    return f"  {left}{char * WIDTH}{right}"


def _row(text, border=Box.V):
    stripped = _strip_ansi(text)
    pad = WIDTH - len(stripped)
    if pad < 0:
        pad = 0
    return f"  {border} {text}{' ' * (pad - 1)}{border}"


def _strip_ansi(s: str) -> str:
    import re
    return re.sub(r'\033\[[0-9;]*m', '', s)


def _center(text, width=WIDTH - 2):
    stripped = _strip_ansi(text)
    pad = width - len(stripped)
    left = pad // 2
    right = pad - left
    return " " * left + text + " " * right


def print_banner():
    print()
    print(f"  {C.BRIGHT_CYAN}{Box.DTL}{Box.DH * WIDTH}{Box.DTR}{C.RESET}")
    print(f"  {C.BRIGHT_CYAN}{Box.DV}{C.RESET}"
          f"{_center(f'{C.BOLD}{C.BRIGHT_WHITE}NIFTY WAVE ANALYZER{C.RESET}')}"
          f"{C.BRIGHT_CYAN}{Box.DV}{C.RESET}")
    print(f"  {C.BRIGHT_CYAN}{Box.DV}{C.RESET}"
          f"{_center(f'{C.DIM}RSI Wave Continuation Pattern Detector{C.RESET}')}"
          f"{C.BRIGHT_CYAN}{Box.DV}{C.RESET}")
    print(f"  {C.BRIGHT_CYAN}{Box.DBL}{Box.DH * WIDTH}{Box.DBR}{C.RESET}")


def print_data_summary(bar_count: int, price_low: float, price_high: float,
                       period_start: str, period_end: str, source: str):
    print()
    print(f"  {C.DIM}{Box.TL}{Box.H * WIDTH}{Box.TR}{C.RESET}")
    print(_row(f"{C.BOLD}DATA{C.RESET}  {C.DIM}{source}{C.RESET}"))
    print(f"  {C.DIM}{_hline(Box.LT, Box.RT)[2:]}{C.RESET}")
    print(_row(
        f"  {C.DIM}Bars:{C.RESET} {C.BRIGHT_WHITE}{bar_count:,}{C.RESET}"
        f"    {C.DIM}Range:{C.RESET} {C.BRIGHT_WHITE}{price_low:,.2f}{C.RESET}"
        f" {C.DIM}-{C.RESET} {C.BRIGHT_WHITE}{price_high:,.2f}{C.RESET}"
    ))
    print(_row(
        f"  {C.DIM}From:{C.RESET} {C.WHITE}{period_start}{C.RESET}"
        f"    {C.DIM}To:{C.RESET} {C.WHITE}{period_end}{C.RESET}"
    ))
    print(f"  {C.DIM}{Box.BL}{Box.H * WIDTH}{Box.BR}{C.RESET}")


def print_timeframe_header(tf: str, count: int, raw_count: int, filtered_out: int):
    print()
    tf_display = tf.upper()
    badge = f"{C.BOLD}{C.BRIGHT_CYAN} {tf_display} {C.RESET}"

    print(f"  {C.CYAN}{Box.TL}{Box.H * WIDTH}{Box.TR}{C.RESET}")
    stats = (f"{C.BRIGHT_WHITE}{count}{C.RESET} signal{'s' if count != 1 else ''}"
             f"  {C.DIM}({raw_count} detected, {filtered_out} filtered){C.RESET}")
    print(_row(f"{badge} {stats}"))
    print(f"  {C.CYAN}{Box.LT}{Box.H * WIDTH}{Box.RT}{C.RESET}")


def print_signal(sig: Signal, index: int):
    # Direction badge
    if sig.direction == Direction.SHORT:
        dir_badge = f"{C.BOLD}{C.BG_RED}{C.BRIGHT_WHITE} SHORT {C.RESET}"
        dir_color = C.BRIGHT_RED
    else:
        dir_badge = f"{C.BOLD}{C.BG_GREEN}{C.BRIGHT_WHITE}  LONG {C.RESET}"
        dir_color = C.BRIGHT_GREEN

    # Trend alignment indicator
    if sig.trend_aligned:
        trend_icon = f"{C.BRIGHT_GREEN}TREND ALIGNED{C.RESET}"
    else:
        trend_icon = f"{C.BRIGHT_YELLOW}COUNTER-TREND{C.RESET}"

    # Timestamp
    ts = sig.timestamp.strftime("%H:%M:%S") if sig.timestamp else f"bar {sig.bar_index}"
    date = sig.timestamp.strftime("%Y-%m-%d") if sig.timestamp else ""

    # Signal card
    print(_row(f""))
    print(_row(f"  {dir_badge}  {C.BOLD}{C.BRIGHT_WHITE}{sig.entry_price:,.2f}{C.RESET}"
               f"  {C.DIM}@{C.RESET} {C.WHITE}{ts}{C.RESET}"
               f"  {C.DIM}{date}{C.RESET}"
               f"    {trend_icon}"))
    print(_row(f""))

    # Details row
    swing_delta = sig.entry_price - sig.swing_price
    swing_pct = (swing_delta / sig.swing_price) * 100

    # RSI color
    if sig.rsi_at_entry >= 70:
        rsi_color = C.BRIGHT_RED
    elif sig.rsi_at_entry <= 30:
        rsi_color = C.BRIGHT_GREEN
    else:
        rsi_color = C.YELLOW

    # MACD color
    macd_color = C.BRIGHT_RED if sig.macd_at_entry < 0 else C.BRIGHT_GREEN

    print(_row(
        f"  {C.DIM}Swing:{C.RESET} {dir_color}{sig.swing_price:,.2f}{C.RESET}"
        f" {C.DIM}({swing_pct:+.2f}%){C.RESET}"
        f"   {C.DIM}RSI:{C.RESET} {rsi_color}{sig.rsi_at_entry:.1f}{C.RESET}"
        f"   {C.DIM}MACD:{C.RESET} {macd_color}{sig.macd_at_entry:,.2f}{C.RESET}"
    ))

    # EMA info
    ema_status = "BEARISH" if sig.ema_fast_at_entry < sig.ema_slow_at_entry else "BULLISH"
    ema_color = C.BRIGHT_RED if ema_status == "BEARISH" else C.BRIGHT_GREEN
    print(_row(
        f"  {C.DIM}EMA 50:{C.RESET} {C.WHITE}{sig.ema_fast_at_entry:,.2f}{C.RESET}"
        f"   {C.DIM}EMA 100:{C.RESET} {C.WHITE}{sig.ema_slow_at_entry:,.2f}{C.RESET}"
        f"   {C.DIM}Crossover:{C.RESET} {ema_color}{ema_status}{C.RESET}"
    ))


def print_timeframe_footer():
    print(f"  {C.CYAN}{Box.BL}{Box.H * WIDTH}{Box.BR}{C.RESET}")


def print_no_signals():
    print()
    print(f"  {C.DIM}{Box.TL}{Box.H * WIDTH}{Box.TR}{C.RESET}")
    print(_row(_center(f"{C.DIM}No signals detected across any timeframe{C.RESET}")))
    print(f"  {C.DIM}{Box.BL}{Box.H * WIDTH}{Box.BR}{C.RESET}")


def print_total(count: int):
    print()
    if count > 0:
        print(f"  {C.BOLD}{C.BRIGHT_WHITE}Total: {count} confirmed signal{'s' if count != 1 else ''}{C.RESET}")
    print()


def print_settings(rsi_period, rsi_ema, macd_fast, macd_slow, macd_signal,
                   ema_fast, ema_slow, macd_filter_on, ema_filter_on):
    on = f"{C.BRIGHT_GREEN}ON{C.RESET}"
    off = f"{C.DIM}OFF{C.RESET}"

    print(f"  {C.DIM}{Box.TL}{Box.H * WIDTH}{Box.TR}{C.RESET}")
    print(_row(f"{C.BOLD}SETTINGS{C.RESET}"))
    print(f"  {C.DIM}{_hline(Box.LT, Box.RT)[2:]}{C.RESET}")
    print(_row(
        f"  {C.DIM}RSI:{C.RESET} {C.WHITE}{rsi_period}{C.RESET}"
        f"  {C.DIM}RSI EMA:{C.RESET} {C.WHITE}{rsi_ema}{C.RESET}"
        f"  {C.DIM}MACD:{C.RESET} {C.WHITE}{macd_fast}/{macd_slow}/{macd_signal}{C.RESET}"
        f"  {C.DIM}EMA:{C.RESET} {C.WHITE}{ema_fast}/{ema_slow}{C.RESET}"
    ))
    print(_row(
        f"  {C.DIM}MACD filter:{C.RESET} {on if macd_filter_on else off}"
        f"    {C.DIM}EMA trend filter:{C.RESET} {on if ema_filter_on else off}"
    ))
    print(f"  {C.DIM}{Box.BL}{Box.H * WIDTH}{Box.BR}{C.RESET}")
    print()
