# obso Agent Guide

## Scope
- This app exists only to apply safe, user-owned Omarchy branding overrides.
- Keep it focused on Plymouth boot branding that Omarchy would otherwise overwrite.
- Do not expand it into a generic Omarchy patch manager unless the user explicitly asks.

## Product Rules
- The durable source of truth must stay in user-owned paths under `~/.config/`, not under `~/.local/share/omarchy/`.
- Prefer automation through Omarchy's supported hook surface in `~/.config/omarchy/hooks/`.
- App-owned generated assets under `~/.config/omarchy/obso/` are the preferred source of truth.
- Theme repos under `~/.config/omarchy/themes/<theme>/` should not own durable Plymouth logo output for this app.

## Contract Deviation
- This is currently a local-first workspace utility, not a published release-managed app yet.
- Until the user asks for a GitHub repo and release flow, keep installer behavior local-checkout based instead of assuming remote GitHub releases.
