# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## [0.2.0](https://github.com/pawamoy/yore/releases/tag/0.2.0) - 2024-08-14

<small>[Compare with 0.1.0](https://github.com/pawamoy/yore/compare/0.1.0...0.2.0)</small>

### Breaking changes

- `yore.cli.CommandCheck.warn_before_eol`: *Public object was renamed `eol_within`*
- `yore.cli.CommandCheck.__init__(warn_before_eol)`: *Parameter was renamed `eol_within`*
- `yore.cli.CommandFix.fix_before_eol`: *Public object was renamed `eol_within`*
- `yore.cli.CommandFix.__init__(fix_before_eol)`: *Parameter was renamed `eol_within`*
- `yore.lib.BlockOrLine`: *Public object was removed*
- `yore.lib.YoreComment.check(bump)`: *Parameter kind was changed*: `positional or keyword` -> `keyword-only`
- `yore.lib.YoreComment.check(warn_before_eol)`: *Parameter was renamed `eol_within`*
- `yore.lib.YoreComment.fix(bump)`: *Parameter kind was changed*: `positional or keyword` -> `keyword-only`
- `yore.lib.YoreComment.fix(fix_before_eol)`: *Parameter was renamed `eol_within`*
- `yore.lib.eol_dates`: *Public object was renamed `python_dates`*

### Features

- Implement BOL (Beginning of Life) comments ([57f9e90](https://github.com/pawamoy/yore/commit/57f9e90970f4b5a162490d35875e271de00604a7) by Timothée Mazzucotelli). [Issue-5](https://github.com/pawamoy/yore/issues/5)
- Support "file" scope ([11e0cd2](https://github.com/pawamoy/yore/commit/11e0cd21693e553238d6817a7b5c5d76efc1e868) by Timothée Mazzucotelli). [Issue-2](https://github.com/pawamoy/yore/issues/2)

## [0.1.0](https://github.com/pawamoy/yore/releases/tag/0.1.0) - 2024-06-27

<small>[Compare with first commit](https://github.com/pawamoy/yore/compare/30ec3c10ea02e966331124ac8f81ceabe4be46f9...0.1.0)</small>

### Features

- Implement initial version ([68ca0cb](https://github.com/pawamoy/yore/commit/68ca0cbe64ee1d0511c67961051724e5c640a99c) by Timothée Mazzucotelli).
- Generate project with Copier UV template ([30ec3c1](https://github.com/pawamoy/yore/commit/30ec3c10ea02e966331124ac8f81ceabe4be46f9) by Timothée Mazzucotelli).
