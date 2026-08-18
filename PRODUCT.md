# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

Recorded as `web` because that is the platform value the design-language
references key off, and the setup page is the only surface they apply to. Two
of the four in-scope surfaces are **not** web and must not be treated as such:
the on-device UI is embedded C++ drawing directly to a 240×320 ST7789, and the
companion is a Python desktop tray app. See *Capabilities and Constraints*.

## Users

The primary user is a **Claude Code heavy user who buys the board** — someone
who works in Claude Code most days, runs into usage limits, and wants a
finished appliance rather than a project. They are not assumed to be an
embedded developer: the intended path is buy the board, flash it from a browser
page, and never open a terminal or a code editor.

Their situation is a desk with a computer already running Claude Code. Their
job is to know, without breaking focus, how much headroom is left in each usage
window and when it resets — replacing a mental estimate or a trip to
`claude /usage`.

Developers and tinkerers exist as a real secondary audience (the firmware is
open source and buildable from PlatformIO), but buyers come first when the two
conflict.

## Product Purpose

Yoyu is a physical desk gadget that displays Claude usage limits at a
glance: how much of each window is left, when it resets, and a phone alert when
a window crosses a threshold.

Success over the next year is measured as **more people actually getting one
running** — completed flashes and boards left powered on desks. Drop-off
anywhere in the buy → flash → Wi-Fi → companion chain is the primary enemy;
that makes setup completion the outranking metric when it competes with other
goals.

## Positioning

The mechanism a neighboring product could not truthfully copy: the companion
**reuses the existing Claude Code CLI login** to read real usage numbers — the
same ones `claude /usage` reports — rather than performing a fresh third-party
sign-in that would hit Anthropic's login throttle. Numbers are real, not
estimated.

Supporting position: it runs entirely on one ~$26 Waveshare
ESP32-S3-Touch-LCD-2 — no Raspberry Pi, no Linux, no soldering — and installs
from a browser page with no VS Code and no command line. A deluxe Raspberry Pi
Zero 2 W variant with a full web dashboard and the "Pip" mascot lives in a
separate repo (YoyuZero); this repo is the self-contained ESP32 appliance.

## Operating Context

The setup chain, in the order a buyer meets it:

1. **Buy** the Waveshare ESP32-S3-Touch-LCD-2 (Amazon affiliate link or direct
   from Waveshare).
2. **Flash** at `https://daveeuson.github.io/Yoyu/` (`docs/index.html`)
   in Chrome or Edge on a computer, over a data USB-C cable. Phones, Safari and
   Firefox cannot flash — a real and recurring failure point.
3. **Wi-Fi** is handed to the board over the same USB cable via Improv, in the
   same browser window. Fallback: the board's own `Yoyu-Setup` hotspot
   (password `yoyu`) at `http://192.168.4.1`, used from a phone.
4. **Feed it usage** one of two ways:
   - *Push mode (default):* download and run the companion on the computer
     where Claude Code is used; it auto-discovers the board and pushes usage.
   - *Self-contained:* run the companion once with `--pair`, confirm the code
     shown on the board's screen, and the board then polls Anthropic directly
     and refreshes its own token — nothing runs on the computer afterward.

Ongoing use is ambient and non-interactive: the board sits on the desk and is
glanced at. Deliberate interaction is touch (tap, long-press, swipe) and motion
(face-down to sleep, shake to wake). Configuration happens in a browser against
the board's own IP (`/settings`, `/alerts`, `/update`) or through the companion
tray menu.

The environment is assumed to be a trusted home or office network.

## Capabilities and Constraints

**In-scope design surfaces** (all four confirmed in scope):

- `docs/index.html` — the GitHub Pages setup and flasher page. Web. Currently a
  single self-contained file; `esp-web-tools` v10.4.0 is deliberately
  **self-hosted, not CDN-loaded**, because the page collects Wi-Fi credentials.
  That constraint is binding: no third-party script or asset host on this page.
- `firmware/src/main.cpp` — the on-device UI. **Embedded C++, not LVGL**: text
  and shapes are drawn with direct TFT calls on a 2" 240×320 ST7789 IPS panel.
  Browser tooling, the bundled HTML detector, and `live` mode do not apply.
  Constraints are real: fixed bitmap font sizes, no compositing, redraw cost,
  a fixed small palette, and legibility at arm's length on a 2" screen.
- `companion/tray.py` and the companion's terminal output — a Python `pystray`
  menubar/system-tray app. Menu surface: status line, Feeding toggle, Start at
  login, Pair board, Open board page, Settings submenu (screens/clock,
  phone alerts, firmware update), Quit. The CLI's printed state matters to
  users: `[LIVE]` versus `[estimated]` is how they tell whether their numbers
  are real.
- `README.md`, `docs/TROUBLESHOOTING.md`, `docs/HARDENING.md` — the reading
  experience for evaluation and debugging.

**Device UI:** eight screens — Meters, Focus, History, Sprocket, Timer, Actions,
Projects, Settings — cycled by tap, each individually enable-able via a screen
mask. Meters cover
every usage window Claude reports (5-hour session, weekly, weekly Opus…) in
fuel-gauge style, with amber under 30% left and red under 10%. History persists
across reboots in flash. Long-press flips "% left" / "% used"; swipe changes
brightness; overnight dimming is on by default.

**Running out:** when a window reaches 0% left, the board puts the Timer screen
up by itself — a full-screen countdown to that window's reset. It is the one
moment the only useful number is how long until you can work again, and the one
moment the user is least likely to go tapping through screens to find it. The
countdown prefers an exhausted window over the merely soonest one, so it always
counts to the reset actually being waited on. This happens once per episode: a
tap moves off it and it stays off until that window resets and is spent again.
It never overrides a pairing code, and it respects the Timer screen being
switched off in the screen mask.

**Actions screen:** the board doubles as a shortcut pad. It queues one of three
actions — Voice mode (Space), Mode toggle (Shift+Tab), Interrupt (Esc) — which
the companion polls from `/api/actions` and synthesizes as a keystroke on the
computer. Queue depth 4, entries expire after 15s. The board only ever queues
on a physical touch, and the companion must be started with `--actions` to act
at all; nothing on the network can inject a keypress. On this screen tap and
swipe are rebound — swipes move the selection, a tap fires.

**Projects screen:** ranks where the tokens actually went — the top 5 projects
by share of the trailing 5 hours, with a "+N more" when others are below the
cut. Anthropic's usage endpoint reports account-wide windows with no
per-project breakdown, so this can only come from Claude Code's own session
logs on the computer running the companion. The screen therefore says "this
computer" out loud: work done from another machine is invisible to it, and
under-reporting silently would be worse than naming the limit. Shares are
percentages of measured tokens in the window rather than of a plan limit, which
keeps the ranking honest even where an absolute percent-of-limit would be an
estimate. Project identity comes from each event's `cwd`, not the mangled
folder name under `~/.claude/projects` — that slug can't be reversed
(`H--Projects-Kiosk-Grand` is "Kiosk Grand", not "Kiosk-Grand").

**Settings screen:** the board's own address (`ip:port`) and firmware version,
plus on-device toggles for which screens are in the rotation. It exists because
a working board previously showed its address nowhere — it appeared only on the
not-yet-set-up and error screens — so there was no route from the device to its
own configuration pages. Swipes move the cursor, a tap toggles a row. Three
toggles are refused with a reason: the Settings screen itself, the power-on
default, and anything that would leave fewer than two screens. Those guards run
in the disable direction only — a Settings row the web form has switched off can
still be switched back on from the device. The web form at `/settings` can do
all three.

There is deliberately **no double-tap shortcut**. Touch dispatches on finger
release, so the first tap of a double-tap is already delivered as a plain tap
before the double-tap code arrives — on the Actions screen that would queue a
real keystroke to the computer and *then* jump. Correcting it would mean
holding every tap ~250 ms to see whether a second follows, which is visible lag
on "next screen" for a shortcut that only duplicates paging.

**Security constraints that design must not undercut:** verified TLS against a
pinned root CA set on every outbound connection (no `setInsecure()`); OTA
images verified against a public key baked into the firmware; pairing requires
a one-time code shown on the physical screen before a login is handed over.

**Known recurring failure modes** users hit, all of which have a UI cost:
"Login expired – re-pair" when the board and computer share a Claude account
and rotate each other's token; "couldn't reach the board" / 404 when two
devices answer to `yoyu.local`; rate limiting when more than one device
polls the same account; charge-only USB-C cables; unsupported browsers.

## Brand Commitments

- **Name:** Yoyu. Sibling project: YoyuZero (the Raspberry Pi
  version, mascot "Pip").
- **Sprocket** — the mascot, a pixel-art character with its own device screen
  who reacts to remaining headroom. Present as an inline pixel SVG on the setup
  page and as an animated screen on the board. Sprocket is an established asset,
  not a decoration to be swapped out.
- **Voice:** plain, concrete, reassuring about difficulty — "No terminal, no
  menubar, no estimating," "no VS Code, no command line," "you'll only do this
  once." It names costs honestly (charge-only cables, unsupported browsers,
  token rotation) instead of hiding them.
- **Authorship:** "Made by Dave Euson with ♥ in San Diego." MIT licensed,
  © 2026 Dave Euson.
- **Disclosure:** Amazon Associate affiliate disclosure appears wherever an
  affiliate link does. This is a legal requirement, not a stylistic choice.

## Evidence on Hand

- Real product photography: `docs/img/meters.jpg`, `docs/img/timer.jpg`,
  `docs/img/sprocket.jpg` — the actual board running, used in the README.
- Working firmware, companion, and tests (`companion/test_companion.py`).
- Real published docs: `docs/TROUBLESHOOTING.md`, `docs/HARDENING.md`
  (threat model), `docs/RELEASE.md`.
- Live distribution: GitHub Pages flasher and GitHub Releases binaries for
  Windows, macOS, and Linux.

**Absences future work must not fabricate:** there are no testimonials,
reviews, user counts, download numbers, star counts, press mentions, benchmarks,
or sales figures. There is no pricing for the software — it is free and MIT;
the only price is the ~$26 third-party board. Do not invent social proof.

## Product Principles

1. **Setup completion outranks everything.** Every surface is judged by whether
   it gets one more person from an unopened box to a live board. When beauty and
   completion conflict, completion wins.
2. **Assume no terminal.** The default reader does not have VS Code, PlatformIO,
   or a shell open, and should never be required to. Developer paths are
   available but never on the critical path.
3. **Name the failure before it happens.** Charge-only cables, unsupported
   browsers, shared-account token rotation, duplicate `yoyu.local` — these
   are known and predictable. Surfaces should pre-empt them in place, not bury
   them in a troubleshooting doc.
4. **Real numbers, or say so.** The product's whole claim is that these are the
   actual figures. Any state where they are estimated, stale, or unreachable
   must be legible as such, on the board and in the companion.
5. **Glanceable at arm's length.** The board is read in under a second from
   across a desk, in ambient conditions, without touching it. That constraint
   outranks density on every device screen.

## Accessibility & Inclusion

No product-specific standard has been established by the user. Two factual
constraints are worth carrying forward: the device UI is a small 2" panel read
at distance, so size and contrast carry real functional load; and usage state on
the board is signaled by color (amber under 30%, red under 10%), which should
not be the only carrier of that meaning.
