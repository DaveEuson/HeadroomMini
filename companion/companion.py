#!/usr/bin/env python3
"""Yoyu companion — runs on the computer where you use Claude Code.

Reads the *real* Claude subscription usage numbers and pushes them to the Pi.

How (and why it works when a fresh sign-in doesn't): it never signs in. It
reuses Claude Code's own existing login — the credentials Claude Code already
saved on this machine — refreshes that token if needed, and reads Anthropic's
usage endpoint. It never touches the authorization-code sign-in exchange, which
is the throttled one. (Same approach as the Sparko "Fuel" widget.)

    Credentials:  macOS Keychain item "Claude Code-credentials", else
                  ~/.claude/.credentials.json  (Windows/Linux)
    Refresh:      POST https://platform.claude.com/v1/oauth/token (refresh_token)
    Usage:        GET  https://api.anthropic.com/api/oauth/usage

If it can't read credentials (Claude Code not logged in here), it falls back to
estimating usage from Claude Code's local logs.

Run it:  python3 companion.py --pi http://yoyu.local:8080
Standard library only, Python 3.8+.
"""

import argparse
import concurrent.futures
import datetime
import glob
import hashlib
import hmac
import json
import os
import secrets
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

# TLS trust store. A PyInstaller-frozen binary (esp. on macOS) often can't find
# the system CA certs -> "CERTIFICATE_VERIFY_FAILED". Prefer certifi's bundle
# when present (it is in the packaged app); fall back to the system default for
# a plain "run from source" where certifi may not be installed.
try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    _SSL_CONTEXT = ssl.create_default_context()

APP_MARKER = "Yoyu"  # /api/status "app" field, used for discovery
# Boards flashed before the rename still answer with these. Discovery has to
# keep accepting them or a working board on the desk becomes undiscoverable
# after a companion update -- and the fix would be a USB re-flash.
LEGACY_MARKERS = ("Headroom", "ClaudeTrackerPi")

CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
REFRESH_URL = "https://platform.claude.com/v1/oauth/token"
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
OAUTH_BETA = "oauth-2025-04-20"
USER_AGENT = "Yoyu-Companion/1.0"
KEYCHAIN_SERVICE = "Claude Code-credentials"
REFRESH_MARGIN = 300  # refresh if the token expires within 5 minutes

WINDOW_LABELS = {
    "five_hour": "Session (5 hour)",
    "seven_day": "Weekly (all models)",
    "seven_day_sonnet": "Weekly (Sonnet)",
    "seven_day_opus": "Weekly (Opus)",
    "seven_day_fable": "Weekly (Fable)",
    "seven_day_oauth_apps": "Weekly (connected apps)",
    "extra_usage": "Extra usage",
}

# Fallback-only: rough token budgets if we must estimate from logs. Anthropic
# doesn't publish real caps, so these are ballpark; "max" is ~5x "pro". Only
# used when there's no Claude Code login to read the real numbers from.
PLAN_PRESETS = {
    "max": {
        "five_hour": 220_000_000,
        "seven_day": 1_500_000_000,
        "seven_day_opus": 300_000_000,
    },
    "pro": {
        "five_hour": 44_000_000,
        "seven_day": 300_000_000,
        "seven_day_opus": 60_000_000,
    },
}
DEFAULT_LIMITS = PLAN_PRESETS["max"]
FIVE_HOURS, SEVEN_DAYS = 5 * 3600, 7 * 86400


# ----------------------------------------------------- credentials (like Sparko)

def _creds_file():
    return os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")


def read_creds():
    """Return (creds, save_fn) or (None, None). creds has accessToken/
    refreshToken/expiresAt(ms). save_fn persists an updated oauth dict."""
    # macOS Keychain
    if sys.platform == "darwin":
        try:
            out = subprocess.run(
                ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                capture_output=True, text=True, timeout=5)
            if out.returncode == 0 and out.stdout.strip():
                creds = _parse_creds(out.stdout)
                if creds:
                    def save(oauth):
                        blob = json.dumps({"claudeAiOauth": oauth})
                        subprocess.run(
                            ["security", "add-generic-password", "-U",
                             "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_SERVICE,
                             "-w", blob], capture_output=True, timeout=5)
                    return creds, save
        except (OSError, subprocess.SubprocessError):
            pass
    # file (Windows / Linux)
    path = _creds_file()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            creds = _parse_creds(fh.read())
        if creds:
            def save(oauth):
                data = {"claudeAiOauth": oauth}
                tmp = path + ".tmp"
                # Create the temp file 0600 up front so the token is never
                # briefly world-readable, then preserve that on the final file
                # (os.replace would otherwise leave it at the umask default,
                # downgrading Claude's original 0600 credentials file).
                fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(data, fh)
                os.replace(tmp, path)
                try:
                    os.chmod(path, 0o600)
                except OSError:
                    pass  # best effort (e.g. Windows)
            return creds, save
    except OSError:
        pass
    return None, None


def _parse_creds(raw):
    try:
        j = json.loads(raw)
    except ValueError:
        return None
    o = j.get("claudeAiOauth") if isinstance(j, dict) else None
    o = o or j
    access = o.get("accessToken") or o.get("access_token")
    if not access:
        return None
    expires = o.get("expiresAt") or o.get("expires_at") or 0
    return {
        "accessToken": access,
        "refreshToken": o.get("refreshToken") or o.get("refresh_token"),
        "expiresAt": int(expires),  # epoch ms
        "subscriptionType": o.get("subscriptionType"),
        "_raw": o,
    }


def valid_token(creds, save_fn):
    """Return a usable access token, refreshing only if expired. None on fail."""
    exp_s = creds["expiresAt"] / 1000.0 if creds["expiresAt"] else 0
    if exp_s and exp_s - REFRESH_MARGIN > time.time():
        return creds["accessToken"]            # still fresh — pure read
    if not creds["refreshToken"]:
        return creds["accessToken"] if not exp_s else None
    # Rotating refresh tokens: only refresh if we can write the new one back,
    # so we never leave Claude Code with a dead token.
    try:
        body = json.dumps({"grant_type": "refresh_token",
                           "refresh_token": creds["refreshToken"],
                           "client_id": CLIENT_ID}).encode("utf-8")
        req = urllib.request.Request(
            REFRESH_URL, data=body,
            headers={"Content-Type": "application/json",
                     "User-Agent": USER_AGENT}, method="POST")
        with urllib.request.urlopen(req, timeout=20, context=_SSL_CONTEXT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"token refresh failed ({exc}); Claude Code can refresh it by "
              "running any command.", file=sys.stderr)
        return None
    oauth = dict(creds["_raw"])
    oauth["accessToken"] = result["access_token"]
    if result.get("refresh_token"):
        oauth["refreshToken"] = result["refresh_token"]
    if result.get("expires_in"):
        oauth["expiresAt"] = int((time.time() + result["expires_in"]) * 1000)
    try:
        save_fn(oauth)
    except Exception as exc:  # noqa: BLE001 - don't lose the token on write fail
        print(f"warning: refreshed but couldn't save back ({exc})",
              file=sys.stderr)
    return oauth["accessToken"]


def fetch_usage(token):
    req = urllib.request.Request(
        USAGE_URL,
        headers={"Authorization": f"Bearer {token}",
                 "anthropic-beta": OAUTH_BETA,
                 "Accept": "application/json",
                 "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20, context=_SSL_CONTEXT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _window_label(key):
    """Friendly name for a usage window. Known windows are named explicitly;
    any future per-model weekly window (seven_day_<model>, e.g. seven_day_fable)
    is turned into "Weekly (<Model>)" rather than a raw "Seven Day Fable"."""
    if key in WINDOW_LABELS:
        return WINDOW_LABELS[key]
    if key.startswith("seven_day_"):
        model = key[len("seven_day_"):].replace("_", " ").title()
        return f"Weekly ({model})"
    return key.replace("_", " ").title()


def windows_from_usage(raw):
    order = list(WINDOW_LABELS)
    out = []
    for key, value in (raw or {}).items():
        if not isinstance(value, dict):
            continue
        util = value.get("utilization")
        if util is None:
            continue
        try:
            util = max(0.0, min(100.0, float(util)))
        except (TypeError, ValueError):
            continue
        out.append({
            "key": key,
            "label": _window_label(key),
            "utilization": round(util, 1),
            "resets_at": value.get("resets_at") or value.get("resetsAt"),
        })
    out.sort(key=lambda w: order.index(w["key"]) if w["key"] in order else 99)
    return out


class LiveUnavailable(Exception):
    """A Claude Code login exists but live usage is temporarily unreadable.
    We must NOT fall back to log estimates in this case — stale real numbers
    on the tracker beat fresh wrong ones."""

    def __init__(self, msg, retry_after=0, rate_limited=False):
        super().__init__(msg)
        self.retry_after = retry_after
        self.rate_limited = rate_limited


def get_live_windows():
    """Real usage via Claude Code's login. Returns (windows, plan), or None
    when there's no login at all. Raises LiveUnavailable on transient failure."""
    creds, save_fn = read_creds()
    if not creds:
        return None
    token = valid_token(creds, save_fn)
    if not token:
        raise LiveUnavailable(
            "couldn't refresh the Claude Code token; run `claude` on this "
            "computer once to refresh the login")
    try:
        raw = fetch_usage(token)
    except urllib.error.HTTPError as exc:
        retry_after = 0
        try:
            retry_after = int(exc.headers.get("Retry-After", 0) or 0)
        except (TypeError, ValueError):
            pass
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:200]
        except Exception:  # noqa: BLE001
            pass
        raise LiveUnavailable(
            f"usage endpoint returned HTTP {exc.code}"
            + (f", retry after {retry_after}s" if retry_after else "")
            + (f" — {detail}" if detail else ""),
            retry_after=retry_after, rate_limited=(exc.code == 429))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise LiveUnavailable(f"couldn't read usage: {exc}")
    windows = windows_from_usage(raw)
    if not windows:
        raise LiveUnavailable("usage response had no windows")
    return windows, creds.get("subscriptionType")


# ------------------------------------------------- fallback: estimate from logs

def _parse_ts(value):
    try:
        return datetime.datetime.fromisoformat(
            str(value).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return None


def _project_key(entry, path, root):
    """The full directory identifying the project an event belongs to.

    Prefer the event's own `cwd` — the folder under ~/.claude/projects is
    path-mangled (H:\\Projects\\Kiosk Grand becomes H--Projects-Kiosk-Grand)
    and can't be reversed: there is no telling a '-' that was a separator from
    one that was in the folder name. `cwd` is on every event and is exact, so
    the mangled slug is only a fallback for entries that somehow lack it.

    This returns the whole path, not the basename: ~/work/client-a/web and
    ~/work/client-b/web are different projects that a basename would merge."""
    cwd = entry.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        return cwd.strip().rstrip("/\\").replace("\\", "/")
    rel = os.path.relpath(path, root)
    return rel.replace("\\", "/").split("/")[0]


def _project_name(key):
    """The last path segment — what a project is called when nothing collides."""
    base = key.rstrip("/").split("/")[-1]
    if not base:
        return key
    # A bare slug fallback ('H--Projects-Sparko') has no separators to split on;
    # take the tail and accept that it may be approximate.
    return base.strip("-").split("-")[-1] if "/" not in key and "-" in base else base


def _roll_up_nested(totals):
    """Fold each project into the nearest ancestor that is also a project.

    Claude Code keys a project directory off the cwd, so opening a repo, a
    subdirectory of it, and a package inside that yields three "projects" that
    are one thing to the person who owns them — split across three rows and
    understated in each.

    Only folds into an ancestor that is *itself* tracked. H:/Projects/Qibb/Audio
    to Video stays put when there is no H:/Projects/Qibb project, because
    inventing a grouping the user never worked in would be a different kind of
    wrong. Matching is case-insensitive: Windows hands back whatever casing the
    shell used, and H:/Projects and h:/projects are the same directory."""
    canon = {}                                  # lowercased path -> real key
    for k in totals:
        canon.setdefault(k.lower(), k)
    root_of = {}
    for k in sorted(totals, key=len):           # ancestors are shorter, so
        cur, found = k, None                    # they resolve first
        while "/" in cur:
            cur = cur.rsplit("/", 1)[0]
            owner = canon.get(cur.lower())
            if owner is not None and owner != k:
                found = root_of.get(owner, owner)
                break
        root_of[k] = found or k
    merged = {}
    for k, tok in totals.items():
        r = root_of[k]
        merged[r] = merged.get(r, 0) + tok
    return merged


def _label_projects(keys, width=21):
    """Board labels for a set of project paths: short, and never ambiguous.

    Two projects that share a basename get qualified by their parent, and
    anything still colliding after the board's width limit gets a numeric
    suffix — two identical rows meaning different things is worse than an
    ugly one."""
    names = {k: _project_name(k) for k in keys}
    seen = {}
    for k, n in names.items():
        seen.setdefault(n, []).append(k)
    for n, owners in seen.items():
        if len(owners) < 2:
            continue
        for k in owners:                       # qualify with the parent dir
            parts = k.rstrip("/").split("/")
            if len(parts) >= 2:
                names[k] = parts[-2] + "/" + n

    out, used = {}, {}
    for k, n in names.items():
        if len(n) > width:
            # Trim from the *end* of each part, never the front. A qualified
            # label is "parent/base" where the parent is what distinguishes it
            # and the base is what they share, so taking the last `width` chars
            # would eat the parent and leave two rows differing only in their
            # ruined prefix ("main/foo" vs "ects/foo"). Give the parent a fixed
            # slice and the base the rest.
            if "/" in n:
                parent, base = n.split("/", 1)
                pw = max(4, width // 3)
                parent = parent[:pw]
                base = base[:max(1, width - len(parent) - 1)]
                n = parent + "/" + base
            else:
                n = n[:width]
        if n in used:                          # still colliding after trimming
            used[n] += 1
            suffix = "~%d" % used[n]
            n = n[:width - len(suffix)] + suffix
        else:
            used[n] = 1
        out[k] = n
    return out


def read_events(root, since=None):
    for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        # Events are appended in time order, so a file whose last write predates
        # the window can't hold one inside it. Skipping those keeps this from
        # being a full-disk read of every project you have ever opened.
        if since is not None:
            try:
                if os.path.getmtime(path) < since:
                    continue
            except OSError:
                pass
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if '"usage"' not in line:
                        continue
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue
                    msg = entry.get("message") or {}
                    usage = msg.get("usage") or {}
                    ts = _parse_ts(entry.get("timestamp"))
                    if not usage or ts is None:
                        continue
                    tokens = sum(usage.get(k, 0) or 0 for k in (
                        "input_tokens", "output_tokens",
                        "cache_creation_input_tokens", "cache_read_input_tokens"))
                    model = (msg.get("model") or "").lower()
                    yield ts, model, tokens, _project_key(entry, path, root)
        except OSError:
            continue


def get_log_windows(limits):
    root = os.path.join(os.path.expanduser("~"), ".claude", "projects")
    if not os.path.isdir(root):
        return None
    now = time.time()
    events = list(read_events(root, since=now - SEVEN_DAYS))

    def win(seconds, key, label, subset=None):
        cutoff, total, oldest = now - seconds, 0, None
        for ts, model, tok, _proj in events:
            if ts >= cutoff and (subset is None or subset in model):
                total += tok
                oldest = ts if oldest is None else min(oldest, ts)
        iso = (datetime.datetime.fromtimestamp(oldest + seconds,
               datetime.timezone.utc).isoformat() if oldest else None)
        return {"key": key, "label": label,
                "utilization": round(min(100.0, 100.0 * total / max(1, limits[key])), 1),
                "resets_at": iso}

    windows = [win(FIVE_HOURS, "five_hour", "Session (5 hour)"),
               win(SEVEN_DAYS, "seven_day", "Weekly (all models)")]
    opus = win(SEVEN_DAYS, "seven_day_opus", "Weekly (Opus)", subset="opus")
    if opus["utilization"] > 0:
        windows.append(opus)
    return windows


# ------------------------------------------------ where the tokens actually go
#
# Anthropic's usage endpoint reports account-wide windows with no per-project
# breakdown, so "which project ate my week" can only be answered from Claude
# Code's own session logs — which exist on *this* computer only. The board
# labels the screen accordingly; work done from another machine is invisible
# here, and quietly under-reporting would be worse than saying so.
#
# Shares are percentages of the window's measured tokens, not of a plan limit.
# That sidesteps the estimated-budget problem entirely: the same measured
# counts go into every project, so the ranking holds even where an absolute
# percent-of-limit would be a guess.

PROJECT_WINDOW_SECS = FIVE_HOURS
PROJECT_WINDOW_LABEL = "5h"
MAX_PROJECTS = 5


def get_project_shares(seconds=PROJECT_WINDOW_SECS, top=MAX_PROJECTS):
    """Rank this computer's projects by tokens spent in the trailing window.

    Returns (ranked, hidden) where `hidden` is how many projects fell outside
    the top N. Shares are of the whole window, so the visible ones won't add
    up to 100% when anything is hidden — the board says "+N more" rather than
    letting the missing percentage read as a rounding error."""
    root = os.path.join(os.path.expanduser("~"), ".claude", "projects")
    if not os.path.isdir(root):
        return [], 0
    cutoff = time.time() - seconds
    totals = {}
    for ts, _model, tok, key in read_events(root, since=cutoff):
        if ts >= cutoff and tok:
            totals[key] = totals.get(key, 0) + tok
    grand = sum(totals.values())
    if not grand:
        return [], 0
    totals = _roll_up_nested(totals)
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    labels = _label_projects([k for k, _ in ranked[:top]])
    shown = [{"name": labels[k], "share": round(100.0 * tok / grand, 1)}
             for k, tok in ranked[:top]]
    return shown, max(0, len(ranked) - len(shown))


# ------------------------------------------------------------------- push loop

def push(pi_url, token, payload):
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Push-Token"] = token
    req = urllib.request.Request(pi_url.rstrip("/") + "/api/push",
                                 data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _pair_hmac(code, msg):
    """HMAC-SHA256(code, msg) as lowercase hex — must match the firmware."""
    return hmac.new(code.encode(), msg, hashlib.sha256).hexdigest()


def _pair_post(url, path, data=None, headers=None, timeout=15):
    req = urllib.request.Request(url.rstrip("/") + path, data=data,
                                 headers=headers or {}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def pair_device(url, token="", code=None, ask_code=None):
    """Hand this computer's existing Claude login to a board (Yoyu) so
    it can poll usage on its own — the user never copies a token by hand.

    The token is only sent after we prove the endpoint is the real board: it
    shows a one-time code on its screen, and we HMAC-challenge it with that code
    before transmitting anything. A discovery-race impostor never learns the
    code, so it never receives the login. If a push token is configured, that
    authorizes pairing directly instead.
    """
    creds, _ = read_creds()
    if not creds:
        _print_no_claude()
        return False
    oauth = {
        "accessToken": creds["accessToken"],
        "refreshToken": creds.get("refreshToken"),
        "expiresAt": creds.get("expiresAt", 0),
        "subscriptionType": creds.get("subscriptionType"),
    }
    body = json.dumps(oauth).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    if token:
        headers["X-Push-Token"] = token
    else:
        # 1. Ask the board to enter pairing mode — it shows a code on its screen.
        try:
            _pair_post(url, "/api/pair/start", timeout=10)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            print(f"Couldn't reach the board at {url}: {exc}", file=sys.stderr)
            return False
        # 2. Get that code from the user (out-of-band — this is the whole point).
        if code is None:
            prompt = "Enter the 6-character code shown on your board's screen: "
            code = ask_code() if ask_code else input(prompt)
        code = (code or "").strip().upper()
        if not code:
            print("No pairing code entered.", file=sys.stderr)
            return False
        # 3. Prove the endpoint knows the code BEFORE sending the token.
        nonce = secrets.token_hex(16)
        try:
            ch = _pair_post(url, "/api/pair/challenge", nonce.encode(),
                            {"Content-Type": "text/plain"}, timeout=10)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            print(f"Couldn't reach the board at {url}: {exc}", file=sys.stderr)
            return False
        if not ch.get("ok") or not hmac.compare_digest(
                ch.get("mac", ""), _pair_hmac(code, nonce.encode())):
            print("That code didn't match the board. Double-check the screen and "
                  "retry — if it keeps failing, the device that answered may not "
                  "be your board.", file=sys.stderr)
            return False
        # 4. Endpoint proven. MAC the token so the board also confirms we hold
        #    the code (stops a random LAN device overwriting the login).
        nonce2 = secrets.token_hex(16)
        headers["X-Pair-Nonce"] = nonce2
        headers["X-Pair-Mac"] = _pair_hmac(code, nonce2.encode() + body)

    try:
        result = _pair_post(url, "/api/pair", body, headers, timeout=20)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"Couldn't reach the board at {url}: {exc}", file=sys.stderr)
        return False
    if not result.get("ok"):
        print(f"Board rejected pairing: {result.get('error')}", file=sys.stderr)
        return False
    live = result.get("live")
    print(f"Paired {url} — the board updates itself now"
          + ("." if live else " (first read pending; it will retry)."))
    print("Tip: use a SEPARATE Claude login for the board. If it shares this "
          "computer's login, the two will rotate each other's token and log "
          "each other out.")
    return True


def _config_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "companion.config.json")


# ------------------------------------------------------ auto-discover the Pi

def _probe(url):
    try:
        req = urllib.request.Request(url.rstrip("/") + "/api/status")
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("app") in (APP_MARKER,) + LEGACY_MARKERS
    except Exception:
        return False


def _local_prefixes():
    """Every /24 this computer sits on. Covers machines with more than one
    adapter (Wi-Fi + Ethernet, VPNs, Hyper-V/WSL) where the board may be on a
    different interface than the default route."""
    prefixes = []

    def add(ip):
        if (ip and ip.count(".") == 3 and not ip.startswith("127.")
                and not ip.startswith("169.254.")):
            p = ip.rsplit(".", 1)[0]
            if p not in prefixes:
                prefixes.append(p)

    try:  # the interface used to reach the internet (first, most likely)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:  # every other IPv4 the host knows about
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            add(info[4][0])
    except OSError:
        pass
    return prefixes


def discover_pi(port=8080):
    """Find the tracker on the LAN with no address typing. Returns URL or None."""
    # yoyu.local first, then the pre-rename hostnames so an older board on the
    # LAN is still found without the user knowing anything changed.
    for host in ("yoyu.local", "headroom.local", "claudetracker.local",
                 "claudecounter.local"):
        url = f"http://{host}:{port}"
        if _probe(url):
            return url
    prefixes = _local_prefixes()
    if not prefixes:
        return None
    urls = [f"http://{p}.{i}:{port}" for p in prefixes for i in range(1, 255)]
    print("Looking for your tracker on the network...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as ex:
        futures = {ex.submit(_probe, u): u for u in urls}
        for fut in concurrent.futures.as_completed(futures):
            try:
                if fut.result():
                    return futures[fut]
            except Exception:
                pass
    return None


def save_pi(url):
    path = _config_path()
    data = {}
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            data = {}
    data["pi"] = url
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


# --------------------------------------------------------- run on every login

INSTALLED_MARKER = os.path.expanduser("~/.claudetracker-companion-installed")


def _launch_argv():
    """How to relaunch *this* companion at login. For a PyInstaller-frozen app
    that's just the executable itself (its __file__ lives in a temp dir that is
    gone after exit); from source it's `python thisfile.py`."""
    if getattr(sys, "frozen", False):
        return [os.path.abspath(sys.executable)]
    return [sys.executable or "python3", os.path.abspath(__file__)]


def install_autostart():
    """Set the companion to launch at login. Returns a human-readable path."""
    argv = _launch_argv()
    if sys.platform == "win32":
        # Frozen: run the exe directly. From source: prefer pythonw (no console).
        if not getattr(sys, "frozen", False) and argv[0].lower().endswith("python.exe"):
            argv[0] = argv[0][:-len("python.exe")] + "pythonw.exe"
        cmd = " ".join(f'"{a}"' for a in argv)
        startup = os.path.join(os.environ.get("APPDATA", ""), "Microsoft",
                               "Windows", "Start Menu", "Programs", "Startup")
        os.makedirs(startup, exist_ok=True)
        target = os.path.join(startup, _WIN_AUTOSTART_NAMES[0])
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(f'@echo off\r\nstart "" {cmd}\r\n')
        return target
    if sys.platform == "darwin":
        d = os.path.expanduser("~/Library/LaunchAgents")
        os.makedirs(d, exist_ok=True)
        target = os.path.join(d, "com.claudetracker.companion.plist")
        args_xml = "".join(f"<string>{a}</string>" for a in argv)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.claudetracker.companion</string>
  <key>ProgramArguments</key>
  <array>{args_xml}</array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>""")
        subprocess.run(["launchctl", "unload", target],
                       capture_output=True)
        subprocess.run(["launchctl", "load", target], capture_output=True)
        return target
    # linux
    d = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(d, exist_ok=True)
    target = os.path.join(d, "claudetracker-companion.service")
    exec_start = " ".join(argv)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(f"""[Unit]
Description=Yoyu companion
After=network-online.target

[Service]
ExecStart={exec_start}
Restart=always
RestartSec=30

[Install]
WantedBy=default.target
""")
    subprocess.run(["systemctl", "--user", "enable", "--now",
                    "claudetracker-companion"], capture_output=True)
    return target


# Every Windows autostart filename this project has ever written. The product
# has been renamed twice, install_autostart() only ever writes the current name,
# and an entry it does not know about keeps launching a companion at every login
# forever. Found in the wild: a machine still had ClaudeTrackerCompanion.bat from
# two names ago, quietly starting the companion after --uninstall reported
# success, because the previous fix for exactly this bug only went back one
# generation. Append here, never replace.
_WIN_AUTOSTART_NAMES = (
    "YoyuCompanion.bat",              # current
    "HeadroomCompanion.bat",          # Headroom Mini
    "ClaudeTrackerCompanion.bat",     # the original
)


def _win_startup_dir():
    return os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                        "Start Menu", "Programs", "Startup")


def sweep_stale_autostart(startup_dir=None):
    """Delete Windows Startup entries this project wrote under an older name.

    --uninstall only helps people who run it. Everyone who upgraded through an
    earlier name still has a stale entry launching a companion at every login,
    polling Anthropic on the same account as everything else -- and two pollers
    on one account is what rate-limits a board into showing nothing. They have
    no way to know that, so the fix cannot be a command they have to find.

    Deliberately conservative about what it deletes, because this is somebody
    else's Startup folder:
      * only names this project has written, never the current one;
      * only if the file actually launches a companion, so an unrelated file
        that happens to share the name survives;
      * and it says what it removed rather than doing it silently.
    """
    if os.name != "nt":
        return []               # the macOS and Linux unit names never changed
    d = startup_dir or _win_startup_dir()
    removed = []
    for name in _WIN_AUTOSTART_NAMES[1:]:      # [0] is the current name: keep it
        path = os.path.join(d, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                body = fh.read()
        except OSError:
            continue
        if "companion" not in body.lower():
            continue            # same name, not ours -- leave it alone
        try:
            os.remove(path)
            removed.append(path)
        except OSError:
            pass
    return removed


def uninstall_autostart():
    removed = []
    paths = [os.path.join(_win_startup_dir(), n) for n in _WIN_AUTOSTART_NAMES]
    paths += [
        # The macOS and Linux unit names never changed, so there is only ever
        # one of each to remove.
        os.path.expanduser("~/Library/LaunchAgents/"
                           "com.claudetracker.companion.plist"),
        os.path.expanduser("~/.config/systemd/user/"
                           "claudetracker-companion.service"),
    ]
    for p in paths:
        if os.path.isfile(p):
            try:
                os.remove(p)
                removed.append(p)
            except OSError:
                pass
    for m in (INSTALLED_MARKER,):
        if os.path.isfile(m):
            os.remove(m)
    return removed


def load_config():
    cfg = {"pi": None, "token": "", "interval": 120, "plan": "max"}
    data = {}
    path = _config_path()
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            cfg.update({k: data[k] for k in ("pi", "token", "interval")
                        if k in data})
            if data.get("plan") in PLAN_PRESETS:
                cfg["plan"] = data["plan"]
            # Optional: remap what the board's Actions screen types, e.g.
            # {"action_keys": {"cancel": "ctrl+c"}}
            if isinstance(data.get("action_keys"), dict):
                cfg["action_keys"] = {str(k): str(v) for k, v
                                      in data["action_keys"].items()}
        except (OSError, ValueError) as exc:
            print(f"Ignoring bad companion.config.json: {exc}", file=sys.stderr)
    # Estimation budgets: start from the plan preset, then apply any overrides.
    cfg["limits"] = dict(PLAN_PRESETS[cfg["plan"]])
    if isinstance(data.get("limits"), dict):
        cfg["limits"].update(data["limits"])
    return cfg


def _print_no_claude():
    """A clear, actionable message when there's no Claude Code login to read."""
    claude_dir = os.path.join(os.path.expanduser("~"), ".claude")
    print("", file=sys.stderr)
    print("Can't find your Claude usage on this computer.", file=sys.stderr)
    if os.path.isdir(claude_dir):
        print("  Claude Code is installed here, but you're not signed in.",
              file=sys.stderr)
        print("  Fix: open a terminal, run  claude  , then type  /login .",
              file=sys.stderr)
    else:
        print("  Claude Code (the CLI) isn't installed on this computer.",
              file=sys.stderr)
        print("  The tracker reads Claude Code's own login to get your real",
              file=sys.stderr)
        print("  usage, so it needs Claude Code installed and signed in HERE.",
              file=sys.stderr)
        print("  Install:  npm install -g @anthropic-ai/claude-code",
              file=sys.stderr)
        print("  then run  claude  and type  /login .", file=sys.stderr)
    print("  (Run this companion on the same computer where you use Claude "
          "Code — not on the Pi.)", file=sys.stderr)


def run_once(cfg):
    """One poll+push cycle. Returns (ok, retry_after_seconds, rate_limited)."""
    try:
        live = get_live_windows()
    except LiveUnavailable as exc:
        # A login exists but live usage is temporarily unreadable (rate
        # limit, network blip). Skip this push: the tracker keeps showing
        # the last REAL numbers instead of wrong log-based estimates.
        print(f"live usage unavailable ({exc}); skipping this push so the "
              "tracker keeps its last real reading", file=sys.stderr)
        return False, min(900, exc.retry_after), exc.rate_limited
    if live:
        windows, plan = live
        source = "live"
    else:
        # No Claude Code login on this machine at all -> estimation is the
        # best we can do (clearly tagged as such).
        windows = get_log_windows(cfg["limits"])
        plan, source = None, "estimated"
        if not windows:
            _print_no_claude()
            return False, 0, False
    payload = {"windows": windows, "plan": plan, "source": source}
    # Project shares ride along on both paths. They come from the local logs
    # even when the windows above are live, because the live endpoint has no
    # per-project breakdown to offer — the two answer different questions and
    # are not expected to agree.
    try:
        projects, hidden = get_project_shares()
    except OSError as exc:                       # unreadable logs shouldn't
        projects, hidden = [], 0                 # cost you the usage push
        print(f"(couldn't read project usage: {exc})", file=sys.stderr)
    # Sent unconditionally, empty included. The firmware reads an absent key as
    # "keep what you have" (so an older companion doesn't blank the screen), so
    # omitting it on a quiet window would leave this morning's ranking on
    # display under a caption claiming it covers the last 5 hours.
    payload["projects"] = projects
    payload["projects_window"] = PROJECT_WINDOW_LABEL
    payload["projects_more"] = hidden
    # cfg["pi"] may be a comma-separated list — one companion can feed
    # several trackers (e.g. a Pi on the desk and a Mini on the shelf).
    targets = [t.strip() for t in str(cfg["pi"]).split(",") if t.strip()]
    delivered = 0
    for target in targets:
        try:
            result = push(target, cfg["token"], payload)
        except (urllib.error.URLError, OSError) as exc:
            print(f"Couldn't reach the tracker at {target}: {exc}",
                  file=sys.stderr)
            continue
        if result.get("ok"):
            delivered += 1
        else:
            print(f"{target} rejected the push: {result.get('error')}",
                  file=sys.stderr)
    if delivered == 0:
        return False, 0, False
    tag = "LIVE" if source == "live" else "estimated"
    summary = ", ".join(f"{w['label'].split(' (')[0]} {w['utilization']}%"
                        for w in windows)
    where = f" -> {delivered}/{len(targets)} trackers" if len(targets) > 1 else ""
    print(f"pushed [{tag}]{where}: {summary}")
    return True, 0, False


# ---- Actions: a tap on the board becomes a keystroke on this computer ------
#
# Off unless you pass --actions. Synthesising keypresses is a real capability,
# so it is never enabled behind your back. The board only ever queues an action
# when someone physically taps its screen — nothing on the network can inject
# one — but the keystroke lands in whatever window happens to be focused here,
# which is why this is opt-in.

DEFAULT_ACTION_KEYS = {
    "voice": "space",         # Claude Code voice mode
    "mode": "shift+tab",      # cycle mode
    "cancel": "escape",       # interrupt
}
ACTION_POLL_SECS = 1.0        # a button has to feel immediate
ACTION_ERROR_BACKOFF = 5.0    # board unreachable: stop hammering it


_MODIFIERS = {"shift", "ctrl", "alt", "cmd"}


def _has_real_key(parts):
    """A combo must contain something other than modifiers — 'shift' on its own
    isn't a shortcut, and silently pressing a bare modifier looks like a bug."""
    return any(p not in _MODIFIERS for p in parts)


def _send_keys_windows(combo):
    import ctypes
    VK = {"space": 0x20, "tab": 0x09, "shift": 0x10, "ctrl": 0x11,
          "alt": 0x12, "escape": 0x1B, "enter": 0x0D}
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    if not _has_real_key(parts):
        return False
    codes = []
    for p in parts:
        if p in VK:
            codes.append(VK[p])
        elif len(p) == 1 and p.isalnum():   # plain letters/digits: VK == ASCII
            codes.append(ord(p.upper()))
        else:
            return False
    user32 = ctypes.windll.user32
    for code in codes:                       # press in order
        user32.keybd_event(code, 0, 0, 0)
    for code in reversed(codes):             # release in reverse
        user32.keybd_event(code, 0, 2, 0)    # 2 = KEYEVENTF_KEYUP
    return True


def _send_keys_macos(combo):
    # Needs Accessibility permission for whatever runs this (Terminal, or the
    # packaged app): System Settings -> Privacy & Security -> Accessibility.
    CODE = {"space": 49, "tab": 48, "escape": 53, "enter": 36}
    MOD = {"shift": "shift down", "ctrl": "control down",
           "alt": "option down", "cmd": "command down"}
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    mods = [MOD[p] for p in parts if p in MOD]
    rest = [p for p in parts if p not in MOD]
    if len(rest) != 1:
        return False
    key = rest[0]
    using = f" using {{{', '.join(mods)}}}" if mods else ""
    if key in CODE:
        target = f"key code {CODE[key]}"
    elif len(key) == 1 and key.isalnum():   # plain character
        target = f'keystroke "{key}"'
    else:
        return False
    script = f'tell application "System Events" to {target}{using}'
    subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    return True


def _send_keys_linux(combo):
    XDO = {"space": "space", "tab": "Tab", "escape": "Escape",
           "enter": "Return", "shift": "shift", "ctrl": "ctrl", "alt": "alt"}
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    if not _has_real_key(parts):
        return False
    keys = []
    for p in parts:
        if p in XDO:
            keys.append(XDO[p])
        elif len(p) == 1 and p.isalnum():   # xdotool takes plain chars as-is
            keys.append(p)
        else:
            return False
    subprocess.run(["xdotool", "key", "+".join(keys)],
                   capture_output=True, timeout=5)
    return True


def send_keys(combo):
    """Type a combo like 'shift+tab' here. Returns True if it was delivered."""
    try:
        if sys.platform.startswith("win"):
            return _send_keys_windows(combo)
        if sys.platform == "darwin":
            return _send_keys_macos(combo)
        return _send_keys_linux(combo)
    except FileNotFoundError:
        print("Actions need 'xdotool' installed to send keystrokes "
              "(sudo apt install xdotool).", file=sys.stderr)
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"Couldn't send keystroke: {exc}", file=sys.stderr)
        return False


def poll_actions(url, token, keymap):
    """Collect button presses from the board and replay them as keystrokes.
    Runs forever; intended for a daemon thread."""
    url = url.rstrip("/") + "/api/actions"
    headers = {"X-Push-Token": token} if token else {}
    while True:
        delay = ACTION_POLL_SECS
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for name in data.get("actions") or []:
                combo = keymap.get(name)
                if not combo:
                    print(f"(board asked for unknown action {name!r})",
                          file=sys.stderr)
                    continue
                if send_keys(combo):
                    print(f"action: {name} -> {combo}")
        except (urllib.error.URLError, OSError, ValueError):
            delay = ACTION_ERROR_BACKOFF     # board asleep/offline; try later
        time.sleep(delay)


LOCK_PORT = 47823   # localhost mutex so two companions can't double-poll


def _single_instance():
    """Bind a localhost port as a process-wide lock. Returns the socket to
    hold for our lifetime, or None if another companion already has it."""
    import socket as _socket
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", LOCK_PORT))
        s.listen(1)
        return s
    except OSError:
        s.close()
        return None


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser(description="Yoyu companion")
    ap.add_argument("--pi", default=cfg["pi"],
                    help="tracker URL(s), comma-separated for multiple "
                         "devices (auto-discovered if omitted)")
    ap.add_argument("--token", default=cfg["token"])
    ap.add_argument("--interval", type=int, default=cfg["interval"])
    ap.add_argument("--once", action="store_true", help="push once and exit")
    ap.add_argument("--pair", nargs="?", const="", default=None, metavar="URL",
                    help="send this computer's Claude login to a board so it "
                         "runs self-contained, then exit (board auto-found if "
                         "no URL is given). The board shows a one-time code you "
                         "confirm, so the login only goes to your real board.")
    ap.add_argument("--pair-code", default=None, metavar="CODE",
                    help="the code shown on the board's screen (otherwise you "
                         "are prompted for it during --pair)")
    ap.add_argument("--actions", action="store_true",
                    help="let the board's Actions screen send keystrokes to "
                         "this computer (off by default; the keypress lands in "
                         "whatever window is focused here)")
    ap.add_argument("--no-install", action="store_true",
                    help="don't add to startup")
    ap.add_argument("--uninstall", action="store_true",
                    help="remove from startup and exit")
    args = ap.parse_args()

    if args.pair is not None:
        url = args.pair
        if not url:
            print("Looking for your board on the network...")
            url = discover_pi()
        if not url:
            ap.error("couldn't find a board on your network. Make sure it's "
                     "powered on and on the same Wi-Fi, or pass the address "
                     "shown on its screen: --pair http://<its-address>:8080")
        sys.exit(0 if pair_device(url, token=args.token,
                                  code=args.pair_code) else 1)

    if args.uninstall:
        removed = uninstall_autostart()
        print("Removed:\n  " + "\n  ".join(removed) if removed
              else "Nothing to remove.")
        return

    cfg["pi"], cfg["token"], cfg["interval"] = args.pi, args.token, args.interval
    if not cfg["pi"]:
        cfg["pi"] = discover_pi()
        if cfg["pi"]:
            print(f"Found your tracker at {cfg['pi']}")
            save_pi(cfg["pi"])
        else:
            ap.error("couldn't find the tracker on your network. Make sure it's "
                     "powered on and on the same Wi-Fi, or pass "
                     "--pi http://<its-address>:8080")

    if args.once:
        print(f"Yoyu companion -> {cfg['pi']} (single push)")
        ok, _, _ = run_once(cfg)
        sys.exit(0 if ok else 1)

    lock = _single_instance()
    if lock is None:
        print("Another Yoyu companion is already running on this computer "
              "(probably the auto-started one) — exiting so we don't "
              "double-poll Anthropic. To run this one instead, stop the other "
              "first (or reboot after --uninstall).")
        return

    print(f"Yoyu companion -> {cfg['pi']} (every {cfg['interval']}s)")
    if args.actions:
        # First target only: keystrokes land on this computer, so a second
        # board sending them here would just be two remotes for one keyboard.
        board = str(cfg["pi"]).split(",")[0].strip()
        keymap = dict(DEFAULT_ACTION_KEYS)
        keymap.update(cfg.get("action_keys") or {})
        threading.Thread(target=poll_actions, daemon=True,
                         args=(board, cfg["token"], keymap)).start()
        print(f"Actions enabled: taps on {board} will type here.")
    # Before anything else touches autostart: clear out entries left by older
    # names of this product, which would otherwise keep starting a second
    # companion at every login for as long as the machine lives.
    for stale in sweep_stale_autostart():
        print("Removed a leftover auto-start entry from an older version:\n"
              f"  {stale}")
    first_ok, _, _ = run_once(cfg)
    if first_ok and not args.no_install and not os.path.isfile(INSTALLED_MARKER):
        try:
            where = install_autostart()
            with open(INSTALLED_MARKER, "w", encoding="utf-8") as fh:
                fh.write(cfg["pi"])
            print(f"Set to run automatically at login.\n  {where}\n"
                  "  (run with --uninstall to stop)")
        except Exception as exc:  # noqa: BLE001
            print(f"(couldn't set auto-start: {exc})", file=sys.stderr)
    # When Anthropic rate-limits the usage endpoint (HTTP 429), stop hammering
    # it: back off exponentially (2x per consecutive 429, capped at 30 min) and
    # honour any Retry-After the server sends as a floor. A single good read
    # resets us to the normal cadence.
    base = max(30, cfg["interval"])
    rl_backoff = 0
    while True:
        time.sleep(base + rl_backoff)
        _ok, retry_after, rate_limited = run_once(cfg)
        if rate_limited:
            rl_backoff = min(1800, max(retry_after, rl_backoff * 2 or base))
            print(f"rate limited by Anthropic — backing off, next try in "
                  f"~{base + rl_backoff}s (staying quiet so we stop hammering "
                  "the usage endpoint)", file=sys.stderr)
        else:
            if rl_backoff:
                print("usage endpoint recovered — back to normal cadence",
                      file=sys.stderr)
            rl_backoff = 0


if __name__ == "__main__":
    main()
