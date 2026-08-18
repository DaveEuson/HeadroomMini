---
name: Yoyu
description: One warm palette in two polarities — cream paper for setup, a lit panel for the desk.
colors:
  paper: "#f0eee6"
  paper-card: "#faf9f5"
  paper-raised: "#ffffff"
  paper-tint: "#fbeee8"
  ink: "#3d3929"
  muted: "#6b6759"
  line: "rgba(61,57,41,.14)"
  panel: "#262624"
  panel-ink: "#f5f4ef"
  panel-muted: "#94907e"
  terracotta: "#d97757"
  terracotta-deep: "#ba5532"
  terracotta-text: "#a8442a"
  terracotta-track: "#4a382f"
  on-terracotta: "#ffffff"
  stone: "#8a8577"
  amber: "#fab219"
  amber-track: "#463b1a"
  crimson: "#e05252"
  crimson-track: "#4a2727"
  error-text: "#b4442a"
  sprocket-body: "#5f83a1"
  sprocket-shade: "#3f5f7a"
  sprocket-outline: "#1a1816"
  sprocket-face: "#faf7ef"
typography:
  display:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1.5
  headline:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "1.2rem"
    fontWeight: 700
    lineHeight: 1.5
  body:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "0.93rem"
    fontWeight: 400
    lineHeight: 1.5
  action:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 700
    lineHeight: 1
  panel-clock:
    fontFamily: "Adafruit GFX 5x7 bitmap, scale 4"
    fontSize: "32px"
    fontWeight: 400
    lineHeight: 1
  panel-title:
    fontFamily: "Adafruit GFX 5x7 bitmap, scale 3"
    fontSize: "24px"
    fontWeight: 400
    lineHeight: 1
  panel-body:
    fontFamily: "Adafruit GFX 5x7 bitmap, scale 2"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1
  panel-caption:
    fontFamily: "Adafruit GFX 5x7 bitmap, scale 1"
    fontSize: "8px"
    fontWeight: 400
    lineHeight: 1
rounded:
  xs: "4px"
  sm: "6px"
  md: "10px"
  lg: "12px"
  panel-card: "14px"
  xl: "16px"
  meter: "7px"
  pill: "999px"
  circle: "50%"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "22px"
  xxl: "32px"
  page-bottom: "64px"
components:
  button-primary:
    backgroundColor: "{colors.terracotta-deep}"
    textColor: "{colors.on-terracotta}"
    typography: "{typography.action}"
    rounded: "{rounded.lg}"
    padding: "17px 28px"
  button-secondary:
    backgroundColor: "{colors.stone}"
    textColor: "{colors.on-terracotta}"
    rounded: "{rounded.md}"
    padding: "12px 18px"
  button-confirmed:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.on-terracotta}"
    rounded: "{rounded.md}"
    padding: "12px 18px"
  card:
    backgroundColor: "{colors.paper-card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.xl}"
    padding: "22px 20px"
  step-badge:
    backgroundColor: "{colors.terracotta-deep}"
    textColor: "{colors.on-terracotta}"
    rounded: "{rounded.circle}"
    height: "28px"
    width: "28px"
  download-tile:
    backgroundColor: "{colors.paper-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "12px 8px"
  note:
    backgroundColor: "{colors.paper-tint}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
  aside:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
  code-inline:
    backgroundColor: "rgba(61,57,41,.07)"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "2px 6px"
  meter-track:
    backgroundColor: "{colors.terracotta-track}"
    rounded: "{rounded.meter}"
    height: "14px"
    width: "216px"
  meter-fill:
    backgroundColor: "{colors.terracotta}"
    rounded: "{rounded.meter}"
    height: "14px"
  meter-fill-warn:
    backgroundColor: "{colors.amber}"
    rounded: "{rounded.meter}"
    height: "14px"
  meter-fill-critical:
    backgroundColor: "{colors.crimson}"
    rounded: "{rounded.meter}"
    height: "14px"
---

# Design System: Yoyu

## Overview

**Creative North Star: "Paper and Panel"**

There is one palette here, and it lives in two polarities. Everything you meet in
a browser — the setup page, the board's own `/settings`, `/alerts`, `/update`
pages — is **paper**: warm cream (`#f0eee6`), dark ink (`#3d3929`), thin borders,
almost no shadow. Everything on the 2" LCD is **panel**: that same warmth
inverted into a near-black ground (`#262624`) with cream ink (`#f5f4ef`), lit
rather than printed. The terracotta accent (`#d97757`) is the one value that
crosses the boundary unchanged, so the button you press in the browser and the
meter that fills on your desk are recognizably the same object.

The register is plain and generous. Type is `system-ui` on every web surface and
a bitmap face on the panel; there is no typeface to admire. Density is low on
purpose — the setup page is three numbered cards and stops, and the panel is read
in under a second from across a desk. What carries the design is discipline about
where color goes and how much room things get.

The system is deliberately **not a SaaS marketing page**: no gradient meshes, no
glassmorphism, no floating testimonial cards, no logo wall, no hero full of
abstract 3D shapes. It is also not trying to extract money — this is free, MIT
software whose only price is a third-party board. That rules out the whole
monetization vocabulary: no urgency, no email capture, no upsell tiers, no
pricing table, no "Pro" badge. The single affiliate link is disclosed in place
and styled no louder than the sentence around it.

**Key Characteristics:**
- One palette, two polarities: cream paper in browsers, inverted lit panel on the device.
- Terracotta is rationed to one primary action per card or screen.
- Flat by default — 1px borders do the separating; one shadow in the system marks the one action that matters.
- Generous and unfussy: 44px hit-target floor, soft 10–16px corners, no ornament.
- A three-tier state ladder (terracotta → amber → crimson) that never rides on hue alone.
- Sprocket, a 11×11 pixel-art mascot, is the only illustration the system owns.

## Colors

A warm, low-chroma palette built from one terracotta and a cream-to-ink neutral
ramp, deployed at opposite polarity depending on whether the surface is printed
or lit.

### Primary
- **Terracotta** (`#d97757`): the accent that crosses both polarities. On the panel it is the healthy-state meter fill and the color of anything the board wants you to act on. On paper it is a *surface* color only — at 2.75:1 on cream it cannot legally carry text.
- **Deep Terracotta** (`#ba5532`): the paper-side action color. Carries white at 4.7:1, so it owns primary buttons and the numbered step badges.
- **Reading Terracotta** (`#a8442a`): anything terracotta you actually read — links, focus rings, the footer heart. 5.1:1 on the page, 5.7:1 on cards.

### Secondary
- **Stone** (`#8a8577`): the step-down for secondary actions — Settings, Phone alerts, Disconnect, Send test alert. Its whole job is to not be terracotta.

### Tertiary
- **Amber** (`#fab219`) and **Amber Track** (`#463b1a`): the ≤30%-left tier, and the color of a "stale >10m" freshness warning.
- **Crimson** (`#e05252`) and **Crimson Track** (`#4a2727`): the ≤10%-left tier.
- **Error Text** (`#b4442a`): paper-side failure copy — unsupported browser, flasher didn't load.

### Neutral
- **Cream Paper** (`#f0eee6`): the page ground on every browser surface, board-served pages included.
- **Card Cream** (`#faf9f5`): raised content blocks on the page ground.
- **White** (`#ffffff`): the second lift — download tiles, network rows, text inputs.
- **Blush Tint** (`#fbeee8`): the terracotta-adjacent wash behind notes, the buy prompt, and selected network rows.
- **Ink** (`#3d3929`): body text on paper, and the confirmed/"Link copied" button fill.
- **Muted Ink** (`#6b6759`): secondary paper text at 4.8:1 on cream.
- **Hairline** (`rgba(61,57,41,.14)`): the separator that does the work shadows would otherwise do.
- **Panel Ground** (`#262624`) / **Panel Ink** (`#f5f4ef`) / **Panel Muted** (`#94907e`): the inverted set, for the LCD only.

### Sprocket
The mascot's four fixed colors, shared byte-for-byte between the inline SVG on the
setup page and the sprite drawn on the board: **Body** (`#5f83a1`),
**Shade** (`#3f5f7a`), **Outline** (`#1a1816`), **Face** (`#faf7ef`).

### Named Rules

**The One Action Rule.** Exactly one element per card or screen wears a
terracotta fill. Every other control steps down to Stone, a bordered white tile,
or plain ink. When a second thing looks equally urgent, one of them is wrong.

**The Polarity Rule.** Paper colors never appear on the panel and panel colors
never appear on paper. `#94907e` is the panel's muted ink; on cream it measures
2.75:1 and fails. Use `#6b6759` on paper.

**The Three-Job Rule.** No single terracotta can be a surface, carry white, and
be readable on cream at once. That is why there are three. Pick by job — fill,
action, or text — never by preference.

## Typography

**Display / Body Font:** `system-ui` (falling back through `-apple-system`, `Segoe UI`, `Roboto`, `sans-serif`)
**Panel Font:** Adafruit GFX 5×7 bitmap, integer-scaled

**Character:** There is no typeface personality here, by design. The web
surfaces borrow whatever the reader's OS already trusts, which makes an ESP32
dev-board project read as a piece of system software rather than a hobby page.
On the panel, type is a bitmap grid at integer scale — glyph size is chosen from
a fixed ladder, never interpolated.

### Hierarchy
- **Display** (700, 2rem, 1.5): the product name in the page header. Once per page.
- **Headline** (700, 1.2rem): step titles inside cards — "Flash the board", "Put it on your Wi-Fi".
- **Body** (400, 1rem, 1.5): instructions. Constrained by a 640px main column, not a `ch` measure.
- **Label** (400, 0.93rem): notes, asides, and disclosure contents — the quieter register for anything supporting.
- **Action** (700, 1.15rem, 1): the primary button only. The largest thing on the page after the h1.
- **Panel Clock** (bitmap ×4, 32px): the time on Meters. The single biggest element on the device.
- **Panel Title** (bitmap ×3, 24px): screen names and "Set me up".
- **Panel Body** (bitmap ×2, 16px): window labels, "93% left", countdowns — the numbers the product exists to show.
- **Panel Caption** (bitmap ×1, 8px): freshness, plan name, IP hints. Reference detail, not glance material.

### Named Rules

**The Glance Rule.** On the panel, anything a user needs at arm's length is
bitmap ×2 or larger. Scale ×1 is for things you walk over and lean in to read;
never put a live number there.

**The Borrowed Type Rule.** No web fonts, ever. `system-ui` is a security and
speed position as much as an aesthetic one — the setup page collects Wi-Fi
credentials and loads nothing from a third-party host.

## Layout

A single centered column, `max-width: 640px`, on a page padded `32px 18px 64px`
and extended into the safe-area insets on notched devices. Content is a vertical
stack of cards at `16px` gaps; there is no multi-column layout at any breakpoint.

The one responsive change on the setup page is the platform download row, which
goes from a single stacked column to three equal columns at `520px`. Everything
else reflows by wrapping.

Rhythm runs on a loose 4px-derived scale — `4 / 8 / 10 / 12 / 14 / 16 / 22 / 32 / 64`.
Card interiors are `22px 20px`; the tighter asides and notes are `10px 14px`.

The panel is a fixed 240×320 canvas with no responsive behavior at all. Its
layout is absolute: a 12px left margin, meters on an 82px vertical pitch, meter
bars 216px wide and 14px tall, and a footer row pinned at y=305.

### Named Rules

**The Three-Window Rule.** The Meters screen draws at most three usage windows,
then prints "+N more" in terracotta rather than shrinking to fit. Overflow is
disclosed, never compressed.

## Elevation & Depth

Flat by default. Surfaces separate with a 1px hairline border and a small tonal
step (cream page → card cream → white), not with shadow. The card's
`0 1px 2px rgba(61,57,41,.05)` is barely a shadow at all — it is an edge softener.

Depth in this system means priority. There is exactly one real shadow, and it
belongs to the single most important control on the page.

### Shadow Vocabulary
- **Edge** (`box-shadow: 0 1px 2px rgba(61,57,41,.05)`): every card. Just enough to keep the border from reading as a drawn line.
- **Primary Lift** (`box-shadow: 0 2px 8px rgba(122,52,26,.28)`): the flash button, and nothing else. Drops to `0 1px 4px` with a 1px translate on `:active`.

The panel has no elevation vocabulary at all — the hardware cannot composite, and
there is nothing to cast onto. Depth there is expressed as a tonal pair: every
meter fill sits on a much darker tint of its own hue.

### Named Rules

**The Earned Shadow Rule.** Surfaces are flat. A shadow marks the one action
that matters most on the surface; adding a second one means the first has stopped
meaning anything.

## Shapes

Soft, consistent, and never fully round except where roundness is the point. The
radius ladder tracks element size: `6px` on inline code, `10px` on secondary
buttons, tiles, notes, and asides, `12px` on the primary button and images,
`14px` on board-served cards, `16px` on setup-page cards.

Two deliberate exceptions: the numbered step badge is a true `50%` circle at
28×28, and meter bars use `radius: 7px` on a `14px` height — exactly half, so the
bar is a capsule at every fill level.

Borders are always 1px and always the hairline neutral, except when a control is
selected or hovered, where the border shifts to terracotta rather than the fill
changing.

### Named Rules

**The Never-Empty Rule.** A meter fill clamps to a minimum of 8px even at 0%
left. A capsule with nothing in it reads as a broken widget, not as an empty
tank.

**The Spent-State Rule.** The three-tier ladder describes *headroom*, and it
stops applying the moment there is none. On a screen about waiting rather than
remaining, drop to neutral ink and let a single crimson label carry the state —
otherwise a long wait wears terracotta, the colour of a full tank, and a wait
about to end wears crimson exactly as the news turns good.

## Components

### Buttons
- **Shape:** softly rounded (`12px` primary, `10px` everything else). Never pill, never square.
- **Primary:** Deep Terracotta fill, white label, `17px 28px` padding, `1.15rem/700`, capped at `340px` and centered. Carries the only real shadow in the system.
- **Hover / Focus:** `filter: brightness(1.08)` over `.15s ease-out` — no color swap, no scale. `:active` translates 1px down and halves the shadow. The primary button's focus ring is deliberately **ink**, not terracotta, because terracotta-on-terracotta doesn't read.
- **Secondary:** Stone fill, white label, `12px 18px`. Used for Settings, Phone alerts, Disconnect, Send test alert.
- **Confirmed:** on success the Copy-link button swaps to an ink fill and a "Link copied" label for 2.4s, then reverts.
- **Tile (download):** white fill, hairline border, ink label with a muted `.8rem` sub-label; hover shifts the *border* to terracotta and leaves the fill alone.

### Cards / Containers
- **Corner Style:** `16px` on the setup page, `14px` on board-served pages.
- **Background:** Card Cream on the page ground.
- **Border:** 1px hairline.
- **Shadow Strategy:** Edge only — see Elevation.
- **Internal Padding:** `22px 20px`.
- Each card opens with a step row: a 28px circular terracotta badge and a `1.2rem` headline on a shared baseline.

### Asides — three weights, deliberately unequal
The system distinguishes three kinds of supporting block, and the distinction is
load-bearing. Giving them equal weight is what made them all get skipped.
- **Note** — a requirement you must act on. Blush tint, terracotta-tinted border.
- **Buy** — the shopping prompt. Same treatment as Note; carries its FTC disclosure inline, not four screens below.
- **Aside** — genuinely optional. Transparent ground, neutral hairline, muted text, with `<strong>` restored to full ink so a skimmer still catches the hook.
- **Disclosure (`<details>`)** — the fourth register, for troubleshooting nobody needs unless they're stuck. Summary rows are padded to a 44px target.

### Inputs / Fields
- **Style:** white fill, 1px hairline border at higher opacity (`.18`–`.25`), `10px` radius, full-width, `box-sizing: border-box`.
- **Focus:** the global ring — `3px solid #a8442a` at `3px` offset — applied uniformly to every focusable control rather than left to seventeen different UA defaults.
- **Selected:** network rows shift border to terracotta and fill to Blush Tint.

### Meter (signature component)
The product's core object, on the panel and conceptually everywhere.
- A `216×14` capsule track in a dark tint of the fill's own hue, with a rounded fill on top.
- Label at bitmap ×2 on the left; the big "93% left" right-aligned to x=228 on the following line; a muted countdown below the bar.
- Tier by remaining headroom: >30% terracotta on `#4a382f`, ≤30% amber on `#463b1a`, ≤10% crimson on `#4a2727`.
- The tier is carried by **three** signals at once — fill color, fill length, and the literal percentage in ×2 type — so hue is never the sole carrier.

### Sprocket (signature component)
An 11×11 pixel-art mascot rendered from a shared four-color sprite map: as inline
SVG at 72px on the setup page (`shape-rendering: crispEdges`), as an animated
buffered screen on the panel, and as a small avatar on the board's own pages
against a `#262624` chip that reproduces the panel polarity in miniature. It
reacts to remaining headroom and to overnight dimming — Sprocket is state, not
decoration.

## Do's and Don'ts

### Do:
- **Do** pick the terracotta by job: `#d97757` to fill a surface, `#ba5532` to carry white, `#a8442a` to be read. The three exist because one value cannot do all three at AA on cream.
- **Do** give exactly one control per card or screen a terracotta fill; step everything else down to Stone (`#8a8577`) or a bordered white tile.
- **Do** separate surfaces with a 1px hairline and a tonal step, and reserve the one real shadow for the single most important action.
- **Do** keep every interactive target at 44px or larger, including `<summary>` rows — which is why they carry `10px` block padding rather than sitting at their natural 24px.
- **Do** carry a state tier with fill length and a literal number alongside the hue, the way the meters already do.
- **Do** hold the panel's glance floor at bitmap ×2 for anything a user reads from across the desk.
- **Do** keep every asset first-party. `esp-web-tools` is vendored into `docs/vendor/` on purpose: this page collects Wi-Fi credentials, and a hijacked CDN could exfiltrate them.
- **Do** preserve the state change when `prefers-reduced-motion` is set, and drop only the movement. A blanket `0.01ms` kill would strip feedback that is doing real work.

### Don't:
- **Don't** put `#94907e` on cream. It is the panel's muted ink and measures 2.75:1 on paper — below AA. The board-served pages currently do this and it is a defect, not a precedent.
- **Don't** set terracotta as text on cream. `#d97757` is 2.75:1; that is what `#a8442a` is for.
- **Don't** introduce a web font, a CDN asset, or any third-party host on any surface.
- **Don't** reach for the SaaS marketing vocabulary — gradient meshes, glassmorphism, testimonial cards, logo walls, abstract 3D hero shapes. None of it belongs here.
- **Don't** add monetization pressure of any kind: no urgency, no email capture, no pricing tiers, no "Pro" gating. The software is free and MIT; the one affiliate link stays disclosed in place and no louder than its surrounding sentence.
- **Don't** let a meter render at zero width. Clamp the fill to 8px.
- **Don't** compress overflow on the panel. Three windows, then "+N more".
- **Don't** invent a second mascot or restyle Sprocket. Its four colors are shared byte-for-byte between the SVG and the firmware sprite.
- **Don't** use terracotta for a focus ring on a terracotta fill — that ring stays ink.
