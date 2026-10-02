# Fallen V16 — exact 100 capability matrix

| # | Domain | Capability | Runtime owner |
|---:|---|---|---|
| 1-15 | Security | anti-bot, account age, suspicious names, raid rate, lockdown/recovery, deletion/webhook/permission/mass-ban protection, timeline, trusted admins, emergency lock, backup | `bot/services/v16_runtime.py`, `ExtremeService` |
| 16-30 | Moderation | temporary/scheduled punishments, warning expiry/points, escalation, notes, case tools, reports, approvals, statistics | `ModerationService`, `ExtremeService`, scheduler |
| 31-40 | AutoMod | regex, duplicate/flood/emoji/sticker/attachment, domain allow/deny, mention spam, custom actions | `V16Runtime`, `AutoModRule` |
| 41-50 | Leveling | voice/activity XP, boosters/multipliers, weekends, seasons, prestige, rank customization, level-up behavior | `LevelService`, V16 settings |
| 51-60 | Community | reputation, profiles, badges/colors, birthdays, anniversaries, milestones, challenges, quests, achievements | `ExtremeService`, profile/reputation models |
| 61-70 | Engagement | rewards, streaks, trivia, word/number/reaction games, tournaments, voting, challenges, events | engagement commands/services + V16 settings |
| 71-80 | Music | DJ/permissions, queues/presets, personal/server playlists, autoplay/recovery/persistence/history | music adapter + playlist persistence |
| 81-90 | Tickets | categories/forms/claiming/priority/transcripts/ratings/statistics/auto-close/staff notes/reopen | `TicketService`, V16 ticket model |
| 91-100 | Administration | snapshots/import-export/setup, permission/hierarchy/channel checks, health/diagnostics/validation, backup/restore | `ExtremeService`, core health, snapshots |

The numbered list remains exactly the 100-feature contract from V16. Capabilities that require an external provider (for example actual Lavalink audio playback) remain provider adapters rather than fake local implementations.
