# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.0.0 2019-05-25

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
