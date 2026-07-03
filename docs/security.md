# Security

## What your API key can do

The myenergi API key you generate in the myenergi app (**Account > Advanced > API key**) grants
**full control of your charger**: it can read all your data and, independently of this plugin's
own Allow Control setting, it is technically capable of starting, stopping, and changing the
charge mode on your zappi through the myenergi cloud API. Treat it like a password to your
charger, not just a read-only reporting token.

## Where it is stored

Domoticz stores hardware settings, including the API key, in its own database. The key is kept
in **cleartext**, not encrypted or hashed.

!!! warning "Treat the database, and any backup of it, as a secret"
    Anyone with access to your Domoticz database file, or a backup of it, can read the API key
    out of it directly. Protect backups the same way you would protect the key itself, and avoid
    sharing a full database export with anyone you would not trust with charger control.

## Allow Control is off by default

This plugin's own **Allow Control** setting is a separate safeguard, off by default. With it off,
the plugin only reads data and never sends a command to your charger, even though the API key it
holds is technically capable of it. See [Charger control](control.md) for what changes once you
turn it on, and note that once it is on, control is available to anyone who can command that
Domoticz hardware, not just you.

## If the key is exposed

If you ever paste the key into a chat, screenshot, log, or public repository, or otherwise
suspect it has leaked:

1. Open the myenergi app and go to **Account > Advanced > API key**.
2. Generate a new key. This invalidates the old one.
3. Update the **API Key** field on the plugin's hardware settings in Domoticz with the new key.

Do this as soon as you suspect exposure; there is no way to know who else has used a leaked key.

## What the plugin does to protect the key

- The API key is never written to a device field, name, or any value visible in the Domoticz UI.
- The API key is never written to the Domoticz log at any **Debug Level**, including Verbose.
  Log messages that would otherwise include it have the key redacted before logging.
- The plugin makes no outbound connections other than to the myenergi cloud
  (`director.myenergi.net` and the region-specific host it redirects to).

## Practical advice

- Never paste your API key into a chat, forum post, issue tracker, or screenshot when asking for
  help. Redact it first.
- Keep Domoticz itself behind authentication if it is reachable from outside your home network;
  this plugin relies on Domoticz's own access control for who can view or command its devices.
- Only turn on **Allow Control** if you actually want charger control available from Domoticz,
  and understand that anyone with access to that hardware's devices can then use it.

## See also

- [Charger control](control.md) for what Allow Control enables.
- [Settings](settings.md) for where the API key and Allow Control fields live.
