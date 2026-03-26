import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


APP_ROOT = Path(__file__).resolve().parents[1]
MAIN = APP_ROOT / "main.py"


def run_app(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    base_env = os.environ.copy()
    if env:
        base_env.update(env)
    return subprocess.run(
        [sys.executable, str(MAIN), *args],
        capture_output=True,
        text=True,
        check=False,
        env=base_env,
    )


class MainContractTests(unittest.TestCase):
    def test_no_args_matches_dash_h(self):
        no_args = run_app()
        help_args = run_app("-h")
        self.assertEqual(no_args.returncode, 0)
        self.assertEqual(no_args.stdout, help_args.stdout)

    def test_version_is_single_line(self):
        result = run_app("-v")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "0.0.0")

    def test_build_uses_current_theme_and_writes_app_owned_logo(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            theme_root = temp / "themes"
            asset_root = temp / "assets"
            theme_dir = theme_root / "mono-dark"
            theme_dir.mkdir(parents=True)
            (theme_dir / "wallpaper.txt").write_text(
                "\n\n"
                "    ██  ██\n"
                "    ██  ██\n"
                "\n",
                encoding="utf-8",
            )
            (theme_dir / "wallpaper.svg").write_text(
                '<svg><text fill="#ffffff" font-family="JetBrainsMono Nerd Font Mono"></text></svg>',
                encoding="utf-8",
            )
            current_theme = temp / "theme.name"
            current_theme.write_text("mono-dark\n", encoding="utf-8")

            fc_match = temp / "fc-match"
            fc_match.write_text(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' /tmp/fake-font.ttf\n",
                encoding="utf-8",
            )
            fc_match.chmod(0o755)

            magick = temp / "magick"
            magick.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "from pathlib import Path\n"
                "Path(sys.argv[-1]).write_bytes(b'png')\n",
                encoding="utf-8",
            )
            magick.chmod(0o755)

            result = run_app(
                "build",
                env={
                    "OBSO_THEME_ROOT": str(theme_root),
                    "OBSO_ASSET_ROOT": str(asset_root),
                    "OBSO_CURRENT_THEME_FILE": str(current_theme),
                    "OBSO_FC_MATCH_BIN": str(fc_match),
                    "OBSO_MAGICK_BIN": str(magick),
                },
            )

            self.assertEqual(result.returncode, 0)
            output = Path(result.stdout.strip())
            self.assertTrue(output.exists())
            self.assertEqual(output.read_bytes(), b"png")
            self.assertEqual(output, asset_root / "mono-dark" / "plymouth-logo.png")

    def test_hooks_command_installs_wrapper_hooks_and_timer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            hooks_dir = temp / "hooks"
            systemd_user_dir = temp / "systemd-user"
            hooks_dir.mkdir()
            theme_set = hooks_dir / "theme-set"
            theme_set.write_text("#!/bin/bash\n\necho existing\n", encoding="utf-8")

            systemctl = temp / "systemctl"
            systemctl.write_text(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' \"$*\" >> \"$OBSO_SYSTEMCTL_LOG\"\n",
                encoding="utf-8",
            )
            systemctl.chmod(0o755)

            systemctl_log = temp / "systemctl.log"
            result = run_app(
                "hooks",
                env={
                    "OBSO_HOOKS_DIR": str(hooks_dir),
                    "OBSO_SYSTEMD_USER_DIR": str(systemd_user_dir),
                    "OBSO_SYSTEMCTL_BIN": str(systemctl),
                    "OBSO_SYSTEMCTL_LOG": str(systemctl_log),
                },
            )
            self.assertEqual(result.returncode, 0)

            wrapper = hooks_dir / "obso_apply"
            self.assertTrue(wrapper.exists())
            self.assertIn(
                'obso_apply" "$1" >/dev/null 2>&1 || true',
                theme_set.read_text(encoding="utf-8"),
            )
            self.assertIn(
                'obso_apply" >/dev/null 2>&1 || true',
                (hooks_dir / "post-update").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "OnUnitActiveSec=3h",
                (systemd_user_dir / "obso.timer").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertIn(
                "ExecStart=",
                (systemd_user_dir / "obso.service").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertEqual(
                systemctl_log.read_text(encoding="utf-8").splitlines(),
                [
                    "--user disable --now omarchy_branding_safe_overrides.timer",
                    "--user daemon-reload",
                    "--user enable --now obso.timer",
                ],
            )

    def test_upgrade_invokes_install_script_with_dash_u(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            marker = Path(temp_dir) / "marker.txt"
            install_script = Path(temp_dir) / "install.sh"
            install_script.write_text(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' \"$*\" > \"$OBSO_MARKER\"\n",
                encoding="utf-8",
            )
            install_script.chmod(0o755)

            result = run_app(
                "-u",
                env={
                    "OBSO_INSTALL_SCRIPT": str(install_script),
                    "OBSO_MARKER": str(marker),
                },
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(encoding="utf-8").strip(), "-u")


if __name__ == "__main__":
    unittest.main()
