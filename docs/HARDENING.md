# Security hardening plan (post-1.2.0)

1.2.0 shipped the code-level fixes from the security review (endpoint auth, XSS
escaping, credentials-file permissions, NVS bounds, self-hosted flasher). Three
findings remain because each needs the **physical board** to validate a
certificate, a signature, or a pairing code — shipping them unverified could
brick connectivity or flashing across every unit, so each lands on a branch for
an on-hardware smoke-test before merge.

## C1 — TLS certificate verification (in progress)

**Goal:** stop `setInsecure()`; verify server certificates so a man-in-the-middle
can't capture the Claude OAuth tokens or feed a spoofed usage/OTA response.

- **Approach:** `tlsTrust()` installs a curated set of public root CAs (via
  `setCACert`) covering every host the device talks to — `api.anthropic.com`,
  `platform.claude.com`, `api.github.com`, `objects.githubusercontent.com`,
  `ntfy.sh`, `api.pushover.net`. A `-DHR_TLS_INSECURE` build flag keeps the old
  `setInsecure()` behaviour for local development only.
- **Roots included:** ISRG (Let's Encrypt), DigiCert Global (CA/G2/G3),
  Baltimore CyberTrust, Amazon Root CA 1-4, USERTrust/Sectigo, and Google Trust
  Services R1/R4 — the CAs behind the hosts above, sourced from the Mozilla
  bundle (`certifi`). A curated set (≈a dozen roots) keeps the per-connection
  parse cheap on the ESP32's internal heap, versus embedding all ~150.
- **Must test on board:** token refresh, usage poll, OTA download, and both
  alert providers must all still connect. If any host fails the handshake, its
  root is missing from the set and gets added. This is the one change that can
  silently break connectivity, so every path is verified before tag.
- **Rollback:** if a host regresses in the field (CA rotation), a firmware
  update adds the new root; the `-DHR_TLS_INSECURE` flag is the emergency dev
  escape hatch, never shipped.

## C2 — OTA image signing (in progress)

**Goal:** the board only flashes firmware images that were actually signed by
the project, closing the "MITM serves a malicious `.bin`" path.

- **Scheme:** ECDSA P-256 (chosen over Ed25519 because ESP32's mbedTLS ships
  P-256 reliably; Ed25519/EdDSA is often not enabled). The **private key lives
  only as a GitHub Actions secret** (`OTA_SIGNING_KEY`); the public key is
  compiled into the firmware (`firmware/src/ota_pubkey.h`). The release workflow
  signs `headroom-mini-app.bin` and publishes a detached
  `headroom-mini-app.bin.sig`. `doOTA()` streams the image while hashing it,
  fetches the `.sig`, and only calls `Update.end(true)` if the signature
  verifies against the embedded key. **Fail-closed:** no valid signature → the
  update is refused.
- **Bootstrapping:** the first signature-checking firmware is installed once
  (OTA from current firmware, or USB); every OTA after that is verified. A
  signed build can't downgrade to a pre-C2 release (those have no `.sig`).

### Required setup before tagging a signed release

1. Generate an EC P-256 keypair (do this locally for a production key):
   ```
   openssl ecparam -name prime256v1 -genkey -noout -out ota_priv.pem
   openssl ec -in ota_priv.pem -pubout -out ota_pub.pem
   ```
2. Put the **public** key (`ota_pub.pem`) into `firmware/src/ota_pubkey.h`.
3. Add the **private** key as the repo secret **`OTA_SIGNING_KEY`**
   (Settings → Secrets and variables → Actions → New repository secret; paste
   the full `ota_priv.pem`, BEGIN/END lines included).
4. Back the private key up offline. Losing it means no more OTA updates until
   you rotate the embedded public key (a firmware change) and re-flash by USB.

The release workflow **hard-fails** if `OTA_SIGNING_KEY` is missing, so a
release can never ship un-updatable to C2 firmware.

### Must test on board
- A correctly-signed release installs (accepted).
- A tampered image / wrong signature is **rejected** (board stays on the old
  version, no brick).

## C3 — Companion pairing verification (planned)

**Goal:** never hand the long-lived refresh token to a host that merely won the
LAN auto-discovery race.

- **Scheme:** on entering pairing mode the board generates an ephemeral X25519
  keypair and shows a short code (and key fingerprint) on its screen. The
  companion prompts for that code, encrypts the token to the board's ephemeral
  public key, and posts it. Only the real board — the one you can physically
  see — can decrypt it, which fixes both impersonation (authenticity) and
  plaintext sniffing (confidentiality) at once.
- **Simpler v1 fallback:** a screen-displayed pairing code used as a single-use,
  time-boxed shared secret proves the companion is talking to the intended
  board, but does not hide the token from a passive sniffer. Prefer the
  encrypted design.

## Build order

C1 → C3 → C2. C1 is the biggest risk reduction and most contained; C3 protects
the token handoff; C2 is the most infrastructure (keys + CI + on-device verify).
