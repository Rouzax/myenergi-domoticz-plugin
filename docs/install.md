# Installation

## Prerequisites

Before you start, make sure you have:

- A **myenergi hub** with at least one **zappi** connected to it. Any **harvi** CT clamps on the
  same hub are picked up automatically.
- Your **hub serial number**, shown in the myenergi app and printed on the hub itself. This is
  used as the API username.
- A **myenergi API key**, generated in the myenergi app under **Account > Advanced > API key**.
- **Internet access from the Domoticz host.** The plugin talks to the myenergi cloud
  (`director.myenergi.net`); the myenergi local API is not supported and cannot be used instead.

!!! warning "The API key grants full control"
    The API key you generate lets its holder change your zappi's charge mode, start or stop
    charging, and more, whether or not you turn on this plugin's own Allow Control setting. Read
    [Security](security.md) before entering it into Domoticz.

## Step 1: Install the plugin

Pick whichever way suits you. Both put the plugin at `.../domoticz/plugins/myenergi/plugin.py`.

=== "Git (easy updates)"

    Clone the `dist` branch (it holds only the files needed to run the plugin) into your Domoticz
    plugins directory:

    ```bash
    cd /opt/domoticz/plugins            # adjust to your Domoticz install path
    git clone -b dist https://github.com/Rouzax/myenergi-domoticz-plugin myenergi
    ```

    To update later: `cd myenergi && git pull`.

=== "Download (no git)"

    1. Open the [Releases page](https://github.com/Rouzax/myenergi-domoticz-plugin/releases) and
       download the `myenergi-vX.Y.Z.zip` file from the latest release.
    2. Unzip it into your Domoticz plugins directory. The zip contains a `myenergi` folder, so you
       end up with `.../domoticz/plugins/myenergi/plugin.py`.

    To update later: download the newer zip and replace the folder.

## Step 2: Restart Domoticz

Domoticz only scans the plugins directory for new plugins at startup, so restart the Domoticz
service (or container) now.

## Step 3: Add the hardware

1. In Domoticz, go to **Setup > Hardware**.
2. Under **Type**, choose **myenergi Monitor**.
3. Fill in the settings. At minimum you need the **Hub Serial Number** and **API Key**; every
   other setting has a sensible default. See [Settings](settings.md) for the full list.
4. Click **Add**.

## Step 4: Allow new devices to appear

Domoticz only shows devices from a new piece of hardware if it is allowed to accept them. Go to
**Setup > Settings > System** (or the **Hardware** page, depending on your Domoticz version) and
make sure **Accept new Hardware Devices** is enabled before or shortly after you add the
hardware.

## What happens next

On its first successful poll, the plugin creates the fixed monitoring devices (Solar Total, Home
Consumption, EV Charging, and so on) plus one device per harvi it finds on the hub. See
[Monitoring devices](devices.md) for the full list.

If you turn on **Allow Control** in the settings, the charger control devices are created too;
see [Charger control](control.md). Devices appear under **Setup > Devices**, grouped under the
hardware you just added.

!!! note "First poll can take a few seconds"
    Devices appear after the plugin's first successful poll of the myenergi cloud, not
    instantly when you click **Add**. If nothing shows up after a minute, check the Domoticz log
    for errors and see [Troubleshooting / FAQ](faq.md).

## Next steps

- [Settings](settings.md): every hardware setting explained.
- [Monitoring devices](devices.md): what each device shows.
- [Charger control](control.md): the opt-in control surface.
