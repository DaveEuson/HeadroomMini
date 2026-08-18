---
target: docs/index.html
total_score: 22
max_score: 40
na_heuristics: 
p0_count: 2
p1_count: 2
timestamp: 2026-08-05T21-50-55Z
slug: docs-index-html
---
Method: dual-agent (A: a501a85e3c317bf60 · B: ad91f2a7c30bb921e)

Target: `docs/index.html` — the GitHub Pages setup and flasher page for Yoyu.
Mode: primarily **Operate** (a 3-step setup wizard) with a Persuade block bolted to the top. All 10 heuristics scored; none n/a.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 2 | No cross-step progress; nothing marks step 1 complete. Before the module upgrades the custom element, the activate button and both red error slots render simultaneously — three contradictory statuses at once. |
| 2 | Match System / Real World | 3 | Strong plain language ("plug the board in", "BOOT/RESET"), undercut by `--pair`, `--pi http://<board-ip>:8080`, and `[LIVE]`/`[estimated]` leaking onto a page whose footer promises "no command line". |
| 3 | User Control and Freedom | 2 | No "I already flashed, skip to step 3". Nothing says the flash is repeatable or non-destructive — at the single scariest click on the page. |
| 4 | Consistency and Standards | 2 | `.note` carries four unrelated meanings (buy ad, hard requirement, prerequisite warning, advanced option) at identical visual weight. Emoji icons (🛒 ⚙️ ⚡) clash with the flat pixel-art mascot. Footer contradicts the body on "no command line". |
| 5 | Error Prevention | 3 | Genuinely good — charge-only cable, browser/phone warning, BOOT/RESET, CLI-login note. Misses Windows SmartScreen, macOS Gatekeeper/`chmod`, guest-network/VPN, and the duplicate `yoyu.local` 404 that TROUBLESHOOTING.md ranks top-three. |
| 6 | Recognition Rather Than Recall | 2 | The board's IP "from step 2" must be memorized and carried into step 3's `<details>`, with no way to re-display it. The Claude Code CLI sign-in prerequisite is only revealed in step 3, after flashing. |
| 7 | Flexibility and Efficiency | 1 | No OS detection across the three download tiles; no copy-to-clipboard for the `--pi` command; no skip-ahead for a returning user; no path at all for a phone visitor. Weakest heuristic on the page. |
| 8 | Aesthetic and Minimalist Design | 2 | Card 3 stacks seven sibling blocks. Two `.note` blocks fire before instruction one. The primary button is unstyled while the secondary downloads are designed. |
| 9 | Error Recovery | 2 | The `unsupported` and `not-allowed` slots are dead ends — a red sentence and no action. No handling if the self-hosted module fails to load; no `<noscript>`. |
| 10 | Help and Documentation | 3 | The page's best heuristic: three `<details>` placed exactly at the point of need, plus the TROUBLESHOOTING.md footer link. Weakened because "It didn't find the board?" jumps to a terminal flag and skips TROUBLESHOOTING.md's own #1 cause (same Wi-Fi / no guest network / no VPN). |
| **Total** | | **22/40** | **Acceptable — significant improvements needed** |

## Design Specificity Verdict

**Authored copy on an interchangeable chassis.**

**LLM assessment (unanchored).** The *words* are unmistakably this product — "a charge-only cable won't work", "Hold BOOT, tap RESET", "`[LIVE]`, not `[estimated]`", "you'll only do this once". Nobody else could ship that copy. The inline Sprocket pixel-grid SVG and the cream/salmon palette are real brand assets, not decoration.

The *structure* is a stock three-step onboarding template: centered header, three cream rounded cards with numbered circles, a row of OS download tiles, muted footer. Strip the SVG and the copy and this is any ESP32 flasher page.

The damning specific: **this page contains zero pixels of the product's actual screen.** It sells a 240×320 display gadget and never shows it. `docs/img/meters.jpg`, `timer.jpg`, and `sprocket.jpg` exist, are real photographs of the working device, and are already used in README.md — but this page, the one that has to justify a purchase and survive a scary flash, uses none of them. The visitor's only mental image of success is the muted sentence "Within a minute or two the meters go live."

On mode: the page is doing two jobs, and the Persuade job is done at about 10% effort — one `.note` with a 🛒 emoji. That is less a split-focus problem than a wasted-slot problem: the buy note occupies the most valuable real estate on the page and returns almost nothing, while pushing the actual first instruction below two consecutive salmon caveat boxes.

**Deterministic scan.** The CLI detector over `docs/index.html` exits **0 (clean)** with one advisory finding: `em-dash-overuse`, 13 em-dashes in body text. The in-browser detector run against the rendered DOM found **18 anti-patterns**:

- **13 × `low-contrast`** (warning, quality — *not* advisory). `p.tag` 3.7:1; all three `span.num` step badges 3.1:1; four `.muted` paragraphs 4.1:1; three `.dl small` labels 4.3:1; `footer` and `small.muted` 3.7:1.
- **1 × `overused-font`** — 96% of text in one family. **False positive:** the page declares one stack by design, and the resolved name "roboto" is a headless font-resolution artifact.
- **1 × `em-dash-overuse`** (advisory) — 8 em-dashes in rendered body text vs. the CLI's 13 (the CLI counts `<title>`, `<meta>`, and the HTML comment, which never render). **Partly false positive:** several are structural separators, and honest-cost em-dashes are load-bearing in this brand's confirmed voice. There is a real cluster in body copy, but I would not restyle the voice over it.
- **1 × `cream-palette`** — `rgb(240,238,230)` page background. **Arguable, not clean:** `#f0eee6` is the Claude-adjacent cream, deliberate for a Claude-adjacent product. The rule is right about the pixel and wrong about the motive.
- **4 × `text-occlusion`** — **all false positives.** Every occluded node is inside a *closed* `<details>`; Chrome gives collapsed details content a layout box, so the rule reads a real rect and concludes the card covers it.

Where they agree: both assessments independently landed on the unstyled primary button and the contrast failures. A hand-computed ~2.7:1 / ~4.0:1 / ~3.1:1 from the CSS; B measured 2.687 / 4.088 / 3.122 in-page. What the detector caught that the review missed: the exact scope of the contrast problem — it is 13 nodes, not a few. What the review caught that the detector could not: every P0 and P1 below. None of them are detectable by rule.

**Visual overlays.** No user-visible overlay is available in your browser. Injection *succeeded* (title mutation and script execution both preflight-confirmed, 35 overlay nodes rendered, `[impeccable] 18 anti-patterns found`), but it ran in a headless CDP session, because the MCP browser path required disambiguating two connected Chrome extensions and a subagent cannot ask. The console findings above are the real result; the overlay itself was painted where you can't see it. Screenshots were captured instead — desktop 1440, mobile 390, five 3× focus-ring closeups, and the overlay render.

## Overall Impression

The writing on this page is better than the design of it. Someone who actually understands the failure modes wrote this copy — it names charge-only cables, unsupported browsers, and the difference between the CLI login and claude.ai, all in plain language, and it bounds each cost instead of hiding it. That instinct is the product's voice and it is working.

What undercuts it is that the page's visual hierarchy points at the wrong thing. The single action that produces your success metric — **Connect & Install** — renders as a 138.8 × 23 px unstyled system button in `rgb(240,240,240)`, while three white bordered download tiles further down look exactly like designed primary buttons. Measured, not inferred. A first-timer scrolling this page sees the download tiles as the thing to click.

The single biggest opportunity: **this page never shows the product working.** Three real photographs sit in `docs/img/`, used in the README but not here. On a page whose whole job is to carry someone through paying, flashing, and troubleshooting, there is no picture of the payoff and no end peak.

## What's Working

1. **The `<details>` placement is genuinely excellent.** "Board not showing up?" sits inside card 1, immediately after the action that fails; "It didn't find the board?" sits inside card 3. Help is co-located with the failure instead of exiled to a separate page, and it costs zero visual weight until needed. Most pages get this wrong.
2. **The failure-naming copy builds real trust.** "(a charge-only cable won't work)", "being signed into the desktop app or claude.ai isn't enough", "Phones and Safari/Firefox can't flash — but you'll only do this once". Naming a cost and immediately bounding it is a craft move, and it is consistent with README.md and TROUBLESHOOTING.md.
3. **The self-hosting decision is correctly implemented and documented in place.** `docs/vendor/esp-web-tools/` contains the full dynamic-import chunk graph locally; nothing on this page reaches an external host, and the comment at lines 156–158 explains why at the point of the decision. Verified: the module loads with zero console errors and the manifest returns 200.

## Priority Issues

### [P0] The primary CTA is unstyled, and the brand CSS meant to style it is dead code

**What.** Lines 33–34 set `--esp-tools-button-color:var(--acc-ink)` and `--esp-tools-button-background-color:var(--acc)`. The vendored library reads only `--esp-tools-button-color` (which drives the *background*, and is being handed `#fff`) and `--esp-tools-button-text-color` (never set). Worse, it doesn't matter either way: those rules live in the shadow root and style only the library's fallback button, which never displays because line 76 fills the slot. There is no `::slotted()` rule in the vendor sheet and no `esp-web-install-button button` rule on the page, so the slotted button inherits **nothing**. Measured: 138.8 × 23 px, computed background `rgb(240,240,240)`, UA default text — the smallest interactive element on the page and the worst tap target on it.

**Why it matters.** This button *is* the success metric. The three `.dl` tiles (white, bordered, `border-radius:10px`, `font-weight:600`) outrank it visually, which is precisely how a first-timer downloads the companion before flashing and runs it against a board with no firmware.

**Fix.** Style the light-DOM button directly and fix the property names:
```css
esp-web-install-button button[slot="activate"]{
  font:600 1.05rem/1 inherit; padding:16px 28px; width:100%; max-width:320px;
  background:var(--acc); color:var(--acc-ink); border:0; border-radius:12px;
  cursor:pointer; box-shadow:0 2px 6px rgba(217,119,87,.35);
}
esp-web-install-button button[slot="activate"]:hover{filter:brightness(1.06)}
esp-web-install-button button[slot="activate"]:focus-visible{outline:3px solid var(--ink);outline-offset:2px}
esp-web-install-button{--esp-tools-button-color:var(--acc);--esp-tools-button-text-color:var(--acc-ink)}
```
Then de-emphasize the `.dl` tiles so the flash button clearly outranks them.

**Suggested command:** `$impeccable polish`

### [P0] Phone visitors hit a red dead end — and phones are how this URL gets opened

**What.** On any phone `serial` is absent from `navigator`, so the element renders only "This browser can't flash — open this page in Chrome or Edge on a computer." That is the entire mobile experience. No copy-link, no QR, no mailto, no way to get the URL onto a computer. README.md line 32 points people at this URL, and links get opened on phones.

**Why it matters.** This is the largest leak in the buy → flash chain. A visitor who is willing and has already bought the board is told "no" and given nothing to act on. Every one of them has to independently remember to come back at a desk.

**Fix.** The library already sets `install-unsupported` on the host — use it. Reveal a hidden block via `esp-web-install-button[install-unsupported] ~ #on-phone{display:block}` containing the full URL as selectable text, a "Copy link" button (`navigator.clipboard.writeText`, inline, no external deps), and an "Email it to myself" mailto. Add `og:image` pointing at `img/meters.jpg` plus `og:title`/`og:description` so a shared link previews the working device instead of a bare URL.

**Suggested command:** `$impeccable adapt`

### [P1] Step 3 ends on the page's biggest unnamed failure, and never shows the payoff

**What.** Line 115 promises "no install, just double-click", then offers an unsigned `.exe` (→ Windows SmartScreen "Windows protected your PC") and an extension-less macOS binary (→ arrives non-executable and quarantined; double-clicking does nothing). Neither is pre-empted, and for macOS the promise is simply false without `chmod +x` and right-click → Open. Separately, the `--pair` note omits the on-screen confirmation code that both README.md and TROUBLESHOOTING.md treat as required — producing exactly the "no pairing code appears" support case. And "It didn't find the board?" jumps to `--pi` while TROUBLESHOOTING.md lists "same Wi-Fi, not a guest network or VPN" as cause #1.

**Why it matters.** Product principle 3 is "name the failure before it happens," and this is the last step. Peak-end means a SmartScreen wall is what the whole experience gets remembered as.

**Fix.** Add a `<details>` under the button row: *"Windows says 'protected your PC'? macOS won't open it?"* with More info → Run anyway, and the macOS `chmod +x` / right-click → Open path. Prepend the same-Wi-Fi check above the `--pi` flag. Add the on-screen code step to the `--pair` note. Close card 3 with `<img src="img/meters.jpg">` so the page ends on the payoff.

**Suggested command:** `$impeccable harden`

### [P1] The custom element's undefined and failed states are unhandled

**What.** The `<script type="module">` is deferred by definition. Until it evaluates, `esp-web-install-button` is an unknown inline element and **all three** light-DOM children render at once — the activate button plus both red error spans — and the button is clickable-but-inert during it. If the module 404s or throws, that state is permanent: a button that does nothing, two red errors, no explanation. There is no `<noscript>`. (Note: the flash-of-three-states is a reading of the DOM contract, not something either assessment observed rendered — headless Chrome reports `serial` present, so the unsupported path never painted. The unrecoverable-failure half is unambiguous.)

**Why it matters.** The first impression of the highest-stakes control is "this page is broken."

**Fix.**
```css
esp-web-install-button:not(:defined) > *{display:none}
esp-web-install-button:not(:defined)::after{content:"Starting the flasher…";color:var(--muted)}
```
Plus a `<noscript>` inside card 1.

**Suggested command:** `$impeccable harden`

### [P2] Systemic contrast failures, including on the affiliate link and the operational instructions

**What.** Measured in-page, WCAG 2.x: every link on the page (`a{color:var(--acc)}`) fails AA against all three of its rendered backgrounds — **2.687:1** on `--bg`, 2.963:1 on `--card`, 2.750:1 on the note background. That governs the Amazon affiliate link, the Waveshare link, the troubleshooting link, and the GitHub link. `.muted` is **4.088:1** on card and **3.707:1** on page background, and it carries real instructions ("Pick the board's port when asked… Takes about a minute") plus the entire footer and all three download sub-labels at 12.8px. The three `.num` step badges are **3.122:1** — and at 15.2px bold they are *not* WCAG-large, so 4.5 applies, not 3.0.

Separately: the FTC affiliate disclosure sits in the 12px footer at 3.707:1, several screens below the Amazon link it discloses. "Clear and conspicuous" is a stretch. The Amazon link also has no `rel="sponsored"`.

**Why it matters.** People read this on a laptop in daylight, and the failing text includes the buy link, the port-picking instruction, and the reassurance line at the scariest moment.

**Fix.** Add `--acc-text:#b4442a` (your existing `.unsupported` colour, 5.244:1 — already on the page and passing) and use it for `a{}`; darken `--muted` to about `#6b6759`; put `--ink` on `.num` or darken the accent behind it. Move a short disclosure into the buy note itself, keeping the footer line.

**Suggested command:** `$impeccable audit`

## Persona Red Flags

**Jordan (confused first-timer)** — arrives from Amazon not really knowing what they bought; the header offers a mascot and a tagline, no photo of the device and no "here's what this does". The two stacked `.note` blocks are visually identical, so the shopping ad and the hard browser requirement read as equally optional. **Clicks the wrong thing first:** the unstyled Connect & Install loses to the three white download tiles, so Jordan downloads the companion before flashing and runs it against a bare board. At the Chrome port picker (entries like "USB JTAG/serial debug unit") the page's only guidance is a muted "Pick the board's port when asked" — it never says what the entry looks like. Then SmartScreen, and the page has nothing to say. Likely quit point.

**Riley (deliberate stress tester)** — disables JS: the button sits there fully visible, clickable, inert, flanked by two red errors, no `<noscript>`. Reads the footer's "no VS Code, no command line," then finds `--pair`, `--pi`, `claude`, and `claude /usage` in the body — direct self-contradiction. Asks the question the page cannot answer: how do you pass `--pair` to a binary you were told to double-click? Follows the `--pair` note, sees no code, and only learns from TROUBLESHOOTING.md that a confirmation code was supposed to appear on the board. Runs a contrast check and finds links at 2.7:1, muted at 4.1:1, badges at 3.1:1.

**Casey (distracted mobile user)** — taps the link on a phone and is **given no forward path whatsoever**: no copy-link, no QR, no mailto. The one element that sounds addressed to them, the "Setting up from a phone instead?" disclosure in card 2, is actively misleading — it describes joining `Yoyu-Setup` on an *already-flashed* board, so Casey may spend minutes hunting for a Wi-Fi network that does not exist. At 390px the download row breaks 2 + 1: Windows and macOS at 151px each, **Linux orphaned alone on its own 312px row** — measured, and it persists from ~390px to ~520px. The footer's "Source & docs on GitHub" splits mid-phrase across two lines and the `·` separator strands. The "on Amazon" link fragments into a **17.1 × 20 px** hit sliver. Casey may tap a tile and download a Windows `.exe` onto a phone.

## Minor Observations

- **Focus rings do exist** — Chrome's UA default renders on all 12 tab stops, dual-tone and legible on every background (verified at 3× zoom). But nothing is authored: the ring is near-black `#101010`, off-brand, and sits at `outline-offset:0` flush against the 23px install button. DOM tab order, no keyboard trap, no positive `tabindex`.
- **The mascot SVG does expose an accessible name** — Chrome maps `aria-label` correctly despite the missing `role="img"` (verified via the a11y tree). Worth noting the opposite problem: it is a decorative mascot with a descriptive name, so screen readers announce it.
- The three emoji (🛒 ⚙️ ⚡) are the page's only iconography and render as full-colour system emoji, stylistically at odds with the flat two-tone pixel art directly above them.
- The `.dl` tiles have no `:hover`, `:active`, or authored `:focus-visible` — they look like buttons and never respond.
- No OS detection: every visitor makes a three-way choice the page could make for them.
- `.note` is used four times for four unrelated purposes at identical weight; the token has no meaning left.
- Step 2's "The board reboots and shows its address on screen" is the *only* place that address ever exists, yet step 3's fallback depends on it. No "write this down", no photo.
- The page never says the flash is repeatable and non-destructive. One sentence would remove most of the fear at the highest-stakes click.
- No `og:`/`twitter:` meta tags on a URL the README explicitly tells people to open.
- Seven external links, all `rel: null`; none use `target="_blank"`, so the risk is low — but the affiliate link should carry `rel="sponsored"`.
- Headings are clean: one `<h1>`, three `<h2>`, no skipped levels, `main`/`header`/`footer` landmarks present, `lang="en"` set. `<details>`/`<summary>` are used correctly throughout.
- The three `<summary>` toggles measure 312 × **24** px — under the 44px target height, as do all inline links at 20px.
- No horizontal overflow at either width. `docs/firmware/` holding only `manifest.json` is correct (the `.bin` is CI-fetched at Pages build), not a defect.

## Questions to Consider

1. **Why does the page that has to justify a $26 purchase and a scary flash contain no photograph of the product working, when three good ones sit in `docs/img/` and are already in the README?** What changes if `meters.jpg` becomes the hero above the `<h1>`, and `timer.jpg` closes card 3 as the payoff?
2. **What if the page detected `install-unsupported` and *reorganized itself* for phones instead of apologizing?** A phone visitor could read what the product is, see the photos, copy the link to their desktop, even start the Claude Code CLI sign-in prerequisite. Right now the most common visitor gets the least page.
3. **Should steps 2 and 3 stay collapsed until step 1 fires its success event?** esp-web-tools emits `closed` on the install dialog. Revealing one card at a time would cut the visible surface by two-thirds at the moment of highest anxiety — and would let the board's IP be captured and carried forward instead of memorized.
4. **If the footer's promise is "no VS Code, no command line," why do `--pair` and `--pi` appear on this page at all?** Would the buyer-first path get measurably better if every terminal flag moved to TROUBLESHOOTING.md and this page kept exactly one way to do each thing?
