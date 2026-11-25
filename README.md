# Gravity agent skills for publishers

Agent skills for AI products that show [Gravity](https://trygravity.com) ads. Install them with the [`skills`](https://github.com/vercel-labs/skills) CLI and your coding agent (Claude Code, Cursor, Codex, and others) can set up Gravity ads, improve the signals you send, audit your integration, and explain your earnings.

## Install

```bash
npx skills add Try-Gravity/skills
```

Install one skill, or see what is in the repo without installing:

```bash
npx skills add Try-Gravity/skills --skill optimize-ad-integration
npx skills add Try-Gravity/skills --list
```

The CLI needs Node.js 22.20 or later. This repo is licensed under the MIT License (see `LICENSE`).

## The skills

| Skill | Use it when |
|---|---|
| [`publisher-setup`](skills/publisher-setup/SKILL.md) | You are adding Gravity ads for the first time, or to a new surface. Picks the SDK, plans placements, wires the request and the display, tests in test mode, and walks the going-live checklist. |
| [`improve-signals`](skills/improve-signals/SKILL.md) | You want better matching and higher advertiser value. Checks the conversation, user ID, hashed email, device, consent, tags, and usage that you send, and keeps them privacy-safe. |
| [`optimize-ad-integration`](skills/optimize-ad-integration/SKILL.md) | You want an audit of a live integration: where ads render, whether they are seen, tracking, ad fatigue, and units with low CTR. Returns ranked fixes and code diffs. |
| [`analyze-earnings`](skills/analyze-earnings/SKILL.md) | Earnings, CPM, or fill moved and you want to know why. Reads your funnel and tells market shifts apart from integration problems. |

Typical order: `publisher-setup`, then `improve-signals`, then `optimize-ad-integration`. Use `analyze-earnings` any time the numbers move.

## Ask your agent

- "Add Gravity ads to my chat app."
- "Improve the signals we send to Gravity."
- "Audit my Gravity ad integration and tell me what to fix first."
- "Why did my Gravity earnings drop this week? Is it the market or my app?"

## What the skills do and don't do

- They read your code and, if you give them your API key through an environment variable, your own dashboard numbers. Dashboard calls are read only.
- They propose changes as diffs for you to review. They don't push or deploy.
- They never print your API key, and they never send raw emails or phone numbers.
- They don't create placements or switch to production unless you ask for exactly that.
- The skills follow the public docs at https://docs.trygravity.com. If a skill and the docs disagree, the docs win.

To give a skill dashboard numbers, set `GRAVITY_API_KEY` in your shell. Keep the key on your server and out of any public repo.

## Docs and support

- Docs: https://docs.trygravity.com (add `.md` to any page for plain Markdown; `https://docs.trygravity.com/llms.txt` lists every page)
- Support: support@trygravity.com
