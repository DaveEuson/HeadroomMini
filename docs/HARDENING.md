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

## C2 — OTA image signing (planned)

**Goal:** the board only flashes firmware images that were actually signed by
the project, closing the "MITM serves a malicious `.bin`" path.

- **Scheme:** Ed25519. Generate a keypair; the **private key lives only as a
  GitHub Actions secret**, the public key is compiled into the firmware. The
  release workflow signs `headroom-mini-app.bin` and publishes a detached
  `.sig`. `doOTA()` downloads both, verifies the signature (mbedTLS) against the
  embedded public key, and only calls `Update.end(true)` on success.
- **Bootstrapping:** the first signature-checking firmware is installed once
  (OTA from current firmware, or USB); every OTA after that is verified.
- **Key management:** document rotation; losing the private key means no more
  OTA updates, so it is backed up out-of-band. Verify on hardware that a good
  build is accepted and a tampered build is rejected.

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
