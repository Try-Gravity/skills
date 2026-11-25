# Reference: optimize your Gravity ad integration

Details for `SKILL.md`: search patterns, how to check each item, the low-CTR math, and code fixes. Every API name here comes from the public docs at https://docs.trygravity.com. If your SDK version differs, read its docs page first.

## 1. Search patterns

```bash
# SDK packages and versions
rg -n '"@gravity-ai/(api|react|ui|react-native)"' --glob 'package.json'
rg -n '@gravity-ai/' --glob '*lock*'
rg -n 'gravity_sdk|gravity-sdk' --glob '*.{py,toml,txt,cfg}'
rg -n 'gravity-swift-sdk|GravitySDK' --glob '*.{swift,resolved}'
rg -n 'ai\.trygravity\.sdk' --glob '*.{kt,kts,gradle}'

# Requests (server)
rg -n 'getAds\(|get_ads\(|/api/v1/ad|server\.trygravity\.(com|ai)'
rg -n 'gravityContext\(|gravity_context|hashPii\(|hashPII\(|getPlacementContext\('
rg -n 'placement_id|placement:'
rg -n 'YOUR_PLACEMENT_ID|placement_id:\s*["'"'"']main["'"'"']'
rg -n 'production\s*[:=]|testAd|alwaysReturn|relevancy|supportsSpec|enableFrames|excludedTopics'

# Rendering (client)
rg -n 'GravityAd|SpecAdView|SpecAd\(|GravityAdView|GravityThemeProvider|useAdTracking'
rg -n 'impUrl|clickUrl|trackImpression|handleClick|\bad\.url\b'

# Pixel and key hygiene
rg -n 'gr-pix\.js|gravityPixel\(|inAppBrowser'
rg -n 'GRAVITY_API_KEY' # should appear only in server code and env config

# Timers and rotation near ad code
rg -n 'setInterval|setTimeout|refetchInterval|refreshInterval'

# Other ad code that could share the screen
rg -n -i 'adsbygoogle|googletag|doubleclick|prebid|sponsored|promo(tion)?banner|house_?ad'
```

Then open each hit and follow the data from request to render.

## 2. How to check each item

**Main ad in the chat (1).** Find the parent of the ad component. Inline: rendered in the message list, right after the assistant message for that turn. Above composer: rendered in normal layout flow directly above the input, fully visible. Outside: sidebar, header, footer, other route, preview pane, status bar. Placement types `left_response`, `right_response`, `top_page`, `bottom_page`, `left_page`, `right_page` are usually outside the chat; confirm by reading the layout.

**Hidden behind the composer (5).** The most common case: the input is `position: fixed` or `sticky` at the bottom, and the message list doesn't have enough bottom padding, so the last message and the ad under it sit behind the input. Also check overlays with higher `z-index`, toasts and banners at the bottom, paywall or "out of credits" modals that stay open while ads keep rendering, and collapsed or `display: none` containers. Visibility detection (including the SDK's 50%-in-viewport rule) can't tell that something covers the ad, so the layout must guarantee it.

**One ad on screen (3).** Count every Gravity component that can be visible at once: one per placement, plus ads kept on past turns in a long chat. If several placements are requested together, make sure the layout never shows two at once (for example, a sidebar plus an inline ad).

**Show rate (7).** Wins that never become impressions. Look for: placements requested but never rendered (for example a desktop sidebar requested on mobile), the `ads` array not passed through the streaming "done" event, the slot unmounted when streaming ends, ad responses ignored when they arrive after the text, a component that renders only `ads[0]` when several placements are requested, and timeouts set too low.

**Signals (8-10).** In the server route, log (redacted) the request body that reaches Gravity once in test mode: `messages`, `sessionId`, `user.id`, `user.hashed_email`, `device.{ip,ua,device_type,os}`. The dashboard **Audience then Request signals** card and `GET /publisher-dashboard/health` show the share of requests carrying each signal. A response header `X-Gravity-Warning` means `device_type` or `os` is missing or not recognized.

**Logged-out users (11).** Find the condition around the ad request or component: `if (user)`, `isLoggedIn`, `session?.user`. Guests should get ads too, with a stable anonymous ID.

**Rotation and blank slots (13).** A timer that re-requests ads or swaps creatives while the user reads is rotation. A slot that clears on a timer, or keeps an empty bordered box when there's no ad, is a blank slot. Request on each user message; hide the slot when `ads` is empty.

**Copy and layout (15-19).** Look for `text-overflow: ellipsis`, `line-clamp`, fixed heights with `overflow: hidden` on the ad container, and very narrow containers. On the server, `getPlacementContext()` from `@gravity-ai/react` sends the real slot width so Gravity fits the copy. `max_ad_text_chars` can be set per placement (the placements API minimum is 120, while the request-field page says 50 to 5000, so use 120 or more).

**CLI (20).** Print the link as a short clickable URL (or an OSC 8 terminal hyperlink with a visible URL fallback) that opens on a plain click.

## 3. Low-CTR math

Use daily per-placement data over at least 14 days (`GET /publisher-dashboard/placements?days=14`, or the **Placements** page).

- **In-chat bar** `B` = total clicks / total impressions across your in-chat placements.
- For each other unit with CTR `c` on `n` impressions, the high end of its range is `c + 2 * sqrt(c * (1 - c) / n)`. Use this to check that a gap is not just noise.
- **Remove** when the unit's CTR stays well below your in-chat CTR for 14+ days, on most days, and the high end is also well below that bar (enough impressions that the gap is real).
- **Test once** when `c` is under `B` but not well below it.
- **Keep** when `c >= B`.
- **Too little data** when `c` looks low but the high end still reaches near `B` because `n` is small: wait for more impressions.

"Well below" is a judgment, not a fixed fraction. If the publisher names a cutoff, use it. If they don't, treat a unit as well below only when the gap is large and obvious, not a close call.

Example with made-up numbers: in-chat bar 1.5%. A sidebar at 0.2% CTR on 20,000 impressions has a high end of 0.2% + 2 * sqrt(0.002 * 0.998 / 20,000) about 0.26%, which is well below 1.5%, so remove it. A banner at 1.2% is below the bar but not well below: test one redesign or a move into the chat.

```python
from math import sqrt
def high_end(clicks, imps):
    c = clicks / imps
    return c + 2 * sqrt(c * (1 - c) / imps)
```

Don't invent a numeric cutoff in the report. State the in-chat bar, the unit's CTR and high end, and why you called the gap well below or not.

## 4. Code fixes

Adapt each to the codebase; keep the smallest change that works.

**Forward the client context from the server (Next.js App Router).**
```ts
// app/api/chat/route.ts
const body = await req.json();
const adPromise = gravity.getAds(
 { body, headers: Object.fromEntries(req.headers) }, // body carries gravity_context
 body.messages,
 [{ placement: 'below_response', placement_id: 'web-chat-below-answer' }],
);
```

**User ID for everyone, plus hashed email (client).**
```ts
import { gravityContext, hashPii } from '@gravity-ai/api';

function anonymousId() {
 let id = localStorage.getItem('anon_id');
 if (!id) { id = crypto.randomUUID(); localStorage.setItem('anon_id', id); }
 return id;
}

const hashed = user?.email ? await hashPii({ email: user.email }) : {};
const gravity_context = gravityContext({
 sessionId: chat.id,
 user: { userId: user?.id ?? anonymousId(), ...hashed },
});
```

**Main ad inline, after the latest reply.**
```tsx
import { GravityAd } from '@gravity-ai/react';

{messages.map((m, i) => (
 <Fragment key={m.id}>
 <Message message={m} />
 {i === messages.length - 1 && m.role === 'assistant' && ad && <GravityAd ad={ad} />}
 </Fragment>
))}
```

**Above the composer, not behind it.**
```tsx
<div className="flex h-full flex-col">
 <MessageList className="flex-1 overflow-y-auto" />
 {ad && <div className="shrink-0"><GravityAd ad={ad} /></div>} {/* in normal flow */}
 <Composer className="shrink-0" />
</div>
```
If the composer must stay `position: fixed`, give the scroll area bottom padding at least as tall as the composer plus the ad.

**Remove a low-CTR placement.** Delete it from the `placements` array in `getAds` and delete its component, in the same change. Leaving it in the request while hiding it in the UI hurts show rate.

**Custom renderer: real impression, tracked click.**
```ts
const gravity = new Gravity({ supportsSpec: false, enableFrames: false });
```
```tsx
function MyAd({ ad }) {
 const ref = useRef<HTMLDivElement>(null);
 useEffect(() => {
 const el = ref.current; if (!el) return;
 const io = new IntersectionObserver(([e]) => {
 if (e.isIntersecting) { new Image().src = ad.impUrl; io.disconnect(); }
 }, { threshold: 0.5 });
 io.observe(el);
 return () => io.disconnect();
 }, [ad.impUrl]);
 return (
 <div ref={ref}>
 <span>Sponsored</span>
 <a href={ad.clickUrl} target="_blank" rel="noopener">{ad.brandName}</a>
 <p>{ad.adText}</p>
 </div>
 );
}
```

**Direct HTTP: declare device type and OS.**
```json
"device": { "ip": "<end user IP>", "ua": "<end user UA>", "device_type": "mobile", "os": "ios" }
```
Values: `device_type` is `desktop`, `mobile`, or `tablet`; `os` is `ios`, `android`, `macos`, `windows`, `linux`, `chromeos`, or `other`.

**Native apps.** iOS: `SpecAdView(ad:gravity:sessionId:)`; custom views call `gravity.trackImpression(ad)` when visible and `gravity.handleClick(ad)` on tap. Android: `SpecAd(...)` in Compose or `GravityAdView` in XML. React Native lists: report visibility through the list (`onViewableItemsChanged`) or `measureVisibility` from `useAdTracking`.

## 5. Docs to read

- Best practices: https://docs.trygravity.com/ai-platforms/best-practices.md
- Guidelines: https://docs.trygravity.com/ai-platforms/publisher-requirements.md
- Request ads (fields, device signals, hashing): https://docs.trygravity.com/ai-platforms/request-ads.md
- Show ads: https://docs.trygravity.com/ai-platforms/show-ads.md
- Placements: https://docs.trygravity.com/ai-platforms/placements.md
- Going live checklist: https://docs.trygravity.com/ai-platforms/going-live.md
- Pixel: https://docs.trygravity.com/ai-platforms/pixel.md
- Experiments: https://docs.trygravity.com/ai-platforms/experiments.md
- User earnings and tags: https://docs.trygravity.com/ai-platforms/user-earnings.md
- Publisher Dashboard API: https://docs.trygravity.com/api-reference/publisher/overview.md
- SDKs: https://docs.trygravity.com/sdks/javascript.md, /sdks/python.md, /sdks/ios.md, /sdks/android.md, /sdks/react-native.md, /sdks/terminal.md
