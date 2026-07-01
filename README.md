# myenergi Domoticz Plugin

Read-only monitoring of a myenergi system (zappi + harvi) via the myenergi cloud API.
See `docs/superpowers/specs/` for the design (local-only). Author: Rouzax.

WARNING: your myenergi API key grants full charger control. Domoticz stores it in
cleartext in its database. Treat DB backups as secrets and rotate the key if it is
ever exposed.
