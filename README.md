![](img/spyglass.jpg)

# Spyglass: Keeping an Eye on Apple Containers

[![macOS](https://img.shields.io/badge/platform-macOS-111111?logo=apple&logoColor=white)](#requirements)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](#requirements)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python runtime dependencies: none](https://img.shields.io/badge/Python%20runtime%20dependencies-none-success.svg)](#requirements)
[![Coverage](coverage.svg)](#coverage)

Spyglass is a **one-shot** command-line tool that keeps selected Apple Containers running and updates them to the latest version of their image. It is not a daemon; schedule it with a macOS LaunchAgent if you want it to run periodically or at login.

## Requirements

- macOS with Apple's container command-line tool installed and its container service configured
- Python 3.12 or newer
- Apple's container executable available on PATH when Spyglass runs

## Run once

Clone this repository, change into the checkout, and run:

```shell
python3 spyglass.py
```

Spyglass only manages containers explicitly labeled **spyglass=true**. For each eligible container it pulls the configured image, compares image digests, and recreates the container when a newer image is available. Stopped, eligible containers are started (for instance after rebooting). After a successful update, the old image is removed by default; set **spyglass_rmi=false** to keep it.

Container configuration is reconstructed from Apple Container's inspect data. The effective environment is saved under ~/Library/Application Support/Spyglass/env. To override environment values, set **spyglass_env_file** to the path of a standard KEY=value file; its values take precedence over the captured environment. These files may contain secrets, so keep them private and do not commit them.

## Logging

Spyglass writes a rotating log to ~/Library/Logs/Spyglass

## Run periodically

To run Spyglass periodically, create a LaunchAgent (example below) that invokes the Python
interpreter and script from your cloned checkout. The paths in
`ProgramArguments` must be absolute; launchd does not expand `~` or `$HOME`.
Use `command -v python3` to find your interpreter and `pwd` from the checkout
to find the repository path.

LaunchAgents have a limited `PATH`. Include the directory containing Apple's
`container` executable; find it with `command -v container`. Adjust the
example's `PATH` if your installation uses a different location.

Run it as the same user who owns the containers; **do not run it as root.**

## Launch Agent

Save as `~/Library/LaunchAgents/com.wolfpaulus.spyglass.plist`. Replace the
example interpreter and checkout paths with the absolute paths on your Mac.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wolfpaulus.spyglass</string>

    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/python3</string>
        <string>/Users/yourname/path/to/spyglass/spyglass.py</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>StartInterval</key>
    <integer>3600</integer>
</dict>
</plist>
```

Create the LaunchAgents directory if needed, then load the job:

```shell
mkdir -p ~/Library/LaunchAgents
launchctl bootstrap "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/com.wolfpaulus.spyglass.plist"
```

This is a one-shot job, so it does not need `KeepAlive`. Adjust `StartInterval`
if an hourly check is not appropriate.

And don't worry, launchd will never launch a second overlapping instance of the LaunchAgent when StartInterval triggers while the previous run is still active.

## Coverage

The badge is generated from `coverage.xml`. After running the tests, refresh it with:

```shell
genbadge coverage -i coverage.xml -o coverage.svg -l
```
