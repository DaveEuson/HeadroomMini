# Headroom companion

Runs on the **computer where you use Claude Code** and feeds your usage to the
board.

> **Requires the Claude Code CLI signed in on this computer** for live numbers —
> the companion reuses that login (it can't sign in on its own). If you only use
> Claude in a browser or the desktop app, it falls back to a rough estimate from
> local logs. See "Why this exists" below.

## Tray app (menubar / system tray)

`tray.py` is the friendly version — it lives in your menubar (macOS) or system
tray (Windows/Linux) instead of a terminal. The icon is green when it's feeding
the board, amber while it's searching, red when it's stuck; the menu has
one-click **Pair** (make the board self-contained), **Open board page**, a
**Feeding** toggle, and a **Settings** submenu that opens the board's own config
pages (screens & clock, phone alerts, firmware update) in your browser. It
reuses everything below.

```
pip install pystray pillow certifi        # + pyobjc-framework-Cocoa on macOS
python tray.py
```

(A packaged, double-click build will ship with a release once it's verified on
each OS — until then, run it from source as above.)

## Why this exists

The Pi can't sign in to Anthropic directly — the fresh OAuth sign-in endpoint
is heavily throttled for anything that isn't Claude Code itself. So instead of
signing in, this script **reuses Claude Code's login that's already on your
computer**: it reads the token Claude Code saved, refreshes it if needed, and
reads Anthropic's real usage endpoint — the exact numbers Claude Code's own
`/usage` shows. It then pushes those to the Pi every couple of minutes. It
never does a sign-in, so it never hits the throttle. (Same technique the
Sparko "Fuel" widget uses.)

If Claude Code isn't logged in on this machine, it falls back to *estimating*
usage from Claude Code's local logs (`~/.claude/projects`).

## Setup

### Easiest: the double-click app (no Python)

Open `http://<tracker-address>:8080` (the address is shown on the tracker's
screen) — or go straight to the [latest release] — and download
**HeadroomCompanion** for your OS. Double-click it. Done.

[latest release]: https://github.com/DaveEuson/HeadroomMini/releases/latest

That download **is the tray app** — a green/amber/red icon appears in your
menubar (macOS) or system tray (Windows/Linux). On first run it **finds the
tracker on your network by itself**, sends the first reading, and (once a feed
succeeds) **sets itself to run at every login** — so you do this once and never
again. (First launch: macOS → right-click → **Open**; Windows → **More info →
Run anyway**, since the binary isn't code-signed yet.) Right-click / click the
icon for **Pair**, **Settings**, **Start at login**, and a **Feeding** toggle.

There's also a **HeadroomCompanion-cli** asset — the same thing without a UI,
for headless servers or debugging (run it from a terminal to watch the
`pushed [LIVE]: …` output).

These apps are produced automatically by CI on every tagged release
(see [BUILD.md](BUILD.md) and `.github/workflows/release.yml`).

### Or run the script

You need Python 3 (already on macOS/Linux; on Windows install from
[python.org](https://www.python.org/downloads/) and tick "Add to PATH").

1. Copy this `companion/` folder to the computer where you run Claude Code
   (or clone the repo there).
2. Run it:

   ```bash
   python3 companion.py
   ```

Same behavior: auto-discovers the tracker, feeds it, and installs itself to run
at login. (If auto-discovery can't find it, pass
`--pi http://<its-address>:8080`, shown on the tracker screen.)

- Stop it auto-running: `python3 companion.py --uninstall`
- Don't auto-install in the first place: add `--no-install`

## Configure without flags

Copy `companion.config.example.json` to `companion.config.json` next to
`companion.py` and fill it in:

```json
{
  "pi": "http://claudecounter.local:8080",
  "token": "",
  "interval": 120,
  "plan": "max"
}
```

`"plan"` is `"max"` or `"pro"` and just picks the fallback estimation budgets
(Pro's are ~1/5 of Max's). It only matters when there's no Claude Code login to
read — live numbers ignore it. Add an explicit `"limits": { … }` object to
override the budgets by hand.

## About the percentages

When Claude Code is logged in on this machine (the normal case), the numbers
are **the real thing** — Anthropic's own utilization windows, identical to what
`claude /usage` shows. The companion prints `pushed [LIVE]: …` when it's using
them.

Only if it *can't* read a Claude Code login does it fall back to *estimating*
from local logs (`pushed [estimated]: …`). In that mode the percentages are
measured against the token budgets in `limits`, which you can tune — the reset
timing and usage amounts are still accurate, just the % is a guess.

**Requires Claude Code signed in on this computer** for live numbers. If Sparko's
"Fuel" widget works for you, you already have this.

## Actions: use the board as a shortcut pad

The board's **Actions** screen can send keystrokes to the computer running
Claude Code — swipe up/down to pick a shortcut, tap to fire it. Defaults:

| Action | Sends | For |
|---|---|---|
| Voice mode | `space` | Claude Code voice mode |
| Mode toggle | `shift+tab` | cycle mode |
| Interrupt | `escape` | stop the current run |

**It is off unless you ask for it:**

```bash
python companion.py --actions
```

Synthesising keypresses is a real capability, so it is never enabled behind
your back. The keystroke lands in **whatever window is focused** on this
computer, so keep that in mind before enabling it. The board only queues an
action when someone physically taps its screen — nothing on the network can
inject one — and unclaimed presses expire after 15 seconds so a tap made while
the companion was closed can't fire later.

Remap what each button types via `companion.config.json`:

```json
{ "action_keys": { "cancel": "ctrl+c" } }
```

Platform notes: **Windows** works out of the box; **macOS** needs Accessibility
permission for whatever runs the companion (System Settings → Privacy &
Security → Accessibility); **Linux** needs `xdotool` (`sudo apt install
xdotool`).

## Projects: where the tokens actually went

The board's **Projects** screen ranks your projects by share of the last 5
hours' tokens — top 5, with "+N more" when others fall below the cut. Nothing
to enable; the companion sends it with every push.

**It only ever describes this computer.** Anthropic's usage endpoint reports
account-wide windows with no per-project breakdown, so the ranking is built
from Claude Code's own session logs under `~/.claude/projects` — which exist
locally. Work you did from another machine, or on the web, won't appear. The
screen labels itself "this computer" for that reason.

It also answers a different question from the meters, and the two aren't
expected to agree:

| | Meters / Timer | Projects |
|---|---|---|
| Source | Anthropic usage API (live) | local session logs |
| Scope | your whole account | this computer |
| Units | % of your plan's window | % of tokens measured in the window |

Shares are percentages of the tokens actually measured, not of a plan limit.
That keeps the ranking trustworthy even when an absolute percent-of-limit would
be an estimate — every project is counted the same way.

**Nested directories roll up.** Claude Code keys a project off the working
directory, so opening a repo, a subdirectory of it, and a package inside that
would otherwise be three rows that each understate the work. Each one folds
into the nearest ancestor that is *also* a project you've worked in — an
ancestor you never opened is never invented as a grouping.

Project names come from each event's own `cwd`, not the folder name under
`~/.claude/projects`. Those folder names are path-mangled and can't be reversed:
`H--Projects-Kiosk-Grand` is the project "Kiosk Grand", but nothing in the slug
distinguishes a `-` that was a path separator from one that was in the name.

## Troubleshooting

Hitting "login expired", a 404 / "couldn't reach the board", "rate limited", or
"another companion is already running"? See the
[troubleshooting guide](../docs/TROUBLESHOOTING.md) — most issues come down to
the board being reached at the wrong address (e.g. two devices sharing
`headroom.local`) or a shared-account login expiring.

## Security

If your board's `config.json` sets a `push_token`, pass the same value with
`--token` (or in the config file). Then only your companion can post data to
the board. On a home network it's optional but nice to have.
