# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.6.x   | yes       |
| 0.5.x   | yes       |
| < 0.5   | no        |

## Reporting a vulnerability

Do not open a public issue. Email `security@hologram-parallax-photo-studio.dev`
with a description, a minimal repro (input photo + preset + command), and
the affected version. We aim to acknowledge within 72 hours.

## Scope

In scope:
- Arbitrary file write via crafted EXIF or sidecar JSON in `ingest/`
- Path traversal through `--output-dir` or preset names in `render/`
- Remote code execution via a malicious ONNX / TorchScript depth model
  loaded from `models/weights/`
- Deserialization issues in the job-queue persistence layer

Out of scope:
- Denial of service from enormous input images (we cap at 16384x16384)
- Model quality complaints
- Anything requiring the attacker to already control the user's Python
  environment

## Hardening notes for users

- Only load depth models from `models/weights/` and verify the SHA256
  listed in `models/weights/CHECKSUMS.txt`.
- Run the studio with `--no-network` if you don't want the optional
  telemetry stub to phone home (it doesn't by default).
- Renders are written to `outputs/` by default; keep that folder out of
  any cloud-synced path if your photos are sensitive.