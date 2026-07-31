# Release checklist

How to cut a Headroom release. Tags drive everything: pushing `vX.Y.Z` builds
the companion apps **and** the Mini firmware image and attaches them to a
GitHub Release; the setup page + companion download links always point at
`releases/latest`.

## What the automation does

| Workflow | Trigger | Produces |
|---|---|---|
| `firmware.yml` | push/PR touching `firmware/**` | compile-check + firmware artifacts (CI gate) |
| `release.yml` | push tag `v*` | `HeadroomCompanion-{windows.exe,macos,linux}` + `headroom-mini-merged.bin` + the signed OTA `headroom-mini-app.bin.sig`, attached to the Release |
| `pages.yml` | push to `main` touching `docs/**` | deploys the setup/flasher page to GitHub Pages |

Fixed URLs the site depends on (resolve once a Release exists):
- Flasher image: `https://github.com/DaveEuson/HeadroomMini/releases/latest/download/headroom-mini-merged.bin`
- Companion: `.../releases/latest/download/HeadroomCompanion-{windows.exe,macos,linux}`
- Setup page: `https://daveeuson.github.io/HeadroomMini/`

## One-time setup (first release only)

- [ ] **GitHub → Settings → Pages → Source = "GitHub Actions."** Without this,
      `pages.yml` has nothing to publish to and the flasher page never goes live.
- [ ] **Add the `OTA_SIGNING_KEY` repo secret** (the EC P-256 private key —
      keygen + steps in `docs/HARDENING.md`). Signature-checking firmware
      refuses an unsigned OTA image, and `release.yml` hard-fails without this
      secret. Required from the first signed-OTA release onward.

## Every release

1. [ ] **Bump the version.** Firmware `FW_VERSION` + `UA` in
       `firmware/src/main.cpp`; companion `USER_AGENT` in
       `companion/companion.py` if it changed. Keep them in step with the tag.
2. [ ] **Green CI on the branch** — `firmware.yml` (the only pre-tag compile
       check for the firmware) and `companion.yml` (unit tests) must be passing.
3. [ ] **Merge the PR into `main`.** This fires `pages.yml`, which redeploys the
       setup page. (It does *not* build binaries — only the tag does.)
4. [ ] **Create the release / tag.** The tag **must start with `v`** (e.g.
       `v1.0.0`) — `release.yml` only triggers on `v*`, so a tag like `1.4.0`
       silently builds nothing.

       **Tag `origin/main` explicitly, never the working copy.** Tagging
       whatever your local checkout happens to be on has shipped the wrong
       commit twice: once a months-old commit, once one commit short of the
       intended content. `release.yml` now cross-checks the tag against
       `FW_VERSION` and fails fast on a mismatch, but the habit is the real fix:
       ```
       git fetch origin main
       git tag v1.0.0 origin/main
       git push origin v1.0.0
       ```
       or on GitHub: **Releases → Draft a new release → Choose a tag → type
       `v1.0.0` → Create new tag on publish → Publish**. Either way `release.yml`
       builds the three companion apps + the merged firmware image and attaches
       them to Release `v1.0.0`.

       *Re-pointing a tag* (only safe while no release has been published for
       it): `git tag -d v1.0.0 && git push origin :refs/tags/v1.0.0`, then
       re-create and push as above.
5. [ ] **Watch `release.yml` go green** and confirm the Release has the three
       `HeadroomCompanion-*` apps plus the firmware images
       (`headroom-mini-bootloader/partitions/boot_app0/app.bin` for the flasher,
       and `headroom-mini-merged.bin` for esptool users).
6. [ ] **Smoke test the retail path** in Chrome/Edge:
       - Open `https://daveeuson.github.io/HeadroomMini/`, click **Connect &
         Install**, flash a board.
       - Same window → **Connect to Wi-Fi** (Improv) → board joins.
       - Open `http://<board-ip>:8080` → styled landing page loads.
       - Download a companion binary from the page and confirm it feeds the
         board (`--pi`, or auto-discovered).
       - **Pair (self-contained):** `HeadroomCompanion --pair` (auto-finds the
         board) → status flips to "Running self-contained" and meters update
         with no companion running. (`/connect` manual paste is the fallback.)
       - `/alerts` → set an ntfy topic → **Send test alert** lands on a phone.
       - **OTA:** from a board on the previous release, open `/update` and
         confirm it installs the new signed image and reboots on the new
         version (the signature is accepted).

## Release notes template

```
## HeadroomMini v1.0.0

### Headroom Mini (ESP32-S3) — first full firmware
- Browser flasher (ESP Web Tools) + Wi-Fi over USB (Improv) — no VS Code/CLI.
- Self-contained on-device usage polling — pair it once with the companion
  (`--pair`), no computer needed afterward; manual `/connect` paste as fallback.
- Touch (cycle screens, % used/left, brightness) + motion (flip to sleep,
  shake wake), battery gauge, usage-history graph, phone push alerts (/alerts).

### Companion
- `--pair` hands a board your login so it runs self-contained.
- Multi-device push (comma-separated --pi), single-instance lock, live-usage
  backoff.
```

## Signed firmware updates (OTA)

From the first signature-checking build onward, the board verifies an ECDSA
P-256 signature before applying any OTA image (details in `docs/HARDENING.md`).
Two things to keep straight:

- **Every release must be signed.** `release.yml` signs `headroom-mini-app.bin`
  with the `OTA_SIGNING_KEY` secret and publishes `headroom-mini-app.bin.sig`
  next to it. The signing step hard-fails if the secret is missing, so you can't
  accidentally ship a release that signature-checking boards will reject.
- **Bootstrap order (matters once).** A board already running signed-OTA
  firmware only accepts signed releases. The *first* signed build therefore has
  to reach a board another way — an OTA from the previous, non-checking firmware,
  or a USB re-flash. After that, every OTA is verified. A signed build will not
  downgrade to a pre-signing release (those carry no `.sig`).

**Rotating the signing key:** generate a new EC P-256 keypair, replace the PEM
in `firmware/src/ota_pubkey.h`, update the `OTA_SIGNING_KEY` secret, and ship
that build — again, its first delivery is OTA-from-old or USB, since existing
boards trust the old key until they run the new firmware.

## Rollback

Releases are immutable; to ship a fix, tag a new patch (`v1.0.1`). The setup
page and companion links track `releases/latest`, so a new Release moves users
forward automatically — nothing else to update. (A signed-OTA board only rolls
forward to another *signed* release, not back to a pre-signing one.)
