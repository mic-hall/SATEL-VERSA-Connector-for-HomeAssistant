# Validation record for 0.1.0-beta.1

Validated on 2026-11-06. This document states observed scope, not general hardware
certification or a claim that all supported input numbers were physically tested.

## Automated tests

Environment: Python 3.14.7, Home Assistant 2026.10.4,
`pytest-homeassistant-custom-component` 0.13.375, `cryptography` 50.0.1.
All environment files are outside this source tree; no global Python installation
was changed. CI recreates the pinned HA testing stack on Linux.

- Protocol: NIST AES-192 reference, DCP-style partial blocks, inner checksum,
  corrupted/truncated frames, explicit command restrictions and bitmap ordering.
- Simulated async module: changing peer tokens, single-byte fragments, serialized
  concurrent reads, START/input/STOP, online notifications, timeout, EOF,
  cancellation and resource cleanup. No test opens a network socket.
- HA: configuration probe and cleanup, duplicate panel prevention, invalid input
  validation, options, reconfiguration, stable entity IDs, violation vs alarm
  memory, unavailable/recovery, backoff and unload cleanup. Removed inputs are
  removed from the entity registry on reload.
- Packaging: explicit file allowlist excludes research data, deterministic ZIP
  contents, translation key parity and required metadata.

Run the full suite and coverage with the commands in README.md. The final local
run passed **52 tests**, with approximately **91% branch-inclusive coverage**
of the integration. Ruff lint and formatting pass.

Official hassfest from Home Assistant tag 2026.10.4 was run locally against this
integration with the default validation plugins: **1 integration, 0 invalid**.
The GitHub HACS validator has not run yet because the repository has not been
published; the workflow is included and must pass after upload. HACS repository
settings such as description/topics/Issues are configured on GitHub, not in code.

## Capture comparison

The Python codec was compared to three private recordings of successful DLOADX
sessions: **2770/2770 plaintext records** and **231/231 generated requests**
matched the previous decoder/captured ciphertext. The reassembled server streams
contain 1387 messages. Original recordings, IDs, keys, input states and DLOADX
binaries are not distributed here.

Previously observed physical changes matched selected inputs in the first byte
(2, 3, 7) and input 10 in the second byte. Other positions follow the mapping
inferred from DLOADX's display logic; they were not individually exercised.

## Live tests

Hardware: one VERSA 15 + ETHM-1 Plus on a local network.

- Initial successful session: START, display query, input read, acknowledged STOP.
- Prepared release protocol client: **20 consecutive reads at approximately
  one-second intervals**, acknowledged close, reconnect, one additional successful
  read and close (2026-11-06, about 22 seconds total).
- No configuration read/write, arming/disarming or output command was sent.

The live test exercised the protocol client under the pinned HA environment,
not a deployed HA installation/UI. Entity lifecycle and availability were tested
with HA fixtures and synthetic data. The live reconnect was a clean close/reopen;
an actual network outage was simulated in tests, not induced on the alarm network.

## Still unverified

Other panels/firmware, simultaneous DLOADX use, overnight/long-term polling,
large installation traffic, all rejection variants and event storms. No
automatic device class or input name discovery is promised. The unknown START
metadata is not treated as a general authentication/permissions specification.

## References used for the HA integration

- [Fetching data and coordinators](https://contributors.home-assistant.io/core/integrations/fetching-data/)
- [Config flows](https://contributors.home-assistant.io/core/integrations/config-flow/)
- [Manifest](https://contributors.home-assistant.io/core/integrations/manifest/)
- [Custom integration structure and brand assets](https://contributors.home-assistant.io/core/integrations/file-structure/)
- [HACS integration requirements](https://www.hacs.xyz/docs/publish/integration/)
