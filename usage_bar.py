#!/usr/bin/env python3
"""
AI Usage Bar — tiny macOS menu bar app.

Shows how much of your AI usage limits you have LEFT:
  - Claude  (Claude Code)   -> 5-hour and weekly windows
  - OpenAI  (Codex CLI)     -> 5-hour and weekly windows

Reads each CLI's local OAuth token and refreshes it automatically when it
expires. No credentials are bundled or sent anywhere.

UI language: auto-detected from macOS (English by default, Spanish if the
system is in Spanish). Can be forced from the menu.

Made by Bouz Labs — https://bouzlabs.com

Requirements:
  - Claude: Claude Code installed and signed in.
  - OpenAI: Codex CLI installed and signed in (measures Codex usage, not
            ChatGPT web chat messages).
"""

import json
import base64
import subprocess
import time
import datetime
import urllib.request
import urllib.parse
import urllib.error
import webbrowser
from pathlib import Path

import rumps

BRAND_URL = "https://bouzlabs.com"
BRAND_LABEL = "by Bouz Labs · bouzlabs.com"

# --- Config -----------------------------------------------------------------
CONFIG_FILE = Path.home() / ".usagebar.json"


def load_config():
    try:
        cfg = json.loads(CONFIG_FILE.read_text())
    except Exception:
        cfg = {}
    mode = cfg.get("mode")
    if mode not in ("claude", "openai", "both"):
        mode = "both"
    lang = cfg.get("lang")
    if lang not in ("auto", "en", "es"):
        lang = "auto"
    show_time = cfg.get("show_time", True)
    return {"mode": mode, "lang": lang, "show_time": bool(show_time)}


def save_config(cfg):
    try:
        CONFIG_FILE.write_text(json.dumps(cfg))
    except Exception:
        pass


# --- i18n -------------------------------------------------------------------
def detect_os_lang():
    """Return 'es' if macOS is set to Spanish, else 'en'."""
    for key in ("AppleLocale", "AppleLanguages"):
        try:
            out = subprocess.run(["defaults", "read", "-g", key],
                                 capture_output=True, text=True).stdout.strip().lower()
        except Exception:
            out = ""
        if out.startswith("es") or '"es' in out or "es-" in out or "es_" in out:
            return "es"
    return "en"


STRINGS = {
    "en": {
        "title_err": "Usage ⚠️",
        "claude": "Claude",
        "openai": "OpenAI (Codex)",
        "hidden": "  (hidden)",
        "row_5h": "  5h: {p}% left   ·   resets in {c}",
        "row_week": "  Weekly: {p}% left   ·   resets {r}",
        "row_dash": "  —",
        "open_claude": "  Open Claude Code to refresh the session",
        "install_codex": "  Install Codex CLI and sign in to see it",
        "open_codex": "  Open Codex to refresh the session",
        "error": "  Error: {s}",
        "updated": "Updated {t}",
        "refresh_now": "Refresh now",
        "show": "Show",
        "only_claude": "Claude only",
        "only_openai": "OpenAI only",
        "both": "Both",
        "language": "Language",
        "auto": "Automatic",
        "english": "English",
        "spanish": "Spanish",
        "show_time": "Show 5h time left",
        "quit": "Quit",
        "now": "now",
        "dash": "—",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "lbl_cl": "Cl", "lbl_oai": "OAI", "lbl_5h": "5h", "lbl_7d": "7d",
    },
    "es": {
        "title_err": "Uso ⚠️",
        "claude": "Claude",
        "openai": "OpenAI (Codex)",
        "hidden": "  (oculto)",
        "row_5h": "  5h: queda {p}%   ·   resetea en {c}",
        "row_week": "  Semanal: queda {p}%   ·   termina {r}",
        "row_dash": "  —",
        "open_claude": "  Abre Claude Code para renovar la sesión",
        "install_codex": "  Instala Codex CLI e inicia sesión para verlo",
        "open_codex": "  Abre Codex para renovar la sesión",
        "error": "  Error: {s}",
        "updated": "Actualizado {t}",
        "refresh_now": "Actualizar ahora",
        "show": "Mostrar",
        "only_claude": "Solo Claude",
        "only_openai": "Solo OpenAI",
        "both": "Ambos",
        "language": "Idioma",
        "auto": "Automático",
        "english": "Inglés",
        "spanish": "Español",
        "show_time": "Mostrar tiempo restante 5h",
        "quit": "Salir",
        "now": "ya",
        "dash": "—",
        "days": ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"],
        "months": ["ene", "feb", "mar", "abr", "may", "jun",
                   "jul", "ago", "sep", "oct", "nov", "dic"],
        "lbl_cl": "Cl", "lbl_oai": "OAI", "lbl_5h": "5h", "lbl_7d": "7d",
    },
}


# --- Claude -----------------------------------------------------------------
CL_SERVICE = "Claude Code-credentials"
CL_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
CL_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
CL_TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"

# --- OpenAI / Codex ---------------------------------------------------------
OAI_AUTH_FILE = Path.home() / ".codex" / "auth.json"
OAI_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
OAI_USAGE_URL = "https://chatgpt.com/backend-api/codex/usage"
OAI_TOKEN_URL = "https://auth.openai.com/oauth/token"

POLL_SECONDS = 180
HTTP_TIMEOUT = 10


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def _cl_account():
    r = _run(["security", "find-generic-password", "-s", CL_SERVICE, "-g"])
    for line in (r.stdout + r.stderr).splitlines():
        if '"acct"' in line and '="' in line:
            return line.split('="', 1)[1].rstrip('"')
    return None


def _cl_read():
    r = _run(["security", "find-generic-password", "-s", CL_SERVICE, "-w"])
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout.strip())
    except json.JSONDecodeError:
        return None


def _cl_write(creds, account):
    _run(["security", "add-generic-password", "-U",
          "-a", account, "-s", CL_SERVICE, "-w", json.dumps(creds)])


def _cl_token():
    creds = _cl_read()
    if not creds:
        return None, "no_creds"
    oauth = creds.get("claudeAiOauth", {})
    now_ms = int(time.time() * 1000)
    if oauth.get("accessToken") and oauth.get("expiresAt", 0) > now_ms + 60000:
        return oauth["accessToken"], "ok"
    refresh = oauth.get("refreshToken")
    if not refresh:
        return None, "expired"
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh,
        "client_id": CL_CLIENT_ID,
    }).encode()
    req = urllib.request.Request(CL_TOKEN_URL, data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            tok = json.loads(resp.read().decode())
    except Exception:
        return None, "refresh_failed"
    oauth["accessToken"] = tok["access_token"]
    if tok.get("refresh_token"):
        oauth["refreshToken"] = tok["refresh_token"]
    oauth["expiresAt"] = now_ms + int(tok.get("expires_in", 3600)) * 1000
    creds["claudeAiOauth"] = oauth
    acct = _cl_account()
    if acct:
        _cl_write(creds, acct)
    return oauth["accessToken"], "refreshed"


def fetch_claude():
    token, status = _cl_token()
    if not token:
        return None, status
    req = urllib.request.Request(CL_USAGE_URL, headers={
        "Authorization": f"Bearer {token}",
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": "claude-code/1.0",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return None, f"http_{e.code}"
    except Exception:
        return None, "net_error"
    five = data.get("five_hour") or {}
    week = data.get("seven_day") or {}
    return {
        "5h": (round(100 - (five.get("utilization") or 0)), five.get("resets_at")),
        "7d": (round(100 - (week.get("utilization") or 0)), week.get("resets_at")),
    }, "ok"


# --- OpenAI / Codex ---------------------------------------------------------
def _oai_read():
    try:
        return json.loads(OAI_AUTH_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _oai_plan(auth):
    try:
        payload = auth["tokens"]["id_token"].split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return claims.get("https://api.openai.com/auth", {}).get("chatgpt_plan_type", "")
    except Exception:
        return ""


def _oai_refresh(auth):
    refresh = auth.get("tokens", {}).get("refresh_token")
    if not refresh:
        raise RuntimeError("no refresh token")
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh,
        "client_id": OAI_CLIENT_ID,
    }).encode()
    req = urllib.request.Request(OAI_TOKEN_URL, data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode())["access_token"]


def _iso_from_epoch(secs):
    if not secs:
        return None
    return datetime.datetime.fromtimestamp(secs, tz=datetime.timezone.utc).isoformat()


def fetch_openai():
    auth = _oai_read()
    if not auth:
        return None, "no_creds"
    tokens = auth.get("tokens", {})
    access = tokens.get("access_token")
    if not access:
        return None, "no_creds"
    account_id = tokens.get("account_id", "")

    data = None
    for attempt in range(2):
        req = urllib.request.Request(OAI_USAGE_URL, headers={
            "Authorization": f"Bearer {access}",
            "chatgpt-account-id": account_id,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                data = json.loads(resp.read().decode())
            break
        except urllib.error.HTTPError as e:
            if e.code in (401, 403) and attempt == 0:
                try:
                    access = _oai_refresh(auth)
                except Exception:
                    return None, "refresh_failed"
            else:
                return None, f"http_{e.code}"
        except Exception:
            return None, "net_error"

    if data is None:
        return None, "net_error"

    rl = data.get("rate_limit") or {}
    p = rl.get("primary_window") or {}
    s = rl.get("secondary_window") or {}
    return {
        "plan": data.get("plan_type") or _oai_plan(auth),
        "5h": (round(100 - (p.get("used_percent") or 0)), _iso_from_epoch(p.get("reset_at"))),
        "7d": (round(100 - (s.get("used_percent") or 0)), _iso_from_epoch(s.get("reset_at"))),
    }, "ok"


# --- Formatting -------------------------------------------------------------
def _local(ts):
    return datetime.datetime.fromisoformat(ts).astimezone()


def dot(p5, p7):
    worst = min(p5, p7)
    return "🟢" if worst > 40 else ("🟡" if worst >= 15 else "🔴")


# --- App --------------------------------------------------------------------
class UsageApp(rumps.App):
    def __init__(self):
        super().__init__("Usage …", quit_button=None)
        self.cfg = load_config()
        self.t = STRINGS[self._lang()]

        self.cl_head = rumps.MenuItem("Claude")
        self.cl_five = rumps.MenuItem("  5h")
        self.cl_week = rumps.MenuItem("  7d")
        self.oa_head = rumps.MenuItem("OpenAI (Codex)")
        self.oa_five = rumps.MenuItem("  5h")
        self.oa_week = rumps.MenuItem("  7d")
        self.m_updated = rumps.MenuItem("—")
        self.m_refresh = rumps.MenuItem("", callback=self.manual)

        # View submenu
        self.v_claude = rumps.MenuItem("", callback=self.set_view)
        self.v_openai = rumps.MenuItem("", callback=self.set_view)
        self.v_both = rumps.MenuItem("", callback=self.set_view)
        self._view_items = {"claude": self.v_claude,
                            "openai": self.v_openai, "both": self.v_both}
        self.view_menu = rumps.MenuItem("")
        self.view_menu.add(self.v_claude)
        self.view_menu.add(self.v_openai)
        self.view_menu.add(self.v_both)

        # Language submenu
        self.l_auto = rumps.MenuItem("", callback=self.set_lang)
        self.l_en = rumps.MenuItem("", callback=self.set_lang)
        self.l_es = rumps.MenuItem("", callback=self.set_lang)
        self._lang_items = {"auto": self.l_auto, "en": self.l_en, "es": self.l_es}
        self.lang_menu = rumps.MenuItem("")
        self.lang_menu.add(self.l_auto)
        self.lang_menu.add(self.l_en)
        self.lang_menu.add(self.l_es)

        self.t_time = rumps.MenuItem("", callback=self.toggle_time)
        self.m_quit = rumps.MenuItem("", callback=rumps.quit_application)
        self.m_brand = rumps.MenuItem(BRAND_LABEL, callback=self.open_site)

        self.menu = [
            self.cl_head, self.cl_five, self.cl_week,
            None,
            self.oa_head, self.oa_five, self.oa_week,
            None,
            self.m_updated,
            self.m_refresh,
            self.view_menu,
            self.lang_menu,
            self.t_time,
            None,
            self.m_brand,
            self.m_quit,
        ]
        self.apply_lang()
        self.update(None)
        rumps.Timer(self.update, POLL_SECONDS).start()

    # -- language ------------------------------------------------------------
    def _lang(self):
        return detect_os_lang() if self.cfg["lang"] == "auto" else self.cfg["lang"]

    def apply_lang(self):
        self.t = STRINGS[self._lang()]
        t = self.t
        self.m_refresh.title = t["refresh_now"]
        self.view_menu.title = t["show"]
        self.v_claude.title = t["only_claude"]
        self.v_openai.title = t["only_openai"]
        self.v_both.title = t["both"]
        self.lang_menu.title = t["language"]
        self.l_auto.title = t["auto"]
        self.l_en.title = t["english"]
        self.l_es.title = t["spanish"]
        self.t_time.title = t["show_time"]
        self.t_time.state = self.cfg["show_time"]
        self.m_quit.title = t["quit"]
        for mode, item in self._view_items.items():
            item.state = (self.cfg["mode"] == mode)
        for code, item in self._lang_items.items():
            item.state = (self.cfg["lang"] == code)

    def set_lang(self, sender):
        for code, item in self._lang_items.items():
            if item is sender:
                self.cfg["lang"] = code
                break
        save_config(self.cfg)
        self.apply_lang()
        self.update(None)

    # -- view ----------------------------------------------------------------
    def set_view(self, sender):
        for mode, item in self._view_items.items():
            if item is sender:
                self.cfg["mode"] = mode
                break
        for mode, item in self._view_items.items():
            item.state = (self.cfg["mode"] == mode)
        save_config(self.cfg)
        self.update(None)

    def toggle_time(self, sender):
        self.cfg["show_time"] = not self.cfg["show_time"]
        sender.state = self.cfg["show_time"]
        save_config(self.cfg)
        self.update(None)

    def manual(self, _):
        self.update(None)

    def open_site(self, _):
        try:
            webbrowser.open(BRAND_URL)
        except Exception:
            subprocess.run(["open", BRAND_URL])

    # -- formatting helpers (language-aware) ---------------------------------
    def fmt_reset(self, ts):
        if not ts:
            return self.t["dash"]
        dt = _local(ts)
        return f"{self.t['days'][dt.weekday()]} {dt.day} {self.t['months'][dt.month - 1]} {dt:%H:%M}"

    def fmt_countdown(self, ts):
        if not ts:
            return self.t["dash"]
        s = int((_local(ts) - datetime.datetime.now().astimezone()).total_seconds())
        if s <= 0:
            return self.t["now"]
        h, m = s // 3600, (s % 3600) // 60
        return f"{h}h {m}m" if h else f"{m}m"

    # -- refresh -------------------------------------------------------------
    def update(self, _):
        t = self.t
        title = []
        show_claude = self.cfg["mode"] in ("claude", "both")
        show_openai = self.cfg["mode"] in ("openai", "both")

        # Claude
        self.cl_head.title = t["claude"] + ("" if show_claude else t["hidden"])
        if show_claude:
            cl, cl_status = fetch_claude()
            if cl:
                c5, c5r = cl["5h"]
                c7, c7r = cl["7d"]
                c_time = f" ⏳{self.fmt_countdown(c5r).replace(' ', '')}" if self.cfg["show_time"] and c5r else ""
                title.append(f"{dot(c5, c7)} {t['lbl_cl']} {t['lbl_5h']} {c5}%{c_time} · {t['lbl_7d']} {c7}%")
                self.cl_five.title = t["row_5h"].format(p=c5, c=self.fmt_countdown(c5r))
                self.cl_week.title = t["row_week"].format(p=c7, r=self.fmt_reset(c7r))
            else:
                title.append(f"⚠️ {t['lbl_cl']}")
                self.cl_five.title = t["open_claude"] \
                    if cl_status in ("no_creds", "expired", "refresh_failed") \
                    else t["error"].format(s=cl_status)
                self.cl_week.title = t["row_dash"]

        # OpenAI
        if show_openai:
            oa, oa_status = fetch_openai()
            if oa:
                o5, o5r = oa["5h"]
                o7, o7r = oa["7d"]
                plan = oa.get("plan") or ""
                self.oa_head.title = t["openai"] + (f" — {plan}" if plan else "")
                o_time = f" ⏳{self.fmt_countdown(o5r).replace(' ', '')}" if self.cfg["show_time"] and o5r else ""
                title.append(f"{dot(o5, o7)} {t['lbl_oai']} {t['lbl_5h']} {o5}%{o_time} · {t['lbl_7d']} {o7}%")
                self.oa_five.title = t["row_5h"].format(p=o5, c=self.fmt_countdown(o5r))
                self.oa_week.title = t["row_week"].format(p=o7, r=self.fmt_reset(o7r))
            else:
                self.oa_head.title = t["openai"]
                if oa_status == "no_creds":
                    self.oa_five.title = t["install_codex"]
                elif oa_status == "refresh_failed":
                    self.oa_five.title = t["open_codex"]
                else:
                    self.oa_five.title = t["error"].format(s=oa_status)
                self.oa_week.title = t["row_dash"]
        else:
            self.oa_head.title = t["openai"] + t["hidden"]

        self.title = "   ".join(title) if title else t["title_err"]
        self.m_updated.title = t["updated"].format(t=datetime.datetime.now().strftime("%H:%M"))


if __name__ == "__main__":
    UsageApp().run()
