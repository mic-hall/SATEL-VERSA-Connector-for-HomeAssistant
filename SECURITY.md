# Security and private data

This integration opens a local ETHM programming connection to read input states.
Only the observed session start/stop, read-input and display-read requests are
implemented. It has no arbitrary command service, code execution or web endpoint.
Do not expose the ETHM programming port to the public Internet.

Credentials belong only in Home Assistant's UI/config storage. They are never
part of this repository, release ZIP or integration diagnostics. Device/entry
identifiers remain visible in HA registries as required for stable identity.
Use HA's normal backup and access protections for stored configuration.

Report suspected vulnerabilities through GitHub's private vulnerability reporting
when enabled. If unavailable, open an issue requesting a private contact without
posting exploit details, credentials, input names/states or packet captures.

No long-term support or response-time commitment is currently offered for this
beta. The tested hardware profile and validation limits are in TESTING.md.
