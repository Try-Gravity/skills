---
name: improve-signals
description: Improve the context and signals a publisher sends with each Gravity ad request, so ads match better and advertisers pay more. Audits and fixes conversation messages, session ID, user ID, hashed email and phone, real device signals, consent and privacy strings, age and gender, user tags, model usage, and placement width, and keeps all of it privacy-safe. Use when a Gravity publisher asks to improve ad relevance, CPM, request signals, hashed email, consent, device data, or the Request signals card. Not for advertiser campaigns.
---

# Improve the signals you send to Gravity

You are helping a publisher send Gravity better, more honest information with each ad request. The Gravity best practices put it plainly: the less Gravity knows, the less advertisers pay. Better signals also help Gravity connect ads to advertiser results, which gives advertisers more confidence to pay for the traffic.

Privacy comes first. Every signal here is only worth sending when the user's consent and the law allow it. When a privacy rule and a revenue gain conflict, privacy wins, and you say so in the report.

The docs are the source of truth: https://docs.trygravity.com (add `.md` to any page for plain Markdown; `https://docs.trygravity.com/llms.txt` lists every page). The key pages are Request ads (`/ai-platforms/request-ads`), Contextual ads (`/engine/contextual-ads`), Best practices, and Understand what your users earn you (`/ai-platforms/user-earnings`). Read the page before you change code for a signal. If the docs and this skill differ, follow the docs and tell the user. `reference.md` next to this file has field-by-field detail, search patterns, and code.

Related skills in this set: `publisher-setup` (first integration), `optimize-ad-integration` (rendering, placement, CTR), and `analyze-earnings` (why earnings moved).

## How to think

1. **Real beats rich.** A signal must describe the real end user. A server IP, a made-up User-Agent, a shared user ID, or a summary of the chat is worse than nothing, because Gravity uses these for fraud checks, reports, and matching.
2. **Send what you have, and only what you may.** Don't collect new personal data just for ads. Don't infer age, gender, or email. Don't send an identifier the user's consent state forbids.
3. **Check before you recommend.** State what the code already sends, then recommend only the gaps.
4. **Order by impact and deadline.** Anything with a date goes first. Then the signals every request should carry. Then the optional ones.
5. **Measure with the dashboard, not a guess.** The Request signals card and the health endpoint show the share of requests that carry each signal.
6. **Signals are not a reason to change what users see.** Don't lower `relevancy` to make fill look better, and don't request ads more often to collect more signals. One request per user message.

## Safety rules for the agent

- Never print, log, or commit the API key (`GRAVITY_API_KEY`). It lives on the server.
- Never print real emails, phone numbers, or user IDs in your report. Redact them, and show hashes only as `<hash>`.
- Never send a raw email or phone number to Gravity. Hash on the client or server before the request (see `reference.md`).
- Don't invent user data. If the app doesn't know age or gender, leave them out.
- Propose changes as diffs for the user to review. Don't push or deploy, and don't change consent behavior without the user's say-so.
- Dashboard calls are read-only (`GET`). If a dashboard MCP server is connected, it can also change things with no confirmation step, so use only its reporting tools.

## The signals

| Signal | Field | What good looks like |
|---|---|---|
| Conversation | `messages` | Every user turn is sent, including turns with no ad planned. Raw user text, not a summary. Secrets redacted. The official SDKs send the last two messages. |
| Session | `sessionId` | One stable ID per conversation. If the Gravity pixel is on the page, it can supply one (`gr_sess_...`). |
| User ID | `user.id` (`userId` in the JS SDK) | Stable per user, for guests too (a stable anonymous install or device ID). Never a shared constant, never the email. |
| Hashed email | `user.hashed_email` | SHA-256 of the trimmed, lowercased email. Sent on every request when you have it and privacy rules allow. |
| Hashed phone | `user.hashed_phone` | SHA-256 of the digits-only phone number, when you have it and may share it. |
| Device | `device.ip`, `device.ua`, `device.device_type`, `device.os` | The real end user's values, forwarded from the client. `device_type` and `os` declared, because guessing from the User-Agent ends on December 1, 2026. |
| Consent | `consent` | TCF string, US privacy string, GPC, or GPP, from the CMP or browser, when the user is in a place that needs it. |
| Age, gender | `user.age`, `user.gender` | Only if users told you. Age as a number, a range like `25-34`, or a birth year. Gender as `male`, `female`, or `other`. |
| Tags | `user.tags` | Up to 10 flat tags for your own analytics. `plan` first. Never used for targeting. |
| Model usage | `usage` | One completed model call: model, input and output tokens. Not running totals. |
| Slot size | `placement_context` | The real width of the ad slot, so copy fits without clipping. |

## Step-by-step

### 1. Inventory what is sent today
Find the ad request and the client context (search patterns are in `reference.md`). In test mode, log the request body that reaches Gravity once, with values redacted, and fill in a table: signal, sent or not, where it comes from, and any problem. Do not skip the server-forwarding check: the most common failure is a server that calls Gravity without the end user's `device` values, so Gravity sees the server instead of the user.

### 2. Read the dashboard (if the user gives access)
- **Audience, Request signals** card: the share of requests in the last 7 days that carry messages, a session ID, a user ID, an email hash, a phone hash, a User-Agent, an IP, an OS, a device ID, and an advertising ID. After 500 requests in 7 days, each gets a status: Good, Low, or Missing.
- `GET /publisher-dashboard/health` (header `X-API-Key`, base `https://platform.trygravity.com`): signal and integration checks for the same 7-day window, with `items` that each have `key`, `kind`, `value`, `status`.
- A response header `X-Gravity-Warning` on ad responses means `device_type` or `os` is missing or not recognized. The `Deprecation` and `Sunset` headers appear until both are declared.

If the user hasn't given a key, say the numbers are unchecked. Do not guess shares.

### 3. Fix in this order
1. **Declare `device.device_type` and `device.os`**, and forward real `device.ip` and `device.ua`. Values: `device_type` is `desktop`, `mobile`, or `tablet`; `os` is `ios`, `android`, `macos`, `windows`, `linux`, `chromeos`, or `other`. In the browser, `gravityContext()` from `@gravity-ai/api` 1.3.1 or later sets both. Native apps and CLIs send their real client User-Agent and the user's IP; the SDKs for iOS and Android take the IP through `userIP` on `getAds()`.
2. **A stable user ID for everyone.** Use the account ID when signed in, and a stable anonymous ID kept on the device when signed out.
3. **Send every user turn,** raw text, with the recent messages. Requests for turns where you won't show an ad are still worth sending. Show an ad, and record an impression, only when one is visible.
4. **Hashed email** when you have it and the privacy rules below allow it. Hash on the client with `hashPii()` or on the server with SHA-256.
5. **Consent plumbing.** Pass the consent state through. The browser, iOS, and Android SDKs read CMP consent by default, and iOS and Android also honor the device's tracking limit. Make sure a custom or server integration forwards what the CMP says. Never send identifiers when the rules below say to skip them.
6. **Stable session ID** per conversation, or the Gravity pixel on the page.
7. **Tags and usage** for analytics: `plan` as the first tag, and usage from the previous completed reply.
8. **Age and gender** only if your users already gave them.
9. **Slot width** with `getPlacementContext()` (React) so ad copy fits the real slot.

### 4. Privacy and consent rules
The docs describe these behaviors, so build to them:
- If GDPR applies (`gdprApplies: true`) and there is no valid `tcfString`, Gravity serves contextual-only ads and does not process user identifiers for that request.
- The same happens when `usPrivacy` opts out of sale, or `gpc` is `true`. Browsers with Global Privacy Control send `Sec-GPC: 1`; forward it or set `consent.gpc`.
- `gpp` and `gppSid` carry the IAB Global Privacy Platform string and section IDs. Gravity reads the US sections and an EU TCF section inside `gpp`; if it cannot decode `gpp`, it serves contextual-only ads.
- Users under 18 get no ads unless the account is approved for teen ads.
- Contextual-only ads still serve, so there is no reason to withhold the conversation itself. Withhold only the identifiers.

When consent state blocks identifiers, skip `hashed_email`, `hashed_phone`, and any advertising ID for that request. The engine also handles consent on its side, but do not rely on that as the only control.

### 5. Verify
- Re-log the redacted request in test mode and confirm each fixed signal is present and correct.
- Check an ad response for `X-Gravity-Warning`. It should be gone.
- Wait for fresh traffic, then re-check the Request signals card or `/publisher-dashboard/health`. Each signal's share should rise. Allow time: the window is 7 days.
- Do not promise a revenue number. Better signals tend to help CPM, but the docs do not give a figure and other factors (see `analyze-earnings`) move earnings too.

## Checklist

| # | Check | Sev |
|---|---|---|
| 1 | `device.ip` and `device.ua` are the end user's, not the server's | H |
| 2 | `device.device_type` and `device.os` declared (deadline December 1, 2026) | H |
| 3 | No raw email or phone sent anywhere | H |
| 4 | No identifier sent when consent state forbids it | H |
| 5 | Stable user ID for every user, guests included; no shared constant | H |
| 6 | Every user turn is requested, raw text, secrets redacted | H |
| 7 | Hashed email sent when available and allowed | M |
| 8 | Consent object forwarded from CMP, browser, or device | M |
| 9 | Stable `sessionId` per conversation or the pixel on the page | M |
| 10 | `plan` tag sent; at most 10 tags; full tag map each request | L |
| 11 | `usage` is one call, sent once, from the previous reply | L |
| 12 | Age and gender only when users gave them | L |
| 13 | Slot width sent so copy isn't clipped | L |

## Output format

Write one short report:

1. **Summary (3 lines max):** the biggest gap, the deadline items, and what you couldn't check.
2. **Signal table:** signal, sent today (yes, partly, no), source in the code, Request signals share if known, action.
3. **Findings**, highest severity first: checklist #, `file:line`, what is wrong, evidence, fix.
4. **Suggested diffs** for each fix, smallest change that works. Don't apply unless asked.
5. **Privacy notes:** what you did not send and why.
6. **Verify plan:** what to re-check and when.
7. **Needs Gravity:** anything only Gravity can do, such as sending more than two messages of context through the SDK, or teen-ad approval. Contact: support@trygravity.com.
8. **Gaps:** anything you couldn't verify.
