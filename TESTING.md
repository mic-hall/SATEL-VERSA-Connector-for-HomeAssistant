# Validation record for 0.1.0-beta.2

Validated on 2026-11-06. This document states observed scope, not general hardware
certification or a claim that all supported input numbers were physically tested.

## Automated tests

Current minimum-version test: Python 3.14.7, Home Assistant **2026.10.1**,
`pytest-homeassistant-custom-component` **0.13.372**, `cryptography` 50.0.1.
All **52 tests passed**, with about **91% branch-inclusive coverage**.
The initial beta was also tested on HA 2026.10.4 with harness 0.13.375.
CI now runs both pinned versions and asserts the installed HA version explicitly.
No integration runtime API changes were required for 2026.10.1; the previous
HACS minimum was more restrictive than the tested compatibility.
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
The initial publication passed the GitHub HACS validator and hassfest.
These workflows run again for each update. HACS repository
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

## Unreleased VERSA Plus LTE changes (2026-11-15)

The local suite passes 58 tests; Ruff lint and formatting pass. Added simulated
built-in Ethernet transport coverage for START/input/STOP, reconnect, token
updates, corrupt checksums, wrong panel identity, EOF cleanup, timeout during
the START delay, explicit settings and unchanged ETHM defaults. No live panel
connection was made for these changes. Physical VERSA Plus LTE validation remains
pending; the supplied installation report is supporting evidence, not a hardware
validation of this implementation. The historical beta.2 record above is unchanged.

## Unreleased ETHM output indicators (2026-11-18)

The local suite passes 79 tests with about 93% branch-inclusive coverage; Ruff
lint and formatting pass. Coverage includes all 256 flag values for each of
12 output positions, malformed profiles, selector restrictions, serialized
input/output reads, token updates, notifications, timeout/EOF/checksum cleanup,
and rejecting output polling for the LTE profile before START.

HA fixtures verify optional setup/options validation, enum states, stable IDs,
association with the existing panel device, unavailable/recovery/unload behavior,
removal of deselected entities and no additional polling for legacy entries.
Raw flag bytes are not entity attributes or diagnostics.

The integration codec decrypted and parsed 18 recorded ETHM output replies and
regenerated 18 output requests byte for byte from a new private capture. All
output replies were constant. This confirms the 71/09 wire layout, not physical
ON/OFF semantics, blinking semantics or behavior of the new client against live
hardware. Output polling remains opt-in, read-only and ETHM-only. No physical
panel connection or HA deployment was performed for this change.

## Unreleased ETHM partition entities (2026-11-22)

The local suite passes 100 tests, with about 93% branch-inclusive coverage.
Ruff lint and formatting pass. Protocol tests cover partition modes, entry/exit
delay, ACPO, current alarms vs memories, isolation of A/B, invalid profiles,
serialized reads and cleanup after checksum/selector/EOF/timeout failures. LTE
partition selection is rejected before START. Legacy entries send no extra read.

HA fixtures cover enum and binary sensor updates, alarm/memory separation,
unavailable/recovery/unload behavior, selection changes and registry cleanup,
setup/options validation and probe cleanup. Memory and ACPO flags are disabled
by default. Existing input/output tests continue to pass.

The production codec decrypted and parsed 187 partition replies and regenerated
209 selector0 requests byte for byte from a new private recording. A/B arming and
disarming match the user's reported actions. Full mode and exit delay follow the
statically recovered DLOADX labels. All received partition alarm bytes were zero,
so active alarm, night/day, entry-delay and memory semantics still have static
code evidence only. The capture has three missing 16-byte client fragments and
one missing 33-byte server fragment; these were not filled or guessed. Continuous
captured ranges replay correctly across arbitrary chunk boundaries.

No live connection or HA deployment was performed for these changes. Research
binaries, PCAPs, keys, user IDs and private plaintexts are not packaged or published.
