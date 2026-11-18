![](img/spyglass.jpg)

# Spyglass: Keeping an Eye on Apple Containers

[![macOS](https://img.shields.io/badge/platform-macOS-111111?logo=apple&logoColor=white)](#requirements)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](#requirements)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python runtime dependencies: none](https://img.shields.io/badge/Python%20runtime%20dependencies-none-success.svg)](#requirements)
[![Coverage](coverage.svg)](#coverage)

Spyglass is a **one-shot** command-line tool that keeps selected Apple Containers running and updates them to the latest version of their image. It is not a daemon; schedule it with a macOS LaunchAgent (see below) if you want it to run periodically or at login.

## Requirements

- macOS with Apple's container command-line tool installed and its container service configured
- Python 3.12 or newer for source or PyPI installs; Homebrew installs Python
  for you
- Apple's container executable available on PATH when Spyglass runs

## Install with Homebrew

This project is distributed from a custom Homebrew tap. Add the tap once, then
install the command:

```shell
brew tap wolfpaulus/spyglass https://github.com/wolfpaulus/spyglass
brew install spyglass
spyglass
```

Alternatively, install from PyPI with Python 3.12 or newer:

```shell
python3 -m pip install apple-container-spyglass
spyglass
```

Or clone the GitHub repository and run Spyglass directly:

```shell
git clone https://github.com/wolfpaulus/spyglass.git
cd spyglass
python3 spyglass.py
```

## Choose containers to manage

Spyglass only manages containers labeled `spyglass=true`. Add that label when
creating a container:

```shell
container run --detach --name my-app \
  --label spyglass=true \
  docker.io/library/nginx:latest
```

To manage an existing container, recreate it with the label. For each labeled
container Spyglass pulls its configured image, compares image digests, and
recreates it if the image changed. Updates briefly interrupt the container.
Stopped labeled containers are started. After an update, the old image is
removed by default; add the label `spyglass_rmi=false` to keep it.

Container configuration is reconstructed from Apple Container's inspect data. The effective environment is saved under ~/Library/Application Support/Spyglass/env. To override environment values, set **spyglass_env_file** to the path of a standard KEY=value file; its values take precedence over the captured environment. These files may contain secrets, so keep them private and do not commit them.

## Logging

Spyglass writes a rotating log to ~/Library/Logs/Spyglass

## Run periodically

Use the LaunchAgent template matching your installation:

- [Homebrew installation](./launchd/com.wolfpaulus.spyglass.homebrew.plist)
- [GitHub checkout](./launchd/com.wolfpaulus.spyglass.github.plist)

Copy one template to `~/Library/LaunchAgents/com.wolfpaulus.spyglass.plist`.
Replace its example paths with absolute paths from your Mac; launchd does not
expand `~` or `$HOME`.

- For Homebrew, use `command -v spyglass` for the executable path.
- For a GitHub checkout, use `command -v python3` and the absolute path to
  `spyglass.py` in your checkout.
- For either installation, include the directory containing Apple's `container`
  command in `PATH`; find it with `command -v container`.

Run it as the same user who owns the containers; **do not run it as root.**

Create the LaunchAgents directory if needed, then load the job:

```shell
mkdir -p ~/Library/LaunchAgents
launchctl bootstrap "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/com.wolfpaulus.spyglass.plist"
```

This is a one-shot job, so it does not need `KeepAlive`. Adjust `StartInterval`
if an hourly check is not appropriate.

And don't worry, launchd will never launch a second overlapping instance of the LaunchAgent when StartInterval triggers while the previous run is still active.
