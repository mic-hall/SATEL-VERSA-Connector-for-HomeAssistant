# SATEL VERSA connector for Home Assistant

This is a custom integration allowing to read input states of SATEL VERSA alarm systems locally through an **ETHM-1 Plus**. This custom integration is distributed under the MIT license.

**Beta: 0.1.0-beta.2.** The protocol has been tested with one VERSA 15 +
ETHM-1 Plus installation. Other models/firmware and long-running operation
are not yet validated. This project is independent of SATEL.

## Features

- A `binary_sensor` for each selected input, with stable IDs across IP changes.
- `on` means the input is currently violated; alarm memory is a separate flag
  in the protocol and does not turn the violation entity on.
- One asynchronous session and one shared poll for all inputs (default 1 s).
- Entities become `unavailable` when polling fails. Reconnect uses a bounded
  backoff of 5–60 seconds, returning to normal polling after recovery.
- UI setup, polling options and connection reconfiguration. English and Polish UI.
- Local communication. No arming/disarming, bypass control, output switching
  or alarm configuration writes. No Home Assistant actions/services are exposed.

## Requirements

- Home Assistant **2026.10.1 or newer**.
- A SATEL VERSA alarm board with ETHM-1 Plus and a working DLOADX LAN/WAN connection.
- Network access from Home Assistant to the ETHM DLOADX port (usually 7090).
- The ETHM **DLOADX key**, **DLOADX identifier** and **VERSA identifier** from
  DLOADX communication settings. The program opening PIN is not used.
- Disconnect DLOADX before using the integration. Concurrent programming
  sessions are not supported by this beta.

The integration uses `cryptography`, already required and installed by Home
Assistant Core. It does not download or run DLOADX. The protocol library is
included in `custom_components/satel_versa/protocol` and is independent of HA.

## Installation

### HACS custom repository

1. Open HACS → menu → Custom repositories.
2. Add https://github.com/mic-hall/SATEL-VERSA-Connector-for-HomeAssistant, category **Integration**.
3. Download SATEL VERSA and restart Home Assistant.
4. Add the integration through Devices & services.

This project is prepared for a HACS custom repository; it is not listed in the
HACS default store.

### Manual

1. Download the release `satel_versa-<version>.zip` and extract it into your
   Home Assistant configuration directory. The resulting path must be:
   `config/custom_components/satel_versa/manifest.json`.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → SATEL VERSA**.

Alternatively, copy only `custom_components/satel_versa` from this repository
into `config/custom_components/` and restart Home Assistant.

## Configuration

| Setting | Meaning |
|---|---|
| Host / port | ETHM LAN address and DLOADX TCP port |
| ETHM DLOADX key | 1–12 printable ASCII characters; copied exactly, including any spaces |
| DLOADX identifier | Exactly 8 hexadecimal characters from communication settings |
| VERSA identifier | Exactly 8 hexadecimal characters from communication settings |
| Inputs | Explicit input numbers, e.g. `1-8,10`; supported positions are 1–30 |
| Poll interval | 1–60 seconds; default 1 second |

Choose only inputs actually configured on your panel. A zero in the bitmap
does not prove an input exists. Input 31/32 and automatic input discovery are
not supported. ASCII key validation deliberately excludes ambiguous legacy
Windows encodings in this first release.

Setup performs START, a display query, one input read and STOP to validate the
settings. It then opens the operational session. The integration never renders
or logs the virtual keypad display.

Entities are called **Input N** (or **Wejście N**). Rename them and assign areas
in Home Assistant. No device class is guessed: a violation may represent motion,
a contact, a fault or a different panel input type.

**Configure** changes the input selection and poll interval. **Reconfigure**
changes the host, port and identifiers/key; enter credentials again. It briefly
stops the running connection while testing the new settings. The panel ID must
remain the same; remove and add the integration to use a different panel.
Identifiers are user-configurable, so changing the panel ID also changes its
HA identity. Preserve it when changing only the network address.

## Availability, stopping and DLOADX

A failed poll makes all entities unavailable until the next successful read.
Old values are not presented as fresh data and are not replaced with `off`.
The coordinator reconnects with increasing delays, capped at 60 seconds.
Normal polls and protocol operations are serialized.

To use DLOADX, disable this integration first. Disable/unload closes the session
and attempts STOP; transport failures may prevent a STOP acknowledgement, but
the socket is still closed. Re-enable the integration after disconnecting DLOADX.

To uninstall, remove its entry from Devices & services, remove
`config/custom_components/satel_versa`, and restart Home Assistant. If installed
through HACS, remove the repository there as well.

## Limitations

- Tested hardware: VERSA 15 + ETHM-1 Plus; no INTEGRA or PERFECTA support claim.
- Reverse-engineered successful-session profile, not an official SATEL protocol
  implementation. Unknown greetings/records fail the operation.
- Some startup notifications can precede input data; a poll handles at most four
  responses under one five-second timeout. Persistent notifications fail the poll.
- Command rejection is not automatically classified as an invalid password.
- No names import, configuration-file import, output control or alarm panel entity.
- A successful read is not a test of the alarm installation or a replacement for
  its independent alarm functions.

## Troubleshooting and privacy

Check the port, identifiers and ETHM key, network routing, and whether DLOADX
is disconnected. A working DLOADX connection on another computer does not prove
Home Assistant has network access. Review HA logs for connection/update failures.

Download integration diagnostics from the entry menu. Diagnostics contain only
version, configured input count, poll interval and last update success. They omit
host, identifiers, key, input states and display content. Credentials are stored
by Home Assistant in the config entry; protect your HA configuration and backups.
Do not attach DLOADX configuration files, packet captures or credentials to issues.

See [SECURITY.md](SECURITY.md) and [TESTING.md](TESTING.md).

## Development and releases

Requires Python 3.14.2+ for the pinned HA test environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest --cov --cov-report=term-missing
.venv/bin/python tools/build_release.py
```

Tests use synthetic data and block network sockets. No private capture, actual
panel identifier, ETHM key, DLOADX installer or decompiled code is included.
The release tool creates an installable integration ZIP and a clean source ZIP
using explicit file allowlists. See [PUBLISHING.md](PUBLISHING.md) before uploading.
