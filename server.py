"""Flask web server for the Nifty Wave Analyzer dashboard."""

import os
import json
import tempfile
from datetime import datetime

import numpy as np
from flask import Flask, render_template, request, jsonify

from sample_data import generate_synthetic_data, load_csv
from scanner import scan_timeframe, scan_all_timeframes, filter_signals
from indicators import compute_all_indicators
from config import (
    RSI_PERIOD, RSI_EMA_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    EMA_FAST, EMA_SLOW, TIMEFRAMES,
)

app = Flask(__name__, template_folder="templates", static_folder="static")


def _sanitize(obj):
    """Recursively convert numpy types to native Python types for JSON."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

# Store uploaded data in memory
_data_store = {}


def _df_to_chart_data(df):
    """Convert a DataFrame with indicators to JSON-serializable chart data."""
    records = []
    for _, row in df.iterrows():
        ts = row.get("timestamp")
        if ts is not None:
            if hasattr(ts, "isoformat"):
                time_val = ts.isoformat()
            else:
                time_val = str(ts)
        else:
            time_val = None

        rec = {
            "time": time_val,
            "open": round(float(row["open"]), 2) if "open" in row else None,
            "high": round(float(row["high"]), 2) if "high" in row else None,
            "low": round(float(row["low"]), 2) if "low" in row else None,
            "close": round(float(row["close"]), 2),
        }

        for col in ["rsi", "rsi_ema", "macd", "macd_signal", "macd_hist",
                     "ema_fast", "ema_slow"]:
            if col in row and not _isnan(row[col]):
                rec[col] = round(float(row[col]), 4)

        records.append(rec)
    return records


def _signals_to_json(signals):
    """Convert Signal objects to JSON-serializable dicts."""
    result = []
    for sig in signals:
        ts = sig.timestamp
        if ts is not None and hasattr(ts, "isoformat"):
            time_val = ts.isoformat()
        else:
            time_val = None

        result.append({
            "time": time_val,
            "direction": sig.direction.value,
            "entry_price": round(sig.entry_price, 2),
            "swing_price": round(sig.swing_price, 2),
            "rsi": round(sig.rsi_at_entry, 2),
            "macd": round(sig.macd_at_entry, 2),
            "ema_fast": round(sig.ema_fast_at_entry, 2),
            "ema_slow": round(sig.ema_slow_at_entry, 2),
            "trend_aligned": sig.trend_aligned,
            "bar_index": sig.bar_index,
        })
    return result


def _isnan(val):
    try:
        import math
        return math.isnan(float(val))
    except (ValueError, TypeError):
        return True


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/demo", methods=["GET"])
def demo_data():
    """Load synthetic demo data."""
    df = generate_synthetic_data(n_bars=50000, bar_seconds=1)
    return _process_and_respond(df, source="Synthetic Demo Data")


@app.route("/api/upload", methods=["POST"])
def upload_data():
    """Upload a CSV file."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Save to temp file and load
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as tmp:
        file.save(tmp)
        tmp_path = tmp.name

    try:
        ts_format = request.form.get("timestamp_format", None)
        df = load_csv(tmp_path, date_format=ts_format or None)
        return _process_and_respond(df, source=file.filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        os.unlink(tmp_path)


@app.route("/api/scan", methods=["POST"])
def scan_data():
    """Re-scan stored data with different parameters."""
    data = request.get_json() or {}
    timeframe = data.get("timeframe", "1m")
    require_macd = data.get("require_macd", True)
    require_ema_trend = data.get("require_ema_trend", False)

    if "df_json" not in _data_store:
        return jsonify({"error": "No data loaded. Upload a CSV or load demo first."}), 400

    import pandas as pd
    df = pd.read_json(_data_store["df_json"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    return _process_and_respond(
        df, source=_data_store.get("source", ""),
        timeframes=[timeframe], require_macd=require_macd,
        require_ema_trend=require_ema_trend,
    )


def _process_and_respond(df, source="", timeframes=None,
                         require_macd=True, require_ema_trend=False):
    """Process DataFrame and return full chart + signals response."""
    import pandas as pd
    from scanner import resample_to_timeframe

    # Store raw data for re-scanning
    _data_store["df_json"] = df.to_json()
    _data_store["source"] = source

    if timeframes is None:
        timeframes = TIMEFRAMES

    all_results = {}

    for tf in timeframes:
        try:
            resampled = resample_to_timeframe(df, tf)
            if len(resampled) < 100:
                continue

            df_ind = compute_all_indicators(
                resampled,
                rsi_period=RSI_PERIOD, rsi_ema_period=RSI_EMA_PERIOD,
                macd_fast=MACD_FAST, macd_slow=MACD_SLOW, macd_signal=MACD_SIGNAL,
                ema_fast=EMA_FAST, ema_slow=EMA_SLOW,
            )

            signals = scan_timeframe(resampled, tf)
            filtered = filter_signals(signals, require_macd, require_ema_trend)

            all_results[tf] = {
                "chart_data": _df_to_chart_data(df_ind),
                "signals_all": _signals_to_json(signals),
                "signals_filtered": _signals_to_json(filtered),
                "bar_count": len(resampled),
            }
        except Exception as e:
            all_results[tf] = {"error": str(e)}

    return jsonify(_sanitize({
        "source": source,
        "total_bars": len(df),
        "price_low": round(float(df["close"].min()), 2),
        "price_high": round(float(df["close"].max()), 2),
        "timeframes": all_results,
        "available_timeframes": list(all_results.keys()),
        "settings": {
            "rsi_period": RSI_PERIOD,
            "rsi_ema": RSI_EMA_PERIOD,
            "macd": f"{MACD_FAST}/{MACD_SLOW}/{MACD_SIGNAL}",
            "ema": f"{EMA_FAST}/{EMA_SLOW}",
        }
    }))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    print(f"\n  Wave Analyzer Dashboard → http://{args.host}:{args.port}\n")
    app.run(host=args.host, port=args.port, debug=True)
