#!/usr/bin/env python3
"""Compare equal Gravity publisher periods and print the funnel side by side.

Read-only. Calls GET /publisher-dashboard/stats and GET /publisher-dashboard/activity.
Reads the key from GRAVITY_API_KEY. Standard library only.

Usage:
  python3 compare_periods.py [--days 7] [--tz UTC] [--json] [--base-url URL]

Windows are --days long (use a multiple of 7, at most 30), back to back, ending
yesterday: the current window, then four earlier windows. A metric is "steady"
when the current value is inside the min..max of the four earlier windows.
This is a screening aid. Confirm with the placement, country, and device reports.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

BASE = "https://platform.trygravity.com/publisher-dashboard"
EARLIER_WINDOWS = 4


def today_in(tz):
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(tz)).date()
    except Exception:
        if tz.upper() != "UTC":
            print(f"note: unknown time zone {tz!r}, using UTC", file=sys.stderr)
        return datetime.now(timezone.utc).date()


def get(base, path, key, params):
    url = f"{base}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"X-API-Key": key})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        detail = ""
        try:
            detail = json.load(err).get("detail", "")
        except Exception:
            pass
        sys.exit(f"error: GET {path} returned {err.code} {detail}".strip())
    except urllib.error.URLError as err:
        sys.exit(f"error: could not reach {url.split('?')[0]}: {err.reason}")


def window_metrics(base, key, start, end, tz):
    params = {"start_date": start.isoformat(), "end_date": end.isoformat(), "tz": tz}
    stats = get(base, "stats", key, params)
    activity = get(base, "activity", key, params)
    imps = sum(r.get("impressions", 0) for r in stats.get("timeSeries", []))
    clicks = sum(r.get("clicks", 0) for r in stats.get("timeSeries", []))
    revenue = sum(r.get("revenue", 0.0) for r in stats.get("timeSeries", []))
    rows = activity.get("data", [])
    requests = sum(r.get("requests", 0) for r in rows)
    wins = sum(r.get("wins", 0) for r in rows)
    shown = sum(r.get("impressions", 0) for r in rows)

    def ratio(a, b):
        return a / b if b else None

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "requests": requests,
        "wins": wins,
        "impressions": imps,
        "clicks": clicks,
        "revenue": round(revenue, 2),
        "fill_rate": ratio(wins, requests),
        "show_rate": ratio(shown, wins),
        "ctr": ratio(clicks, imps),
        "ecpm": ratio(1000 * revenue, imps),
    }


METRICS = [
    ("requests", "Requests", "count"),
    ("fill_rate", "Fill rate", "pct"),
    ("show_rate", "Show rate", "pct"),
    ("impressions", "Impressions", "count"),
    ("ctr", "CTR", "pct2"),
    ("ecpm", "eCPM ($)", "money"),
    ("revenue", "Revenue ($)", "money"),
]


def fmt(value, kind):
    if value is None:
        return "n/a"
    if kind == "count":
        return f"{value:,.0f}"
    if kind == "pct":
        return f"{value * 100:.1f}%"
    if kind == "pct2":
        return f"{value * 100:.2f}%"
    return f"{value:,.2f}"


def delta(cur, prev, kind):
    if cur is None or prev is None:
        return "n/a"
    if kind in ("pct", "pct2"):
        return f"{(cur - prev) * 100:+.1f} pts"
    if prev == 0:
        return "n/a"
    return f"{(cur - prev) / prev * 100:+.1f}%"


def position(cur, earlier):
    vals = [w for w in earlier if w is not None]
    if cur is None or len(vals) < 2:
        return "thin history"
    if cur < min(vals):
        return "down"
    if cur > max(vals):
        return "up"
    return "steady"


def hint(pos):
    if pos["requests"] == "down":
        return "Requests are below normal: traffic or the integration. Check deploys, errors, and 401, 403, 429."
    if pos["show_rate"] == "down":
        return "Show rate is below normal: ads are won but not shown. Look at rendering (optimize-ad-integration)."
    if pos["ctr"] == "down":
        return "CTR is below normal with show rate steady: creative, position, fatigue, or mix. Break down by placement."
    steady_core = all(pos[k] in ("steady", "up") for k in ("requests", "show_rate", "ctr"))
    if steady_core and (pos["fill_rate"] == "down" or pos["ecpm"] == "down"):
        return ("Requests, show rate, and CTR are in their normal range while fill or eCPM is below it: "
                "consistent with a market shift. Check country and device mix, and confirm it holds across placements.")
    if steady_core and pos["revenue"] == "up":
        return "Revenue is above normal with a steady funnel: probably the market or better signals. Do not credit a UI change without evidence."
    if all(v in ("steady", "thin history") for v in pos.values()):
        return "Everything is inside its normal range."
    return "Mixed or unclear. Split the change by component and by placement, country, and device."


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7, help="window length, 1 to 30 (default 7)")
    ap.add_argument("--tz", default="UTC", help="IANA time zone for daily buckets (default UTC)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    ap.add_argument("--base-url", default=BASE, help=argparse.SUPPRESS)
    args = ap.parse_args()

    if not 1 <= args.days <= 30:
        sys.exit("error: --days must be 1 to 30 (the activity endpoint allows up to 30 days per call)")
    key = os.environ.get("GRAVITY_API_KEY")
    if not key:
        sys.exit("error: set GRAVITY_API_KEY in your environment")
    if args.days % 7:
        print("note: use a multiple of 7 days so every window covers the same weekdays", file=sys.stderr)

    end = today_in(args.tz) - timedelta(days=1)  # last complete day
    windows = []
    for i in range(EARLIER_WINDOWS + 1):
        w_end = end - timedelta(days=i * args.days)
        w_start = w_end - timedelta(days=args.days - 1)
        windows.append(window_metrics(args.base_url, key, w_start, w_end, args.tz))
    current, previous, earlier = windows[0], windows[1], windows[1:]

    pos = {k: position(current[k], [w[k] for w in earlier]) for k, _, _ in METRICS}
    result = {"tz": args.tz, "days": args.days, "current": current, "previous": previous,
              "earlier_windows": earlier, "position": pos, "hint": hint(pos)}
    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"Current {current['start']} to {current['end']} vs previous {previous['start']} to {previous['end']} ({args.tz})")
    print(f"Normal range = min..max of the {EARLIER_WINDOWS} earlier windows.\n")
    print(f"{'Metric':<14}{'Current':>14}{'Previous':>14}{'Change':>12}  Position")
    for k, label, kind in METRICS:
        print(f"{label:<14}{fmt(current[k], kind):>14}{fmt(previous[k], kind):>14}"
              f"{delta(current[k], previous[k], kind):>12}  {pos[k]}")
    print(f"\nHint: {result['hint']}")
    print("This is a screening aid, not a verdict. Confirm with placements, countries, and devices.")


if __name__ == "__main__":
    main()
