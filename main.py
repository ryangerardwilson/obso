#!/usr/bin/env python3

import os
import re
import shutil
import subprocess
import sys
import tempfile
from hashlib import sha256
from pathlib import Path

from _version import __version__


APP_NAME = "obso"
LEGACY_APP_NAME = "omarchy_branding_safe_overrides"
APP_ROOT = Path(__file__).resolve().parent
INSTALL_SCRIPT = Path(os.environ.get("OBSO_INSTALL_SCRIPT") or APP_ROOT / "install.sh")

HELP_TEXT = """obso
apply safe Omarchy Plymouth logo overrides from your active theme

flags:
  obso -h
    show this help
  obso -v
    print the installed version
  obso -u
    install or refresh this local app

features:
  apply the current theme logo override and ensure the 3-hour background timer
  # obso run
  obso run
"""

THEME_SET_HOOK_LINE = '"$HOME/.config/omarchy/hooks/obso_apply" "$1" >/dev/null 2>&1 || true'
POST_UPDATE_HOOK_LINE = '"$HOME/.config/omarchy/hooks/obso_apply" >/dev/null 2>&1 || true'
LEGACY_THEME_SET_HOOK_LINE = '"$HOME/.config/omarchy/hooks/omarchy_branding_safe_overrides_apply" "$1" >/dev/null 2>&1 || true'
LEGACY_POST_UPDATE_HOOK_LINE = '"$HOME/.config/omarchy/hooks/omarchy_branding_safe_overrides_apply" >/dev/null 2>&1 || true'


def theme_root() -> Path:
    return Path(os.environ.get("OBSO_THEME_ROOT") or Path.home() / ".config/omarchy/themes")


def current_theme_file() -> Path:
    return Path(
        os.environ.get("OBSO_CURRENT_THEME_FILE")
        or Path.home() / ".config/omarchy/current/theme.name"
    )


def hooks_dir() -> Path:
    return Path(os.environ.get("OBSO_HOOKS_DIR") or Path.home() / ".config/omarchy/hooks")


def asset_root() -> Path:
    return Path(
        os.environ.get("OBSO_ASSET_ROOT")
        or Path.home() / ".config/omarchy/obso/assets"
    )


def plymouth_target_dir() -> Path:
    return Path(
        os.environ.get("OBSO_PLYMOUTH_TARGET_DIR") or "/usr/share/plymouth/themes/omarchy"
    )


def systemd_user_dir() -> Path:
    return Path(
        os.environ.get("OBSO_SYSTEMD_USER_DIR")
        or Path.home() / ".config/systemd/user"
    )


def hook_wrapper_path() -> Path:
    return hooks_dir() / f"{APP_NAME}_apply"


def legacy_hook_wrapper_path() -> Path:
    return hooks_dir() / f"{LEGACY_APP_NAME}_apply"


def service_name() -> str:
    return f"{APP_NAME}.service"


def timer_name() -> str:
    return f"{APP_NAME}.timer"


def legacy_service_name() -> str:
    return f"{LEGACY_APP_NAME}.service"


def legacy_timer_name() -> str:
    return f"{LEGACY_APP_NAME}.timer"


def service_path() -> Path:
    return systemd_user_dir() / service_name()


def timer_path() -> Path:
    return systemd_user_dir() / timer_name()


def legacy_service_path() -> Path:
    return systemd_user_dir() / legacy_service_name()


def legacy_timer_path() -> Path:
    return systemd_user_dir() / legacy_timer_name()


def legacy_asset_root() -> Path:
    return Path.home() / ".config/omarchy/branding_safe_overrides/assets"


def app_logo_path(theme_name: str) -> Path:
    return asset_root() / theme_name / "plymouth-logo.png"


def legacy_theme_logo_path(theme_name: str) -> Path:
    return theme_dir(theme_name) / "plymouth-logo.png"


def resolve_theme_name(theme_name: str | None) -> str:
    if theme_name:
        return theme_name
    current = current_theme_file()
    if not current.exists():
        raise SystemExit(f"Current theme file not found: {current}")
    return current.read_text(encoding="utf-8").strip()


def theme_dir(theme_name: str) -> Path:
    return theme_root() / theme_name


def wallpaper_txt_path(theme_name: str) -> Path:
    return theme_dir(theme_name) / "wallpaper.txt"


def wallpaper_svg_path(theme_name: str) -> Path:
    return theme_dir(theme_name) / "wallpaper.svg"


def print_help() -> None:
    print(HELP_TEXT.rstrip())


def install_self() -> int:
    return subprocess.call([str(INSTALL_SCRIPT), "-u"])


def parse_theme_visuals(theme_name: str) -> tuple[str, list[str]]:
    txt_path = wallpaper_txt_path(theme_name)
    svg_path = wallpaper_svg_path(theme_name)

    if not txt_path.exists():
        raise SystemExit(f"Missing wallpaper text: {txt_path}")
    if not svg_path.exists():
        raise SystemExit(f"Missing wallpaper svg: {svg_path}")

    lines = txt_path.read_text(encoding="utf-8").splitlines()
    svg = svg_path.read_text(encoding="utf-8")

    font_match = re.search(r'font-family="([^"]+)"', svg)
    font_family = font_match.group(1) if font_match else "monospace"

    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1

    end = len(lines)
    while end > start and not lines[end - 1].strip():
        end -= 1

    logo_lines = lines[start:end]
    if not logo_lines:
        raise SystemExit(f"No visible logo art in {txt_path}")

    left: int | None = None
    right = 0
    for line in logo_lines:
        stripped = line.rstrip()
        if not stripped:
            continue
        first = next((idx for idx, ch in enumerate(line) if ch != " "), None)
        if first is None:
            continue
        left = first if left is None else min(left, first)
        right = max(right, len(stripped))

    if left is None or right <= left:
        raise SystemExit(f"No visible logo art in {txt_path}")

    cropped = [line[left:right].rstrip() for line in logo_lines]
    return font_family, cropped


def require_command(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"Required command not found: {name}")
    return path


def resolve_font_file(font_family: str) -> str:
    fc_match = require_command(os.environ.get("OBSO_FC_MATCH_BIN", "fc-match"))
    result = subprocess.run(
        [fc_match, "-f", "%{file}\n", font_family],
        check=False,
        capture_output=True,
        text=True,
    )
    font_file = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    if result.returncode != 0 or not font_file:
        raise SystemExit(f"Unable to resolve font file for {font_family}")
    return font_file


def build_logo(theme_name: str | None) -> Path:
    resolved = resolve_theme_name(theme_name)
    font_family, cropped_lines = parse_theme_visuals(resolved)
    font_file = resolve_font_file(font_family)
    magick = require_command(os.environ.get("OBSO_MAGICK_BIN", "magick"))

    output = app_logo_path(resolved)
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("\n".join(cropped_lines) + "\n")
        temp_txt = Path(handle.name)

    try:
        result = subprocess.run(
            [
                magick,
                "-background",
                "none",
                "-fill",
                "#ffffff",
                "-font",
                font_file,
                "-pointsize",
                "36",
                f"label:@{temp_txt}",
                "-trim",
                "+repage",
                "-resize",
                "800x188",
                "-gravity",
                "center",
                "-background",
                "none",
                "-extent",
                "800x188",
                str(output),
            ],
            check=False,
            text=True,
            capture_output=True,
        )
    finally:
        temp_txt.unlink(missing_ok=True)

    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "Failed to build Plymouth logo")

    return output


def run_root(command: list[str]) -> int:
    cmd = list(command)
    if os.geteuid() != 0:
        cmd.insert(0, "sudo")
        if os.environ.get("OBSO_NONINTERACTIVE_SUDO") == "1":
            cmd.insert(1, "-n")
    return subprocess.call(cmd)


def rebuild_initramfs() -> int:
    if shutil.which("limine-mkinitcpio"):
        return run_root(["limine-mkinitcpio"])
    return run_root(["mkinitcpio", "-P"])


def file_digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def apply_logo(theme_name: str | None) -> int:
    resolved = resolve_theme_name(theme_name)
    logo = build_logo(resolved)
    target_dir = plymouth_target_dir()
    target_logo = target_dir / "logo.png"

    if target_logo.exists() and file_digest(logo) == file_digest(target_logo):
        print(f"Plymouth logo already current for theme: {resolved}")
        print(f"App asset: {logo}")
        return 0

    rc = run_root(["install", "-m", "0644", str(logo), str(target_logo)])
    if rc != 0:
        return rc

    rc = run_root(["plymouth-set-default-theme", "omarchy"])
    if rc != 0:
        return rc

    rc = rebuild_initramfs()
    if rc == 0:
        print(f"Applied Plymouth logo for theme: {resolved}")
        print(f"App asset: {logo}")
    return rc


def ensure_wrapper_script() -> Path:
    wrapper = hook_wrapper_path()
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    launcher = APP_ROOT / APP_NAME
    content = "\n".join(
        [
            "#!/bin/bash",
            "set -euo pipefail",
            f'if command -v {APP_NAME} >/dev/null 2>&1; then',
            f'  exec env OBSO_SKIP_RUNTIME_INSTALL=1 {APP_NAME} run',
            "fi",
            f'exec env OBSO_SKIP_RUNTIME_INSTALL=1 "{launcher}" run',
            "",
        ]
    )
    wrapper.write_text(content, encoding="utf-8")
    wrapper.chmod(0o755)
    legacy_hook_wrapper_path().unlink(missing_ok=True)
    return wrapper


def ensure_theme_set_hook() -> None:
    path = hooks_dir() / "theme-set"
    if not path.exists():
        path.write_text("#!/bin/bash\n\nset -euo pipefail\n\n", encoding="utf-8")
        path.chmod(0o755)

    text = path.read_text(encoding="utf-8")
    cleaned = text.replace(
        '"$HOME/.config/omarchy/hooks/sync-plymouth-logo" "$1"\n', ""
    )
    cleaned = cleaned.replace(f"{LEGACY_THEME_SET_HOOK_LINE}\n", "")
    if THEME_SET_HOOK_LINE not in cleaned:
        if not cleaned.endswith("\n"):
            cleaned += "\n"
        cleaned += f"\n{THEME_SET_HOOK_LINE}\n"
    path.write_text(cleaned, encoding="utf-8")
    path.chmod(0o755)


def ensure_post_update_hook() -> None:
    path = hooks_dir() / "post-update"
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = "#!/bin/bash\n\nset -euo pipefail\n"

    cleaned = text.replace('"$HOME/.config/omarchy/hooks/sync-plymouth-logo"\n', "")
    cleaned = cleaned.replace(f"{LEGACY_POST_UPDATE_HOOK_LINE}\n", "")
    if POST_UPDATE_HOOK_LINE not in cleaned:
        if not cleaned.endswith("\n"):
            cleaned += "\n"
        cleaned += f"\n{POST_UPDATE_HOOK_LINE}\n"

    path.write_text(cleaned, encoding="utf-8")
    path.chmod(0o755)


def ensure_service_unit() -> None:
    path = service_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            "[Unit]",
            "Description=Reapply safe Omarchy Plymouth branding override",
            "",
            "[Service]",
            "Type=oneshot",
            "Environment=OBSO_NONINTERACTIVE_SUDO=1",
            "Environment=OBSO_SKIP_RUNTIME_INSTALL=1",
            f"ExecStart={hook_wrapper_path()}",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def ensure_timer_unit() -> None:
    path = timer_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            "[Unit]",
            "Description=Reapply safe Omarchy Plymouth branding override every 3 hours",
            "",
            "[Timer]",
            "OnBootSec=5m",
            "OnUnitActiveSec=3h",
            "Persistent=true",
            f"Unit={service_name()}",
            "",
            "[Install]",
            "WantedBy=timers.target",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def systemctl_bin() -> str:
    return require_command(os.environ.get("OBSO_SYSTEMCTL_BIN", "systemctl"))


def migrate_legacy_assets() -> None:
    legacy_root = legacy_asset_root()
    current_root = asset_root()
    if legacy_root == current_root or not legacy_root.exists():
        return
    current_root.parent.mkdir(parents=True, exist_ok=True)
    if current_root.exists():
        shutil.rmtree(legacy_root)
        return
    shutil.move(str(legacy_root), str(current_root))


def cleanup_legacy_timer(systemctl: str) -> None:
    subprocess.run(
        [systemctl, "--user", "disable", "--now", legacy_timer_name()],
        check=False,
        capture_output=True,
        text=True,
    )
    legacy_service_path().unlink(missing_ok=True)
    legacy_timer_path().unlink(missing_ok=True)


def enable_timer() -> None:
    systemctl = systemctl_bin()
    cleanup_legacy_timer(systemctl)
    subprocess.run([systemctl, "--user", "daemon-reload"], check=True)
    subprocess.run([systemctl, "--user", "enable", "--now", timer_name()], check=True)


def install_hooks() -> int:
    migrate_legacy_assets()
    ensure_wrapper_script()
    ensure_theme_set_hook()
    ensure_post_update_hook()
    ensure_service_unit()
    ensure_timer_unit()
    enable_timer()
    print(f"Installed hook wrapper: {hook_wrapper_path()}")
    print(f"Updated hook: {hooks_dir() / 'theme-set'}")
    print(f"Updated hook: {hooks_dir() / 'post-update'}")
    print(f"Installed service: {service_path()}")
    print(f"Installed timer: {timer_path()}")
    return 0


def run_command() -> int:
    if os.environ.get("OBSO_SKIP_RUNTIME_INSTALL") != "1":
        rc = install_hooks()
        if rc != 0:
            return rc
    return apply_logo(None)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args == ["-h"]:
        print_help()
        return 0

    if args == ["-v"]:
        print(__version__)
        return 0

    if args == ["-u"]:
        return install_self()

    if args == ["--install-runtime"]:
        return install_hooks()

    if args == ["run"]:
        return run_command()

    print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
