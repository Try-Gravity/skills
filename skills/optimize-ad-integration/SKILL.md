---
name: optimize-ad-integration
description: Audit and optimize your own Gravity ad integration. Finds where ads render, checks that the main ad sits in the chat (inline or directly above the composer), finds hidden or duplicate ads, missing user signals, broken impression or click tracking, and units with low CTR that cause ad fatigue, then ranks fixes and proposes code diffs and a simple A/B test. Use when a Gravity publisher asks to review, audit, fix, or improve their ads, CTR, show rate, or earnings from their integration. Not for advertiser campaigns.
---

# Optimize your Gravity ad integration

You are reviewing a publisher's own codebase and, when they give you access, their own Gravity dashboard numbers. The goal: ads that users actually see and click, in the right place, with the signals Gravity needs to pay well. Good ads earn more over time. Ads that get in the way or get ignored earn less over time.

The docs are the source of truth: https://docs.trygravity.com (add `.md` to any page for plain Markdown; `https://docs.trygravity.com/llms.txt` lists every page). Read the linked page before you change code for that step. Don't fill gaps from memory or from other ad networks. `reference.md` next to this file has the grep patterns, check details, the low-CTR math, and code snippets.

Related skills in this set: `publisher-setup` (first integration), `improve-signals` (what to send with each request), and `analyze-earnings` (why earnings moved, market or integration). Hand off to them instead of repeating their work here.

## How to think

1. **The best ads are in the chat.** The Gravity best practices say to keep ads in the conversation, alongside the conversation they relate to, and not outside the chat. Put the main ad inline, right after the assistant reply it relates to, or directly above the composer. Directly above means visible above the input, not underneath it or covered by it. Ads outside the chat (sidebars, top or bottom banners, other pages, preview panes, status lines) come second at best, and the low-CTR rule below applies to them first. They never replace the in-chat ad.
2. **Remove what users ignore.** A unit with consistently low CTR is not free money. It adds ad fatigue to your product and teaches users to skip every ad, including the good one. Turn it off instead of keeping it for extra impressions. "Low" means low compared with your own in-chat units, over enough impressions (see "Judge low CTR" below).
3. **An impression has to be real.** Gravity bills on the impression. An ad behind the input, a toast, a modal or a paywall, or mounted off-screen, is a fake impression, and advertisers pay less for traffic that doesn't perform.
4. **One ad at a time, and only Gravity.** Never show two ads at once. Never show another network's ad, a house promo, or a direct campaign next to a Gravity ad. This is a Gravity Guideline, not a style preference.
5. **Relevance comes from context.** Send every user turn with the raw user text, a stable session ID, a stable user ID, a hashed email when you're allowed, and the real end user's device signals. The less Gravity knows, the less advertisers pay. The `improve-signals` skill covers this in depth.
6. **A fresh ad for each user message, never on a timer.** Request when the user sends a message. Don't rotate or refresh while they read.
7. **Look at it the way a user does.** Check wide and narrow screens, light and dark themes, during and after streaming, logged out and signed in. Most rendering bugs only show in one state.
8. **Judge by revenue per user.** CTR, fill rate and CPM are diagnostics. A unit that gets more impressions but pays less per user is a loss. Don't lower relevancy just to make fill look better.
9. **Check what's already there before you recommend anything.** State what the integration already sends and does, and recommend only what's missing.
10. **Changes to live ads go through Gravity.** The Guidelines require Gravity's approval before you change an approved ad format, placement, or ad frequency. Propose changes; don't ship them silently.

## Safety rules for the agent

- Never print, log, or commit the API key. It lives on the server as `GRAVITY_API_KEY`. Flag it if you find it in client code or source control.
- Dashboard calls are read-only (`GET`). Don't create, change, or delete placements, and don't set `production: true`, unless the user asks for that exact change. If a dashboard MCP server is connected, it can act as well as read, with no confirmation step, so use only its reporting tools.
- Never send raw emails or phone numbers to Gravity. Hash them (see `reference.md`). Respect consent signals.
- Propose code as diffs for the user to review. Don't push or deploy.

## Step-by-step audit

### 1. Find the integration
Search the repo for the SDKs and raw API calls (full patterns in `reference.md`):

```bash
rg -n "@gravity-ai/|gravity_sdk|GravitySDK|ai\.trygravity\.sdk|trygravity\.(com|ai)|getAds\(|get_ads\(|gravityContext\(|GravityAd|SpecAdView|SpecAd\(|impUrl|clickUrl"
```

Record: platforms (web, iOS, Android, React Native, CLI), SDK packages and versions (lockfiles), where ads are requested (server route), and where they render (component). If ads are requested with a direct HTTP call to `/api/v1/ad`, note it: direct API use needs a signed agreement with Gravity.

### 2. Map every placement
For each `getAds` / `get_ads` call, list each `{ placement, placement_id }` and follow the returned ad to the component that draws it. For each placement, write down:
- the surface (web chat, iOS chat, sidebar, CLI, and so on);
- where it renders: **inline** (after the assistant reply), **above composer**, or **outside the chat**;
- whether the `placement_id` is a real registered slug. Docs placeholders like `YOUR_PLACEMENT_ID` or `main` are bugs, and unregistered IDs are silently dropped when the account has registered placements;
- whether the same `placement_id` is reused across different surfaces (it shouldn't be);
- whether the code requests placements it never renders (requested but not shown hurts show rate).

No placement type is documented for "above the composer". The standard types are `above_response`, `below_response`, `inline_response`, `left_response`, `right_response`, `search_result`, and the `*_page` types. The Action ads docs show a slot near the composer registered as `below_response` with a descriptive `placement_id` (`composer-slot`). Pick the closest standard type, give the placement a descriptive `placement_id`, and say in the report that the type is a judgment call. Changing an approved placement needs Gravity's approval.

Flag the integration if its main placement is outside the chat, or if it has no in-chat placement at all. Check by reading the layout, not by trusting names.

### 3. Check signals on every request
On the client, find `gravityContext(...)`; on the server, find what reaches `getAds(req, ...)`. Check:
- **Every user turn sends a request**, including turns where you don't plan to show an ad, with the **raw user text** in `messages`, not a summary, a rewritten query, or fixed text. Redact secrets.
- **Recent context:** short turns like "yes" or "more" are hard to match alone. The docs ask for the recent messages, not only the last one. The official SDKs send only the last two messages, and the docs describe no option to change that (check the SDK page for your version). Pass the real conversation array to `getAds` and let the SDK trim it. If a product needs more context than two messages, tell the user to ask Gravity at support@trygravity.com. Do not hand-roll direct API calls to get around the SDK: direct API use needs a signed agreement.
- **Stable `sessionId`** per conversation (or the Gravity pixel on the page).
- **Stable `user.userId` for everyone**, including logged-out users: use a stable anonymous install or device ID, never a shared constant.
- **Hashed email** (`hashPii()` on the client, or SHA-256 of the trimmed, lowercased email) when privacy rules allow.
- **Device signals of the real user:** `ip`, `ua`, `device_type`, `os`. A server must forward `gravity_context` from the client. `device_type` and `os` must be declared: Gravity stops guessing them from the User-Agent on December 1, 2026 (`@gravity-ai/api` 1.3.1+ sets them in `gravityContext()`).
- **The Gravity pixel** is on every page of the website, and in the in-app browser if your app opens ad links in a WebView.

### 4. Check rendering, impressions and clicks
- **Official component?** `GravityAd` (React, React Native), `SpecAdView` (iOS), `SpecAd` (Android). These fire the impression when the ad is visible, route clicks through `clickUrl`, show the label, and let Gravity test designs remotely. `GravityAdView` (iOS and Android) is the plain built-in card without server-rendered designs. A custom renderer gets none of that and can't take part in Gravity's design experiments. The docs and the SDK READMEs name the iOS component differently in places: follow the SDK page for the installed version.
- **Custom renderer:** `supportsSpec: false` and `enableFrames: false` on the server; load `ad.impUrl` once, only when the ad is actually visible; open `ad.clickUrl`, never `ad.url`; show a clear "Sponsored" label.
- **Visibility:** the slot is not under a fixed composer, a toast, a modal, a paywall, or outside the scroll area. An ad can be "in the viewport" and still be covered; check z-index, `position: fixed/sticky`, and the bottom padding of the message list.
- **One ad on screen:** only one Gravity ad visible at a time, and no other ad script or house promo in the same view.
- **Show the ads you win:** the slot mounts when the ad arrives, survives the end of streaming, and isn't dropped when the ad response comes after the text. An empty `ads` array hides the slot cleanly.
- **Complete and readable:** no truncated or clipped copy, readable text in both themes, brand name visible, no placeholder or stretched logo, CTA on its own row (or a link on the brand), one consistent label.
- **Error handling:** if Gravity is blocked, the chat still works and nothing errors for the user.

### 5. Read the numbers (if the user gives access)
Use the Publisher Dashboard API with the user's key from the environment (header `X-API-Key`, base `https://platform.trygravity.com`). If a Gravity dashboard MCP server or plugin is already connected, you can use its read-only reporting tools instead. List the available tools first and use the names you see, because they differ between the dashboard MCP server and plugins. Never call a tool that creates or changes placements.

| Need | Call |
|---|---|
| Daily impressions, clicks, revenue, CPM, CTR | `GET /publisher-dashboard/stats?days=14` |
| Requests, wins, impressions, fill rate, show rate | `GET /publisher-dashboard/activity?days=14` |
| Results per placement, daily | `GET /publisher-dashboard/placements?days=14` |
| Signal and integration checks | `GET /publisher-dashboard/health` |
| Earnings per user, by tag | `GET /publisher-dashboard/user-analytics?days=14&tag=key:value` |
| Device and country mix | `GET /publisher-dashboard/devices`, `GET /publisher-dashboard/geography` |

Definitions (from the docs): fill rate = wins / requests. Show rate = impressions / wins. CTR = clicks / impressions. eCPM = revenue per 1,000 impressions. Quote them in the report.

Read the funnel in order: requests fell then traffic or integration sends fewer requests; fill fell then demand or matching changed; **show rate fell or is low then ads are won but not shown, which points to your rendering**; impressions held but revenue fell then price or clicks moved. Compare equal periods, watch weekends and country mix, and don't redesign on a short dip. If CTR and show rate held and only fill or CPM moved, it is probably the market, not your integration: switch to the `analyze-earnings` skill instead of changing the UI.

### 6. Judge low CTR
For each placement with daily data over at least 14 days:
1. **In-chat bar:** the CTR of your in-chat placements combined (total clicks / total impressions).
2. **Remove:** a unit whose CTR stays **well below your in-chat CTR** for 14+ days, on most days, with enough impressions that the gap is not just noise (formula in `reference.md`).
3. **Test once:** below the in-chat bar but not well below it. Try one redesign or a move into the chat; if it still sits well below, remove it.
4. **Keep:** at or above the in-chat bar.

If there's no in-chat unit, the first fix is to add one, not to judge the others against each other. If a unit to remove carries a big share of revenue, the plan is "move that inventory into the chat, then remove", not "keep it". Removing or moving a placement needs Gravity's approval.

## Checklist

Severity: **H** breaks the Guidelines, billing, or costs money now. **M** costs performance. **L** polish.

| # | Check | Sev |
|---|---|---|
| 1 | Main ad is in the chat: inline after the reply, or directly above (not behind) the composer | H |
| 2 | No unit with consistently low CTR still running | H |
| 3 | One Gravity ad on screen at a time | H |
| 4 | No other network, house, or direct ad in the same view | H |
| 5 | Ad never hidden behind the input, a toast, a modal, a paywall, or off-screen | H |
| 6 | Impression fires once, only when visible; clicks open `clickUrl` | H |
| 7 | Show rate: every won ad that should show, does (no dropped ads, no requested-but-unrendered placements) | H |
| 8 | Every user turn requested, with raw user text and recent turns | H |
| 9 | Stable `sessionId`, stable user ID, hashed email (when allowed) on every request | H |
| 10 | Real end-user `ip`, `ua`, `device_type`, `os` forwarded from the client | H |
| 11 | Ads for logged-out and guest users too, with a stable anonymous ID | M |
| 12 | Gravity pixel on every page, and in the WebView if ads open in-app | M |
| 13 | A fresh ad per user message; no timed rotation; no blank slot left on screen | M |
| 14 | Official SDK component (`GravityAd`, `SpecAdView`, `SpecAd`) on a current version | M |
| 15 | Copy complete, not truncated or clipped; slot width sent (`getPlacementContext`) | M |
| 16 | Brand name visible; no placeholder, glyph, or stretched logo | M |
| 17 | CTA on its own row, or a link on the brand; never a boxed button squeezed onto the same row as the copy | M |
| 18 | One clear, consistent "Sponsored" label, readable in light and dark | M |
| 19 | Native look, but clearly an ad; no auto-rotating carousels of your own | M |
| 20 | CLI ads open on a plain click (a short clickable link), not only on modifier-click | M |
| 21 | Registered placement slugs only; one placement per surface; no docs placeholders | M |
| 22 | API key only on the server; `production: true` only after approval | H |
| 23 | Chat still works when Gravity is blocked or times out | M |

## Fixes, ranked by impact

Fix clear bugs directly. Test only what's uncertain.

1. **Guideline blockers first:** a second ad on screen, another provider's ad next to Gravity, hidden or fake impressions. These put the account at risk, not just revenue.
2. **Move the main ad into the chat**, inline after the reply or directly above the composer.
3. **Remove low-CTR units.** If one carries real revenue, move that inventory into the chat first.
4. **Show the ads you already win:** fix dropped ads, late responses, unrendered placements, and covered slots.
5. **Send the user's text every turn, with recent turns.**
6. **Complete signals:** stable user ID (anonymous for guests), hashed email, real device signals with `device_type` and `os`.
7. **Install the pixel** (and the WebView install).
8. **Rendering polish:** complete copy, CTA on its own row, brand and logo, one label.
9. **Use the official component** so Gravity can test designs on your traffic without code changes.
10. **Serve logged-out users** with a stable anonymous ID.

Two rules are not open to testing: the main ad belongs in the chat, and a unit whose CTR stays well below your in-chat CTR gets removed. You can test *which* in-chat position works best, and you can hold out a small group to measure the effect of a removal.

## Run a simple A/B test

Design tests (layouts, images, CTA styles) are run by Gravity on the official components with no code change. Email support@trygravity.com to start one. For tests you run yourself, such as a placement move:

1. **Get approval** from Gravity for the variant placement (Guidelines).
2. **Register a separate placement** for the variant, so each arm reports on its own `placement_id`.
3. **Assign by user**, with a stable hash of the user ID (for example 50/50). The same user always sees the same arm.
4. **Tag the arm** on every request: `user.tags: { ad_test: "control" }` or `"variant"`. Earnings per user by tag then show in **Audience then Users** and in `GET /publisher-dashboard/user-analytics?tag=ad_test:variant`. Groups under 50 users aren't shown.
5. **Change one thing.** Fix rendering bugs first: a clipped ad isn't a fair test.
6. **Size it:** per arm, impressions about 16 * p * (1 - p) / (p * lift)^2, where p is the current CTR and lift is the smallest change you care about (0.15 for 15%). At 1% CTR and 15% lift that's about 70,000 impressions per arm.
7. **Run at least 7 full days** to cover the weekly cycle.
8. **Primary metric:** earnings per user. Watch CTR and show rate as diagnostics. **Guardrails:** show rate doesn't drop, still one ad on screen, and your product metrics (retention, messages per user) hold.
9. **Decide:** the variant wins when it beats control by at least the lift you sized for, leads on most days, and the guardrails hold. Ship it, retire the losing placement, and plan the next test. Winners wear out over time.

## Hand-offs

- No integration yet, or placements and keys not set up: `publisher-setup`.
- Signals missing or weak (user ID, hashed email, device, consent, context): `improve-signals`.
- Earnings moved and the integration looks fine: `analyze-earnings`.

## Output format

Write one report, in plain words:

1. **Summary (3 lines max):** Is the main ad in the chat? The top three fixes. What you couldn't check.
2. **What's already right:** the signals and practices already in place.
3. **Placements table:**

| Placement (`placement_id`) | Surface | Position (inline / above composer / outside) | Component | Impressions | CTR | Show rate | Keep / Test / Remove | Notes |
|---|---|---|---|---|---|---|---|---|

4. **Findings**, highest severity first. Each one: checklist #, severity, `file:line`, what's wrong, evidence (code, number, or screenshot), the fix.
5. **Suggested diffs:** unified diffs for each code fix, smallest change that works, with a one-line reason. Don't apply them unless the user asks.
6. **Numbers used:** the KPIs with the definitions above, the period, and the source call. Mark every number as measured (from a response) or estimated.
7. **Test plan** (if any): hypothesis, arms, assignment, sample size, duration, primary metric, guardrails.
8. **Needs Gravity:** placement or format changes that need approval, design experiments to request, ad unit settings only Gravity can turn on. Contact: support@trygravity.com.
9. **Gaps:** anything you couldn't verify (no dashboard access, app-only screens, login walls).
