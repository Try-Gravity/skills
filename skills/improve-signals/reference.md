# Reference: improve your Gravity signals

Details for `SKILL.md`. Every name comes from the public docs at https://docs.trygravity.com or from the published SDK packages. If your SDK version differs, read its docs page first.

## 1. Search patterns

```bash
# Requests and context
rg -n 'getAds\(|get_ads\(|/api/v1/ad|gravityContext\(|gravity_context|hashPii\(|hashPII\('
rg -n 'device_type|device\.os|"os"|userIP|extraDeviceFields'
rg -n 'hashed_email|hashed_phone|\.email\b|\.phone\b'
rg -n 'consent|tcfString|usPrivacy|gpc|Sec-GPC|gppSid|readCMPConsent|honorATT|honorAdTrackingLimit'
rg -n 'sessionId|session_id|gr_sess_|getSessionId'
rg -n 'user\.tags|tags:|usage:|inputTokens|prompt_tokens'
rg -n '"anonymous"|userId:\s*["'"'"']'
rg -n 'getPlacementContext|placement_context|max_ad_text_chars'
```

Then follow the data from the client, through your server, to the Gravity call.

## 2. Request fields in one place

| Field | Notes from the docs |
|---|---|
| `messages` | `[{role, content}]`. The engine uses the most recent messages. The SDKs send the last 2. Don't send a full chat archive. |
| `sessionId` | Required. Used for frequency caps and experiment groups. The pixel supplies `gr_sess_...` IDs that end after 30 minutes idle or 1 day, if you send none. |
| `user.id` | Required in the JS SDK as `userId`; optional in the API. Python, iOS, and Android SDKs send `"anonymous"` when none is given, and Gravity leaves that value out of per-user analytics. An email alone is not a user ID. |
| `user.hashed_email` | SHA-256 of the email after `strip()` and `lower()`. `email_hash` is an older name. |
| `user.hashed_phone` | SHA-256 of the phone number, digits only. |
| `user.age` | `"34"`, `"25-34"`, or `"1990"`. Under 18 gets no ads unless the account is approved for teen ads. |
| `user.gender` | `male`, `female`, or `other`. |
| `user.tags` | Up to 10 keys. Keys: lowercase letters, digits, underscores, 1 to 32 characters. Values: string, number, or boolean, trimmed to 64 characters. Resend the full map every request: the latest map per UTC day wins. Groups under 50 users are hidden in the dashboard. Never used for targeting. |
| `usage` | One call: `model`, `inputTokens`, `cachedInputTokens`, `outputTokens`, optional `cost` in USD. OpenAI-style usage objects are accepted. JS `@gravity-ai/api` 1.4.0 or later takes it as an option; the Python, iOS, and Android SDKs have no option for it. |
| `device.ip` | The end user's IP. Gravity ignores `user.ip`. |
| `device.ua` | The end user's User-Agent. Native apps send the real client string, for example `CFNetwork/Darwin`, `okhttp`, or `ktor-client`. |
| `device.device_type` | `desktop`, `mobile`, `tablet`. |
| `device.os` | `ios`, `android`, `macos`, `windows`, `linux`, `chromeos`, `other`. Version goes in `os_version`. |
| `device.ifa`, `device.id` | Optional advertising ID (apps) and your own device ID. The SDKs don't read the advertising ID; send it only if the user consented. |
| `consent` | `gdprApplies`, `tcfString`, `usPrivacy`, `gpc`, `gpp`, `gppSid`. All optional. |

## 3. Usage timing

When a new user message triggers an ad request, send the usage of the previous completed assistant reply. On the first turn, send none. Report each call once. If you fetch the ad after the model finishes, send that reply's usage on that request instead, not again on the next turn.

## 4. Code

**Hash on the client and forward everything (JavaScript).**
```ts
import { gravityContext, hashPii } from '@gravity-ai/api';

function anonymousId() {
  let id = localStorage.getItem('anon_id');
  if (!id) { id = crypto.randomUUID(); localStorage.setItem('anon_id', id); }
  return id;
}

// Only hash and send when your privacy rules allow it.
const hashed = user?.email ? await hashPii({ email: user.email }) : {};
const gravity_context = gravityContext({
  sessionId: chat.id,
  user: { userId: user?.id ?? anonymousId(), ...hashed },
});
// Send gravity_context to your server with the chat request.
```

**Forward the context on the server.**
```ts
const body = await req.json(); // carries gravity_context
const adPromise = gravity.getAds(
  { body, headers: Object.fromEntries(req.headers) },
  body.messages,
  [{ placement: 'below_response', placement_id: 'web-chat-below-answer' }],
);
```
`getAds` reads `gravity_context` from the body and adds the end user's IP from the forwarded headers. Make sure a proxy or CDN passes the real client IP in `X-Forwarded-For` or `X-Real-IP`.

**Hash on the server (Python).**
```python
import hashlib
def sha256_email(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()
def sha256_phone(phone: str) -> str:
    return hashlib.sha256("".join(c for c in phone if c.isdigit()).encode()).hexdigest()
```
The Python SDK reads `user` and `device` from `gravity_context` in the request body, so hash on the client where you can.

**Native apps.** iOS and Android SDKs take `userId` and the end user's IP (`userIP`) on `getAds()`. Both read CMP consent by default (`readCMPConsent`), and both honor the platform's tracking limit (`honorATT` on iOS, `honorAdTrackingLimit` on Android), which asks for contextual-only ads. Pass `consent` yourself if you need to override.

**Consent object by hand (custom server integration).**
```json
"consent": { "gdprApplies": true, "tcfString": "<from your CMP>", "usPrivacy": "1YNN", "gpc": false }
```
Send `Sec-GPC: 1` through if the browser sent it.

## 5. What to log while testing

Log the redacted request once, in test mode only. Keep: field names present, value types, `device.device_type`, `device.os`, and whether `device.ip` matches the client and not your server. Drop: message text, IDs, hashes, and keys.

## 6. Reading `/publisher-dashboard/health`

`items` rows have `key`, `kind` (`signal` or `check`), `value` (a share from 0 to 1), `status` (for example `good`), and `basis` (`measured` or `approximated`). `score` can be `null` while Gravity keeps the health score hidden. Use the rows, not the score.
