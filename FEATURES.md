# FALLEN — implemented feature overview

This file lists major systems present in the repository. It is not a promise that every feature is enabled in every Discord server; behavior can depend on permissions, configuration, external services, and deployment setup.

## Moderation
- Ban, kick, timeout, and untimeout
- Warning records with active warning-point totals and optional expiry
- Scheduled temporary timeouts and temporary bans
- Moderation cases and moderation logging
- Message cleanup, slowmode, and channel lockdown controls

## AutoMod and security
- Message-flood detection
- Configurable AutoMod rule matching and moderation actions
- Anti-raid tracking and join-time checks
- Security event handling, lockdown, and quarantine workflows
- Redis-backed coordination and temporary security state

## Community and administration
- Welcome and goodbye messages
- Leveling and level-role rewards
- Tickets, suggestions, polls, and custom commands
- Economy and daily rewards
- Reminders and server configuration

## External dependencies and limitations
- Music requires an independently hosted Lavalink v4 node.
- Music queue and playback state are in-memory and are not restored after a bot restart.
- The Control Center API is an early-stage FastAPI scaffold; see the README for its current deployment and session limitations.

For planned work, use GitHub Issues rather than treating an unimplemented capability catalog as a shipped feature list.

The capability configuration group is exposed as `/fallen` and `,fallen`; `v16` remains a legacy prefix-command alias.
