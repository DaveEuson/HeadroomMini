// OTA image-signing public key (C2). The release workflow signs
// headroom-mini-app.bin with the matching PRIVATE key (a GitHub Actions secret,
// OTA_SIGNING_KEY); doOTA() verifies the signature against this key before it
// ever marks a downloaded image bootable. A MITM can no longer serve a forged
// firmware image (the review's C2).
//
// This is a PUBLIC key — safe to commit. Rotating it means generating a new
// EC P-256 keypair, replacing this PEM, and updating the OTA_SIGNING_KEY secret.
#pragma once

static const char OTA_PUBKEY[] = R"KEY(
-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE9PoBsHPoBbGkLbFnSZyWNc+sfRmp
kRbuGQDhnF12VG6Zn1/w0RJGmCFG0rhy1Z7WgDDBTrhhUQMgGiFrc8cs2Q==
-----END PUBLIC KEY-----
)KEY";
