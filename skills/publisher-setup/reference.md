# Reference: set up Gravity ads

Details for `SKILL.md`. Every name here comes from the public docs at https://docs.trygravity.com or the published SDK packages. If your SDK version differs, read its docs page first.

## 1. Code per stack

**Web client (JavaScript or React).**
```ts
import { gravityContext } from '@gravity-ai/api';

const gravity_context = gravityContext({
  sessionId: chatSession.id,         // your conversation ID
  user: { userId: currentUser.id },  // stable ID; a stable anonymous ID for guests
});

await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ messages, gravity_context }),
});
```
`gravityContext()` throws if `user.userId` is missing, and if `sessionId` is missing and the Gravity pixel is not on the page.

**Node server (Express shape).**
```ts
import { Gravity } from '@gravity-ai/api';
const gravity = new Gravity(); // reads GRAVITY_API_KEY; test ads until production: true

app.post('/api/chat', async (req, res) => {
  const { messages } = req.body;
  const adPromise = gravity.getAds(req, messages, [
    { placement: 'below_response', placement_id: 'web-chat-below-answer' },
  ]);
  // stream the model answer first
  const { ads } = await adPromise; // never throws; empty array on failure
  res.write(`data: ${JSON.stringify({ type: 'done', ads })}\n\n`);
  res.end();
});
```

**Show it (React).**
```tsx
import { GravityAd } from '@gravity-ai/react';
{ads[0] && <GravityAd ad={ads[0]} />}
```
`GravityAd` draws the design and the "Sponsored" label, sends the impression when at least half of the ad is visible, and routes clicks through the tracking URL.

**Python server (FastAPI shape).**
```python
from gravity_sdk import Gravity
gravity = Gravity()  # reads GRAVITY_API_KEY

ad_task = asyncio.create_task(
    gravity.get_ads(request, messages, [
        {"placement": "below_response", "placement_id": "web-chat-below-answer"}
    ])
)
# stream the model answer, then:
ad_result = await ad_task
ads = [a.to_dict() for a in ad_result.ads]
```
The Python SDK package is `gravity-sdk` (Python 3.10 or later). Check its docs page for what it forwards from the client context.

**React Native.** On the server:
```ts
import { GRAVITY_RN_SPEC_OPTIONS } from '@gravity-ai/react-native';
const result = await gravity.getAds(req, messages, placements, {
  ...GRAVITY_RN_SPEC_OPTIONS,
  enableFrames: false,
});
```
In the app, `GravityAd` from `@gravity-ai/react-native`, inside `GravityThemeProvider`. Requires `react` 18.2 or later and `react-native` 0.76 or later. In a `FlatList`, pass `isViewable` from `onViewableItemsChanged`.

**iOS (Swift package `https://github.com/Try-Gravity/gravity-swift-sdk`, iOS 15 or later).**
```swift
let gravity = Gravity(apiKey: "<from your own secure config>")
let result = await gravity.getAds(
  messages: messages, sessionId: sessionId, userId: currentUser.id,
  placements: [.belowResponse(id: "ios-chat-below-answer")]
)
if let ad = result.ads.first { SpecAdView(ad: ad, gravity: gravity, sessionId: sessionId) }
```

**Android (`ai.trygravity:gravity-sdk`, Android 7.0 or later).**
```kotlin
val gravity = Gravity(context, apiKey = "<from your own secure config>")
val result = gravity.getAds(
  messages = messages, sessionId = sessionId, userId = currentUser.id,
  placements = listOf(Placement.belowResponse("android-chat-below-answer")),
)
// Compose: SpecAd(...); Views: GravityAdView(...)
```
`getAds()` never throws on iOS and Android. It returns an empty result with `status` `0` on a failure before a response, `204` for no match, and `401` for a key problem.

**Terminal app.** Install `@gravity-ai/api`, start `gravityPixel({ pixelId })` once, call `gravityContext()` with the pixel's visitor and session IDs, then `gravity.getAds(...)`. Print the ad with a clear label and a short link that opens on a plain click. See the terminal SDK page.

## 2. Test-mode behavior

- The SDKs request test ads until `production` is set. Test ads are not billed and earn nothing.
- `alwaysReturn: true` (JavaScript) returns a test ad instead of an empty result. Gravity ignores it in production.
- An empty `ads` array is normal: no campaign matched. Hide the slot. A lower `relevancy` (default `0.2`) admits weaker matches, but don't lower it only to raise fill.
- Without `GRAVITY_API_KEY`, the JavaScript SDK sends no request and returns an empty array.
- Same ad on every request: still in test mode.
- Impressions not counting: `GravityAd` counts at 50% visible. A custom renderer must load `ad.impUrl` once.

## 3. Going-live checklist

Do each in test mode, start to end:
1. The key is only on the server (`GRAVITY_API_KEY` in production config). Native iOS and Android SDKs keep it in the app by design; see the warning on their SDK pages.
2. Every `placement_id` in code is a registered slug, one per surface. No `YOUR_PLACEMENT_ID` or `main`.
3. The ad shows in the right place on each surface.
4. Impression fires when the ad is visible, once.
5. Click goes through `clickUrl`, which redirects to the advertiser.
6. The pixel is installed and sends events (and the WebView install, if links open in-app).
7. The same `sessionId` for every request in one conversation.
8. Each request carries the real end user's `device.ip` and `device.ua` (plus `device_type` and `os`).
9. Chat and UI keep working with Gravity blocked.
10. Gravity approved the platform.

Then set `production: true`. This is the only code change. After going live: check the dashboard, watch latency (JavaScript SDK timeout 4 seconds, Python 3 seconds, tune on the constructor), and watch the fill rate.

To roll back, set `production: false` on the constructor and deploy. The SDK then requests test ads, and you stop earning revenue. Nothing else changes.

## 4. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Production request returns `403` "publisher_not_approved" | Platform not approved yet. Test ads still work. |
| `429` `daily_request_limit_reached` | Self-serve limit of 1,000 production requests per UTC day. Resets at midnight UTC. |
| No ad for a new placement | Cache refresh takes up to 5 minutes. Or the `placement_id` isn't registered. |
| Placement ignored, no error | Unregistered `placement_id` while the account has registered placements. |
| `401` | Key missing or invalid, or the account is archived. |
| Ad shows as a plain text card in React Native | `GRAVITY_RN_SPEC_OPTIONS` missing on the server. |
| `gravityContext()` throws | `userId` missing, or no `sessionId` and no pixel on the page. |
| Device and Geography reports empty | The server did not forward the end user's `device` object. |
