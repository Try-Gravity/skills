---
name: publisher-setup
description: Set up Gravity ads in an AI chat app from zero to the first ad on screen. Picks the right SDK for the stack (JavaScript, React, React Native, Python, iOS, Android, terminal), plans one placement per surface with the main ad in the chat, wires conversation context and tracking, tests with test ads, and walks the going-live checklist. Use when a publisher asks to add Gravity ads, integrate Gravity, get a first ad showing, or connect a new surface such as a mobile app. Not for advertiser campaigns.
---

# Set up Gravity ads in your AI product

You are helping a publisher go from nothing to a first Gravity ad on screen, in test mode, with a clean path to production. Work in the publisher's codebase, make small reviewable changes, and verify each step.

The docs are the source of truth: https://docs.trygravity.com (add `.md` to any page for plain Markdown; `https://docs.trygravity.com/llms.txt` lists every page). Start from the publisher quickstart (`/ai-platforms/quickstart`) and the SDK page for the stack. Read the page before you write code for a step. Don't fill gaps from memory or from other ad networks. If the docs and this skill differ, follow the docs and tell the user. `reference.md` next to this file has per-stack code, the going-live checklist, and a troubleshooting table.

Related skills in this set: `improve-signals` (what else to send with each request), `optimize-ad-integration` (audit after launch), and `analyze-earnings` (why earnings moved).

## How to think

1. **Ads belong in the conversation.** Plan the main ad for inline in the chat, right after the assistant reply, or directly above the composer, visible and not covered by the input. Other surfaces can come later. Never put the first ad in a place users don't look.
2. **One ad at a time, only Gravity.** When a Gravity ad is on screen, no other ad can be. This includes other networks, house promos, and direct campaigns. Find and remove any existing ad code before you add Gravity (a Guideline, not a style choice).
3. **Use an official SDK.** The Guidelines require serving through a Gravity SDK. A direct HTTP integration needs a signed agreement with Gravity, so don't build one unless the user says they have it.
4. **One placement per surface.** Web chat, iOS app, Android app, and CLI are different surfaces, even when the ad is below the answer in each.
5. **Request on user messages, never on a timer.** Start the ad request in parallel with the model call. Never make the answer wait for the ad. Every user turn sends a request, even when you don't plan to show an ad on that turn.
6. **Send real signals from day one.** The user ID, session ID, and the end user's device signals are cheaper to add now than to retrofit. `improve-signals` has the full list.
7. **Test mode first.** Production waits for Gravity's approval. A production request before approval returns `403` with "publisher_not_approved".

## Safety rules for the agent

- Never print, log, or commit the API key. It goes in the `GRAVITY_API_KEY` environment variable on the server, never in client code or a public repo. If it is already in a repo, tell the user to rotate it (Settings in the dashboard, API Key card).
- The same key reads dashboard data and can create placements. Treat it as a full-access secret. The iOS and Android SDK pages warn that the key ships inside the app package and users can extract it. State this plainly to the user for a native app, and point them to support@trygravity.com if they want a different arrangement. Do not invent one.
- Don't set `production: true` until Gravity has approved the platform and the user asks for that change.
- Don't create, change, or delete placements, through the API or through a dashboard MCP tool. Tell the user to register each placement in the dashboard **Placements** page, then use the slug they get as `placement_id`.
- If a dashboard MCP server is connected, it can act as well as read, with no confirmation step. Use only its reporting tools. Never use a write tool, including ones that create or change placements.
- Never use docs placeholders such as `YOUR_PLACEMENT_ID`, `YOUR_API_KEY`, `YOUR_PIXEL_ID`, or `main` in code you leave behind.
- Propose changes as diffs for the user to review. Don't push or deploy.

## Step-by-step

### 0. Read the project
Find out, from the code, before asking the user:
- Platforms and surfaces: web, iOS, Android, React Native, terminal.
- Where the model is called: a server of theirs (best), or the device calling the model directly.
- The framework (Next.js, Express, FastAPI, SwiftUI, Compose, and so on) and the chat UI component tree.
- Whether users are signed in, signed out, or both.
- Any existing ad code (`adsbygoogle`, `googletag`, other SDKs, house promos). It must go.
- Whether a Gravity SDK, key, or placement already exists.

Ask the user only for what you cannot find: account and approval status, where the ad should appear, and which surface to start with.

### 1. Account and key
The user creates an AI platform account at https://app.trygravity.com/platform/signup, opens **Settings**, and copies the key from the **API Key** card. Set it as `GRAVITY_API_KEY` on the server. Don't ask the user to paste the key into chat. Ask them to set it in their environment, then check only that it exists, never its value.

### 2. Plan and register placements
One placement per surface. Standard types: `above_response`, `below_response`, `inline_response`, `left_response`, `right_response`, `search_result`, `top_page`, `bottom_page`, `left_page`, `right_page`, `center_page`. `below_response` is the most common in chat. `above_response` means above the response and the docs say to use it carefully. No type is documented for "above the composer". The Action ads docs show a composer-adjacent slot registered as `below_response` with the `placement_id` `composer-slot`. If the user wants that position, pick the closest type, use a descriptive `placement_id`, and say it is a judgment call.

Name each placement for its surface, for example `web-chat-below-answer` and `ios-chat-below-answer`. Ask the user to register each one in the dashboard **Placements** page. The slug in the dashboard is the `placement_id` to send in requests. A new placement serves ads after Gravity refreshes its cache, within 5 minutes. Sending a `placement_id` in a request does not create it, and when the account has registered placements, unregistered IDs are dropped with no error.

### 3. Pick the SDK
| Stack | Request ads | Show ads |
|---|---|---|
| Web (Node server) | `@gravity-ai/api` on the server, `gravityContext()` on the client | `@gravity-ai/react` `GravityAd`, or `@gravity-ai/ui` |
| React Native | `@gravity-ai/api` on the server, with `GRAVITY_RN_SPEC_OPTIONS` and `enableFrames: false` | `@gravity-ai/react-native` `GravityAd` |
| Python server | `gravity-sdk` (`get_ads`) | your web client with `GravityAd`, or another official component |
| iOS, macOS, tvOS, watchOS | `GravitySDK` Swift package, `gravity.getAds(...)` on device | `SpecAdView` (SwiftUI) |
| Android | `ai.trygravity:gravity-sdk`, `gravity.getAds(...)` on device | `SpecAd` (Compose) or `GravityAdView` (Views) |
| Terminal app (Node, Bun, Deno) | `@gravity-ai/api`, plus `gravityPixel()` | your own terminal output, with a clear label and a clickable `clickUrl` |

Check the SDK page for the current version and options before you write code. The docs and the SDK READMEs name some iOS components differently, so follow the SDK page for the installed version.

### 4. Wire the request
1. **Client:** call `gravityContext({ sessionId, user: { userId } })` and send the result as `gravity_context` with the chat request. It throws if `userId` is missing. Use a stable anonymous ID for signed-out users, never a shared constant like `"anonymous"`.
2. **Server:** call `gravity.getAds(req, messages, placements)` in parallel with the model call. Pass the raw `messages` array and the real `placement_id`. The SDK reads `gravity_context` from the body, adds the end user's IP, and never throws. The SDKs send the last two messages.
3. **Stream:** don't wait for the ad before you stream the answer. Send the ads with the final event, or when they arrive.
4. **Native apps:** pass `userId`, the end user's IP as `userIP` when a server knows it, and a stable `sessionId` to `getAds()`.

### 5. Wire the display
Render the ad with the official component, in the in-chat position from step 2. Hide the slot when `ads` is empty. Never render more than one Gravity ad at once. Use `ad.clickUrl` for clicks, never `ad.url`. If you write a custom renderer, you must load `ad.impUrl` once when the ad is visible, label it clearly, and set `supportsSpec: false` and `enableFrames: false` on the server. Prefer the official component, which also lets Gravity test designs on your traffic.

### 6. Install the pixel
Put the Gravity pixel snippet (dashboard **Settings**, **Tracking**) in the `<head>` of every page. For a native app that opens ad links in a WebView, also do the in-app browser install on the pixel docs page. In a terminal app, use `gravityPixel()`. Verify that the pixel sends events, not just that the script loads.

### 7. Test in test mode
Test mode is the default. Use `alwaysReturn: true` (JavaScript) to always get a test ad. Check each of these and report what you saw:
- The ad shows in the planned position, in light and dark, wide and narrow, during and after streaming.
- Scrolling it into view fires a request to the impression URL. Clicking it goes through `clickUrl` and redirects.
- The chat still works with Gravity blocked or slow.
- Only one ad is on screen. No other ad code remains.
- `placement_id` is a real registered slug.

### 8. Go live
Gravity must approve the platform before real ads serve. The review needs the URL or app where ads show, and a test login if users must sign in. Test ads keep working during review, and Gravity emails the result. After approval, and only when the user asks, set `production: true` (`production=True` in Python, `production: true` in the constructors for the native SDKs). Walk the checklist in `reference.md` first. Self-serve accounts have 1,000 production requests per UTC day; past that the API returns `429`, and the SDKs return no ads while the chat keeps working.

After launch: check the dashboard for requests, impressions, clicks, and revenue; then run `optimize-ad-integration` and `improve-signals`.

## Output format

Report in plain words:
1. **Summary (3 lines max):** what is done, what is next, what blocks going live.
2. **Plan:** surfaces, placement names and types, SDK per surface.
3. **Changes:** a diff per file, smallest change that works, with a one-line reason each. Don't apply unless asked.
4. **Test results:** each step 7 check as passed, failed, or not checked.
5. **Go-live status:** approval, the checklist, and what the user must do (set the key, request approval, say when to go to production).
6. **Needs Gravity:** approval, a different key arrangement, a direct API agreement, or an ad unit setting. Contact: support@trygravity.com.
7. **Gaps:** anything you couldn't verify.
