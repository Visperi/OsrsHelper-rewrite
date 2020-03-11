# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.1.0 - 2020-3-11

### Added
- `COMMANDS.md` to list all the currently available commands
- Command `nicks` to get saved old in game nicknames for given user

### Changed
- Updated bot commands to be case sensitive
- Changed the way of detection of what account type was requested in commands 'ehp' and 'stats'. They now use an alias 
that was used to invoke command instead of manual parsing.
- Changed the behavior of `visit_website` after a timeout. Exception is now returned instead of None like in any other 
exception situations.

### Fixed
- Fixed a bug where command 'ehp' wouldn't show any xp/h rates if there were only one xp requirement. This required that 
the queried levels and experiences from database had to be changed.
- Fixed a bug where command 'ehp' wouldn't show xp/h rates for 200 million xp if it was in requirements

### Removed
- Removed variables `formatted_skills` and `formatted clues` from `make_scoretable()`

## 1.0.0 - 2019-05-25

### Added
- Started version numbering and maintaining a changelog
- Added command 'info' to get basic information about this bot
- Added command 'me' to show some information about the message author
- Added handling for exception `UserInputError`
- Added `MissingRequiredArgument` into ignored exceptions in `on_command_error()`
- Added combat level to tracked players data and gains command

### Changed
- Updated discord.py to version 1.1.1. This required that cogs have to inherit `commands.Cog`
- Renamed members.py (MembersCog) to discord_cog.py (DiscordCog)
- Updated single-quoted strings and docstring in CommandErrorHandler to follow the style of rest of the project
- Updated the Behavior of `get_drop_chances()`. The amount of kills and boss name are now automatically converted and 
separated when invoking this command.
- Updated some variable names in OsrsCog to be more describing
- Changed all dates to follow ISO 8601 standard
- Changed names of stats command and highscores method to be more distinguishable

### Fixed
- Abbreviation 'cox' for Chambers of Xeric in command 'loot'
- Fixed a bug where accounts combat level was saved to database in a same list with highscore data

### Removed
- Error handling for exception `BadArgument` as redundant
