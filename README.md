# obso

Safe, user-owned Omarchy Plymouth branding overrides.

This app builds an app-owned Plymouth logo override from the active Omarchy
theme's wallpaper art, forces it to a white silhouette, reapplies it after
theme changes and Omarchy updates, and avoids editing Omarchy-managed defaults
under `~/.local/share/omarchy/`.

## Install

From this local checkout:

```bash
./install.sh -u
```

If `~/.local/bin` is not already on your `PATH`, add this line to `~/.bashrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Usage

```bash
obso -h
obso -v
obso -u
obso run
```

## Notes

- Generated logos are stored under
  `~/.config/omarchy/obso/assets/<theme>/plymouth-logo.png`.
- Theme source assets are read from `~/.config/omarchy/themes/<theme>/`.
- `run` applies the override for the active theme and ensures the 3-hour
  background timer is installed.
- `run` still needs `sudo`, because Plymouth assets live under
  `/usr/share/plymouth/themes/omarchy/`.
