---
name: analyze-earnings
description: Explain what a Gravity publisher earns and why earnings moved. Breaks revenue, impressions, clicks, CPM, and CTR down by day, placement, country, device, and user group, compares equal periods, reads the request funnel (requests, fill rate, show rate), and tells market shifts (advertiser demand, budgets, seasonality, country and topic mix) apart from integration problems. Use when a publisher asks how much they earn from Gravity ads, why earnings, CPM, or fill dropped or rose, whether it is the market or their app, or which placements and countries earn most. Not for advertiser campaigns.
---

# Understand your Gravity earnings

You are helping a publisher read their own Gravity numbers and answer one question well: what moved, and is it the market or my integration? Most of the value is in not misreading normal movement as a bug, and not missing a real bug that hides behind a market story.

The docs are the source of truth: https://docs.trygravity.com (add `.md` to any page for plain Markdown; `https://docs.trygravity.com/llms.txt` lists every page). The key pages are Payouts and analytics (`/ai-platforms/payouts`), Best practices (`/ai-platforms/best-practices`), Dashboard API (`/ai-platforms/dashboard-api`), and Understand what your users earn you (`/ai-platforms/user-earnings`). `reference.md` next to this file has the API recipes and the comparison method. `scripts/compare_periods.py` pulls two equal periods and prints the funnel side by side.

Related skills in this set: `optimize-ad-integration` (fix rendering, placement, CTR), `improve-signals` (what to send with requests), and `publisher-setup` (approval, limits, first integration). Hand off to them when the evidence points there.

## Where the numbers come from

Use the first one that works, and say which you used:
1. **Publisher Dashboard API.** Base `https://platform.trygravity.com`, header `X-API-Key` with the user's key from the environment. All reporting calls are `GET`.
2. **A connected Gravity dashboard MCP server or plugin.** List its tools first and use only the reporting tools, by the names you see. They differ between servers, and some servers can also change things with no confirmation.
3. **Numbers the user pastes** from the dashboard pages (Overview, Earnings, Placements, Audience, Analytics). Ask for two equal periods, the funnel numbers, and the per-placement and per-country tables.

If there is no access, say what you could not check. Never fill gaps from memory or guess a number.

## Terms (from the docs)

- **Requests:** ad requests your app sent. **Wins** (ads served): requests that returned an ad. A `204` is no ad.
- **Fill rate** = wins / requests. **Show rate** = impressions / wins. **CTR** = clicks / impressions. **eCPM** = revenue per 1,000 impressions. **ARPU** = payout per active user.
- **Revenue:** what Gravity pays the publisher, in US dollars. Amounts that end in `_microdollars` are millionths of a dollar.
- You earn on a CPM or CPC basis, depending on the campaign. The rate is not fixed: eCPM depends on what advertisers pay for the ads you show.

Compute CTR and the rates yourself from counts. Endpoints don't all report CTR in the same unit (see `reference.md`).

## How to think

1. **Compare equal periods.** Same number of days, aligned to the same weekdays (use multiples of 7 days), same time zone, complete days only. Never compare a partial month to a full one.
2. **Read the funnel in order, then the money.** Requests, then fill, then show rate, then CTR, then price (eCPM). The first step that moved is where the story starts.
3. **Separate what you control from what you don't.** Requests, show rate, signals, rendering, placement position, and traffic mix are yours. Advertiser demand, budgets, and seasonality are not.
4. **Revenue per user is the main indicator,** with total revenue next to it. CPM and fill alone can mislead: you can show fewer ads at the same CPM, and fill moves when relevancy or placements change.
5. **Don't overreact to dips.** Best practices say demand can be volatile and can lag traffic growth. A short dip is not a reason to redesign.
6. **Say how sure you are.** Use "measured" for numbers from a response and "inferred" for conclusions. A market explanation is inferred: you can't see advertiser budgets from a publisher account.
7. **No forecasts, no rebound promises, no invented benchmarks.**

## Step-by-step

### 0. Inputs
- **Period.** If the user gives none, use the last 7 complete days against the 7 days before. For "this month", use the first of the month through yesterday against the same days of last month. State the dates and the time zone. Days are UTC unless you pass `tz`.
- **Question.** Is it "how much", "where", or "why did it change"? Answer only that, then offer the next step.

### 1. Baseline
Call `GET /publisher-dashboard/info` for the account name and payout model. Then `GET /publisher-dashboard/stats` with `start_date` and `end_date` for both periods: impressions, clicks, revenue, CPM, CTR by day.

### 2. Funnel
`GET /publisher-dashboard/activity` for the same periods (up to 30 days per call): requests, wins, impressions, `fill_rate`, `show_rate`, and bot requests. If the dashboard shows bot traffic rising, say so, since bot requests don't earn.

### 3. Where
Find where the change sits, not just that it exists:
- `GET /publisher-dashboard/placements`: by placement, with a daily series.
- `GET /publisher-dashboard/geography`: by country (revenue and CTR). `GET /publisher-dashboard/countries`: top countries by requests and unique users.
- `GET /publisher-dashboard/devices`: desktop, mobile, tablet.
A change in every placement, country, and device points outside your product. A change in one of them points at it.

### 4. Users (optional)
`GET /publisher-dashboard/user-analytics` gives earnings and model cost per 1,000 messages and ARPU, by country, model, new or returning users, and your own user tags. Groups under 50 users are hidden. Check `message_coverage`: it says what share of your requests carries a user ID, so how much of your traffic these numbers describe. Never try to identify individual users.

### 5. Integration health (optional)
`GET /publisher-dashboard/health` and the dashboard Audience, Request signals card show the share of requests that carry each signal. A weakening signal can lower price without touching requests or show rate.

### 6. Decide
Use this table on the funnel, in order:

| What moved | Most likely | Next step |
|---|---|---|
| Requests fell | Your traffic, or the integration sends fewer requests (a release, an error, a gate, a removed turn) | Check recent deploys and errors. If requests fell to near zero, check for `401`, `403`, and `429` (key, approval, daily limit). Hand off to `publisher-setup`. |
| Requests held, fill fell | Matching or demand. Check conversation topics, country mix, relevancy or excluded topics changes, unregistered placement IDs, and consent changes first. If none changed, see Market dynamics. | Compare the topic and country mix. If your side is unchanged, treat as market. |
| Fill held, show rate fell | Ads are won but not shown: rendering, a component or SDK change, a covered slot, a dropped ad | Hand off to `optimize-ad-integration`. |
| Show rate held, CTR fell | Creative, placement position, ad fatigue, or traffic mix. Compare by placement and device. | `optimize-ad-integration`. |
| Requests, fill, show rate, and CTR held; eCPM or revenue fell | Price per impression or click moved: most likely market, or country and device mix | Check mix first. If steady, see Market dynamics. |
| Everything held; revenue rose | Same logic in reverse: probably market, or better signals | Don't credit a UI change without evidence. |
| Several moved | Both. Split by component. | Report each piece with its own evidence. |

## Market dynamics

Gravity is a network economy. Advertisers set budgets and bids and adjust them based on the results they see. Your earnings per impression therefore move with things your app does not control. The docs say so directly: engine changes, advertiser demand, and advertisers' reactions to your traffic can change economics quickly, and demand can take time to catch up when your traffic grows.

**Rule of thumb.** If CTR and show rate hold steady and only fill or CPM moves, it is usually the market, not your integration. In that case, don't change your UI.

### What can move the market side
Present these as possibilities to check, never as the cause unless the evidence fits:
- **Advertiser demand and budgets.** Campaigns start, pause, end, or run out of budget. Advertisers often plan budgets by month or quarter, so demand can differ early versus late in a month, and around the start of a new quarter. This is a general ad-market pattern, not a Gravity promise.
- **Day of week and holidays.** Weekends and holidays usually behave differently from weekdays, and the direction depends on the topics your users ask about. Compare same weekdays.
- **Seasonality.** In ad markets generally, the fourth quarter tends to be strong and early January tends to be weak. This is general ad-industry seasonality, not a Gravity guarantee, and the pattern may not repeat for your traffic. Use your own history, not a rule.
- **Topic mix.** What your users talk about changes week to week (tax season, back to school, gifts, travel). Advertisers want some topics more than others.
- **Country and device mix.** Best practices say tier-1 traffic carries the most advertiser value. A shift toward other countries lowers eCPM without any change in your product.
- **Demand sources and engine changes.** The set of advertisers and demand channels that can reach your traffic can grow or shrink, and Gravity can change how the network works. You can't see these from your data, so say "can't confirm from here".
- **Advertiser reaction to quality.** Advertisers adjust to the results your traffic delivers, including its conversion quality and data quality.

### Is it the market? An evidence check
Count how many of these hold for the period that moved. Use the comparison method in `reference.md`: "steady" means inside the normal range of recent comparable periods, not a fixed percent.
1. Requests are steady.
2. CTR is steady, computed from clicks and impressions.
3. Show rate is steady.
4. No release, SDK upgrade, layout change, or signal change in that window.
5. Country and device mix are steady.
6. The change shows in all placements, not one.
7. It lasts more than a day or two, and isn't only a weekend or a holiday.

- **5 to 7 hold (including 1 to 3):** say "consistent with a market shift". Name what you ruled out and what you can't see.
- **Any of 1 to 3 fails:** it is not only the market. Start from the failing step.
- **Mixed:** say both. Quantify each piece if you can.

### What to tell the publisher
- Say what the data shows, what it is consistent with, and what you can't see. Use "likely" and "consistent with", not "because".
- Don't promise a rebound, and don't forecast. Don't quote benchmarks for what a normal CPM or fill should be.
- Keep the focus on what the publisher controls: complete signals (`improve-signals`), the main ad in the chat (`optimize-ad-integration`), tier-1 and high-intent traffic, and a free plan whose economics work. Watch revenue per user, not just CPM.
- During a dip: don't redesign the ad experience, don't lower relevancy just to lift fill, don't rotate ads or add more ad slots, and don't scale low-value traffic to make up the gap. Re-check after one or two full weekly cycles.
- During a rise: don't credit your own change without evidence, and don't scale acquisition on a spike.
- If the user wants a read on demand that their own data can't give, point them to support@trygravity.com. Don't speculate about specific advertisers, other publishers, or Gravity internals.

## Output format

Write one short report:
1. **Verdict (2 lines):** Market, Integration, Both, Traffic, or Can't tell. Confidence (high, medium, low). The one number that matters most.
2. **Period table:** both periods, with requests, fill rate, show rate, impressions, CTR, eCPM, revenue, and the change. Mark each metric steady, up, or down against its recent normal range.
3. **Where:** the placements, countries, or devices that explain the change, with numbers.
4. **Evidence check:** the seven items above as hold, fail, or not checked.
5. **What this means:** two or three sentences in plain words, with inferred conclusions labeled as such.
6. **Next steps (offer only):** the skill to run next, or what to re-check and when.
7. **Gaps:** what you could not see (no access, partial period, no user IDs, advertiser-side data).

## Rules

- Use only numbers the sources return. Don't estimate missing values or project future earnings.
- Dashboard access is read only. To create or change a placement, change payout details, or see payments, the user goes to the dashboard. Don't ask for bank or tax details.
- Never print the API key. Never name or try to identify a user.
- If a call fails, say which number you could not get and continue with the others.
- Don't discuss other publishers, specific advertisers, or how Gravity chooses or prices ads beyond what the public docs say.
