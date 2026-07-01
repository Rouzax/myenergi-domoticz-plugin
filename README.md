# myenergi Domoticz Plugin

Read-only monitoring of a myenergi system (zappi + harvi) via the myenergi cloud API.
Design and implementation notes are maintained by the author and are not distributed with the plugin. Author: Rouzax.

WARNING: your myenergi API key grants full charger control. Domoticz stores it in
cleartext in its database. Treat DB backups as secrets and rotate the key if it is
ever exposed.
