# Reference: analyze your Gravity earnings

Details for `SKILL.md`. Endpoint names and fields come from the public Publisher Dashboard API reference at https://docs.trygravity.com/api-reference/publisher/overview. Read it for the current range limits.

## 1. Calls

Base URL `https://platform.trygravity.com`, header `X-API-Key: $GRAVITY_API_KEY`. Reporting endpoints are read-only. About 100 requests per second per client IP; `429` carries `Retry-After`. Most reports take `days`, or `start_date` and `end_date` (`YYYY-MM-DD`; a date range replaces `days`), plus `tz` (an IANA time zone, default `UTC`).

| Need | Call | Key fields |
|---|---|---|
| Account, payout model | `GET /publisher-dashboard/info` | `name`, `payout_model`, lifetime totals |
| Daily earnings | `GET /publisher-dashboard/stats` | `totalImpressions`, `totalClicks`, `totalRevenue`, `avgCpm`, `timeSeries[]` with `date`, `impressions`, `clicks`, `revenue`, `cpm`, `ctr` |
| Funnel | `GET /publisher-dashboard/activity` (1 to 30 days) | `data[]` with `date`, `requests`, `wins`, `impressions`; `fill_rate`, `show_rate`, bot request fields |
| By placement | `GET /publisher-dashboard/placements` | `placements[]` with totals and `daily[]` |
| By country | `GET /publisher-dashboard/geography` | `countries[]` with `country_code`, impressions, clicks, revenue |
| Top countries by traffic | `GET /publisher-dashboard/countries` | `requests`, `ads_served`, `unique_users`, `pct_requests` |
| By device type | `GET /publisher-dashboard/devices` | `devices[]` with `device_type` |
| Revenue per user | `GET /publisher-dashboard/user-analytics` | `summary`, `daily`, `breakdowns`, `message_coverage`, `too_few_users` |
| Active users and cohorts | `GET /publisher-dashboard/arpu-trend` | `daily[]`, `cohorts[]` |
| Signal and integration checks | `GET /publisher-dashboard/health` | `items[]` (`key`, `kind`, `value`, `status`) |

`user-analytics` filters: `country`, `segment` (`new`, `returning`), `usage`, `tag=key:value`, `model`, and `rows` with `columns` for a matrix. Every group has at least 50 users.

Units: `stats` reports `avgCtr` and `ctr` as percent points (0.48 means 0.48%), while the placements, devices, and geography examples show `ctr` as a ratio (0.005 means 0.5%). Always compute CTR as clicks / impressions.

Errors: `401` bad or missing key; `400` bad parameter or too long a range; `404` route not on your account (for example the user value API is off); `422` invalid parameter; `429` rate limit.

## 2. The comparison method

Goal: decide whether a metric moved outside its normal range, without inventing thresholds.

1. Choose a window length N days, a multiple of 7 (7 is the default). Use complete days. Leave out today.
2. Build the **current** window and four earlier windows of the same length, back to back, so each covers the same weekdays. The most recent earlier window is the **previous** one.
3. For each window compute: requests, wins, impressions, clicks, revenue, `fill = wins / requests`, `show = impressions / wins`, `ctr = clicks / impressions`, `ecpm = 1000 * revenue / impressions`.
4. For each metric, the **normal range** is the minimum and maximum of the four earlier windows. The metric is **steady** if the current value is inside that range, **up** if above, **down** if below. Four weekly windows give a rough sense of normal; if there is less history, say the range is thin.
5. Report the change against the previous window too, as a percent or percentage points.
6. Watch for holidays inside any window; flag them.

This is a screening aid, not a statistical test. Small volumes are noisy: if a window has only a few hundred impressions, say that CTR and eCPM are too noisy to read.

`scripts/compare_periods.py` implements steps 1 to 5:

```bash
export GRAVITY_API_KEY=...        # set in your shell; never paste the key into chat
python3 scripts/compare_periods.py --days 7 --tz America/Chicago
python3 scripts/compare_periods.py --days 14 --json
```

It reads `GRAVITY_API_KEY` from the environment, calls only `GET /stats` and `GET /activity`, and prints a table plus a hint line. The hint follows the decision table in `SKILL.md`. It is a starting point; confirm with the placement, country, and device breakdowns.

## 3. Reading each pattern

| Pattern | Reading |
|---|---|
| Requests, CTR, and show rate steady; fill and eCPM both down | Demand-side. Consistent with a market shift. Check country and topic mix first. |
| Requests, CTR, and show rate steady; eCPM down only | Price per impression moved. Consistent with a market shift, or a country or device mix shift. |
| Fill down, everything else steady, on one day only | A one-day blip. Don't act. Re-check next week. |
| Show rate down | Not the market. Ads won but not shown. Rendering or component. |
| CTR down, show rate steady | Creative, position, fatigue, or mix. Break down by placement. |
| Requests down | Traffic or integration. Check deploys and errors. |
| Revenue down 100% | Key, approval, or limit: look for `401`, `403` "publisher_not_approved", `429` `daily_request_limit_reached`. |
| ARPU down, requests per user up | More messages from low-value users. Break down `user-analytics` by country and new versus returning. |

## 4. Plain-language phrases

- "Your requests, CTR, and show rate are in their normal range. Fill and eCPM fell. That is consistent with a market shift. I can't see advertiser budgets from your account, so I can't confirm it."
- "Show rate fell from 86% to 71% while fill held. That points to ads being won and not shown. Check rendering."
- "This looks like a normal weekend pattern. Compare Monday to Monday."
- "I don't expect a number for when it recovers. Re-check after two full weeks."
