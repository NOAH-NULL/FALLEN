# TITAN V16 implementation rules

## Command-count target

The product target is 600+ useful Discord-focused commands/capabilities. This is a target, not a claim that the current archive already contains 600 implementations. Roadmap items must not be registered as commands until they have working behavior.

## Acceptance gate for every command

A command can be exposed in help only when it has:

1. A real Discord action or service implementation (not a placeholder acknowledgement).
2. Input validation and useful failure messages.
3. Permission checks appropriate to the action, including hierarchy checks for moderation/role operations.
4. Prefix `,` and slash interfaces where the action is suitable for both, backed by shared service logic.
5. Persistent storage for configuration/history/state that must survive restarts.
6. Audit logging for security-sensitive changes.
7. Tests for normal behavior, invalid input, permission failures, and service/API failures.

## Help system

- `,help [search]`, aliases `,commands` and `,cmds` list the actual registered prefix and slash commands.
- `/help [query]` offers the same inventory privately.
- `,help-category <category>` and `,helpcat <category>` filter by registered command category.
- Results are paginated using interactive buttons. Search terms match command syntax, description, and category.
- The default discord.py help command is disabled so the custom help implementation is the single source of truth.
- Roadmap-only items and unregistered commands are never advertised.

## Delivery policy

Implement in testable batches. Do not advertise 600+ commands as completed until the codebase has 600+ real, reviewed command implementations and the full test suite has been run against the packaged archive.
