# AI Usage Bar

**By [Bouz Labs](https://bouzlabs.com)** · A tiny macOS **menu bar** app that shows how much of your AI usage limits you have **left** — for **Claude** (via Claude Code) and **OpenAI** (via Codex CLI), side by side.

```
🟢 Cl 5h 69% ⏳41m · 7d 89%   🟢 OAI 5h 94% ⏳2h14m · 7d 55%
```

The ⏳ shows the time left until the 5-hour window resets — so at a glance you know not just *how much* you have left, but *how long* until it refills.

![Claude + OpenAI in the macOS menu bar](docs/both.png)

![Time left until the 5h window resets](docs/time.png)

<p align="center">
  <img src="docs/claude.png" alt="Claude only" width="320"> &nbsp;
  <img src="docs/openai.png" alt="OpenAI only" width="320">
</p>

For each service it shows the **5-hour** session window and the **weekly** window: the percentage remaining, when the 5h window resets, and the exact day the weekly window ends. Click the menu bar text for the full breakdown.

The colored dot is an at-a-glance health indicator: 🟢 plenty left · 🟡 getting low (<40%) · 🔴 almost out (<15%).

## Why

Claude (Max/Pro) and OpenAI's Codex both use rolling 5-hour + weekly limits, but checking how much you have left means digging into settings or running a CLI command. This puts it permanently in your menu bar and refreshes itself.

## Features

- **Claude** and **OpenAI (Codex)** usage in one place.
- **Time-to-reset at a glance**: a ⏳ countdown shows how long until the 5-hour window refills, right next to the percentage. Toggle it from the menu (*Show 5h time left*).
- **Choose what to show**: Claude only, OpenAI only, or both (menu → *Show*). Your choice is remembered.
- **Bilingual UI** (English / Spanish), auto-detected from your macOS language and overridable from the menu (*Language*).
- **Auto-refresh** every 3 minutes — no manual action needed.
- **Self-renewing tokens**: when the local access token expires (~hourly) it refreshes automatically using the stored refresh token, so the widget keeps working without you opening the CLIs.
- **No credentials bundled or transmitted anywhere.** It only reads the tokens that already live on your Mac and talks directly to the official Anthropic / OpenAI hosts.

## Requirements

- macOS.
- For **Claude**: [Claude Code](https://www.anthropic.com/claude-code) installed and signed in.
- For **OpenAI**: [Codex CLI](https://developers.openai.com/codex) installed and signed in (ChatGPT login).
- Python 3 is **not** required if you use the standalone app (Option A); it's only needed for the script-based options.

> The OpenAI figure reflects **Codex** usage (the 5h/weekly windows of your ChatGPT plan that Codex consumes), **not** your ChatGPT web chat messages — OpenAI does not expose those.

## Install

### Option A — Standalone app (recommended, no Python needed)

Download **`AI Usage Bar.app`** from the [latest Release](../../releases), then:

1. Drag it into your **Applications** folder.
2. First launch: **right-click the app → Open → Open** (one-time Gatekeeper prompt, because the app isn't notarized).
3. To start it automatically: *System Settings → General → Login Items → +* and add the app.

> Building it yourself: double-click **`build_app.command`** (needs Python once) — it produces `dist/AI Usage Bar.app`. The same build runs automatically on GitHub Actions and is attached to each release.

### Option B — Script + auto-start (needs Python)

Double-click **`install.command`**. It creates an isolated virtualenv, installs the only dependency (`rumps`), starts the app, and sets it to launch at login. First run may need *right-click → Open* for Gatekeeper.

### Option C — Run manually (for developers)

```bash
python3 -m venv .venv && ./.venv/bin/pip install rumps
./.venv/bin/python usage_bar.py
```

## How to use

Once running, everything lives in the menu bar item. Reading it:

```
🟢 Cl 5h 69% ⏳41m · 7d 89%
│   │  │   │    │     │   └─ weekly window: % left
│   │  │   │    │     └───── weekly label
│   │  │   │    └─────────── ⏳ time until the 5h window resets
│   │  │   └──────────────── 5-hour window: % left
│   │  └──────────────────── 5h label
│   └─────────────────────── service: Cl = Claude, OAI = OpenAI
└─────────────────────────── health dot: 🟢 plenty · 🟡 low (<40%) · 🔴 almost out (<15%)
```

Click the item to open the menu, where you can:

- See the full breakdown per service (exact % left, 5h countdown, and the day the weekly window ends).
- **Refresh now** — force an immediate update (it also auto-refreshes every 3 minutes).
- **Show** — pick what appears in the bar: Claude only, OpenAI only, or both.
- **Language** — Automatic (follows macOS), English, or Spanish.
- **Show 5h time left** — toggle the ⏳ countdown on/off.

All preferences are saved and restored on restart.

## Uninstall

Double-click **`uninstall.command`** (removes auto-start; doesn't delete files). To stop a running instance, use **Salir** in its menu.

## How it works

It reads your local OAuth tokens and queries each provider's usage endpoint:

| | Claude | OpenAI (Codex) |
|---|---|---|
| Token source | macOS Keychain `Claude Code-credentials` | `~/.codex/auth.json` |
| Usage endpoint | `api.anthropic.com/api/oauth/usage` | `chatgpt.com/backend-api/codex/usage` |
| Refresh endpoint | `console.anthropic.com/v1/oauth/token` | `auth.openai.com/oauth/token` |

Both endpoints return `5h` and `7d` windows with a used-percentage and a reset time. The app displays `100 − used` (what's left).

## ⚠️ Disclaimer

These are **undocumented** endpoints — the same ones that power Claude Code's `/usage` and Codex's `/status`. They work well today but Anthropic or OpenAI may change or restrict them at any time. This project is not affiliated with or endorsed by Anthropic or OpenAI. Use at your own risk.

## Credits

Built on endpoints documented by the community:

- Anthropic OAuth usage endpoint — discussion in [Claude-Code-Usage-Monitor #202](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues/202).
- Codex usage endpoint — reference implementation [`codex-cli-usage`](https://github.com/wakamex/codex-cli-usage).

## License

[MIT](LICENSE) © 2026 [Bouz Labs](https://bouzlabs.com)

---

<p align="center">
  Made with care by <a href="https://bouzlabs.com"><b>Bouz Labs</b></a> — <a href="https://bouzlabs.com">bouzlabs.com</a>
</p>
