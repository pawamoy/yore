# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## [0.4.1](https://github.com/pawamoy/yore/releases/tag/0.4.1) - 2025-03-19

<small>[Compare with 0.4.0](https://github.com/pawamoy/yore/compare/0.4.0...0.4.1)</small>

### Bug Fixes

- Don't crash with unicode decode errors ([cdd7227](https://github.com/pawamoy/yore/commit/cdd7227cf3919c8d008d9089809e01ed878709ef) by Timothée Mazzucotelli).

## [0.4.0](https://github.com/pawamoy/yore/releases/tag/0.4.0) - 2025-03-19

<small>[Compare with 0.3.4](https://github.com/pawamoy/yore/compare/0.3.4...0.4.0)</small>

### Features

- Add `yore diff` command ([590851d](https://github.com/pawamoy/yore/commit/590851d295e77acbf4cb5c7622d2d115c99c1ed3) by Timothée Mazzucotelli). [Issue-12](https://github.com/pawamoy/yore/issues/12)
- Support config files, add prefix option ([708a6c0](https://github.com/pawamoy/yore/commit/708a6c03932355ccb1598e1e028dcf23e17762ec) by Timothée Mazzucotelli). [Issue-8](https://github.com/pawamoy/yore/issues/8)
- Check comments validity ([abd31e3](https://github.com/pawamoy/yore/commit/abd31e3f42616d741c744c578b9b3f72f674e2be) by Timothée Mazzucotelli). [Issue-13](https://github.com/pawamoy/yore/issues/13)
- Support many more languages and list files with Git ([2f7bb5f](https://github.com/pawamoy/yore/commit/2f7bb5fb92e9ad561068bdc8471908e156cae00e) by Timothée Mazzucotelli). [Issue-4](https://github.com/pawamoy/yore/issues/4)

### Code Refactoring

- Simplify CLI invocation ([c727477](https://github.com/pawamoy/yore/commit/c727477ab5afd34922a67637ebe4afd2c0a17dc9) by Timothée Mazzucotelli).
- Shorten messages, display original comment ([c49a5b0](https://github.com/pawamoy/yore/commit/c49a5b0f05d8d62dc74c75b54cccdc6f12a75230) by Timothée Mazzucotelli).

## [0.3.4](https://github.com/pawamoy/yore/releases/tag/0.3.4) - 2025-03-08

<small>[Compare with 0.3.3](https://github.com/pawamoy/yore/compare/0.3.3...0.3.4)</small>

### Bug Fixes

- Exit with code 1 if `yore check` found issues ([a32c470](https://github.com/pawamoy/yore/commit/a32c47073b1aa58971b6ee712a7f3b33e61928c4) by Timothée Mazzucotelli).

## [0.3.3](https://github.com/pawamoy/yore/releases/tag/0.3.3) - 2025-02-25

<small>[Compare with 0.3.2](https://github.com/pawamoy/yore/compare/0.3.2...0.3.3)</small>

### Bug Fixes

- Remove a leftover investigation `print` ([3ec4795](https://github.com/pawamoy/yore/commit/3ec4795e50c5727059e0aceb5b155d5d9067784b) by Bartosz Sławecki). [PR-11](https://github.com/pawamoy/yore/pull/11)

## [0.3.2](https://github.com/pawamoy/yore/releases/tag/0.3.2) - 2025-02-25

<small>[Compare with 0.3.1](https://github.com/pawamoy/yore/compare/0.3.1...0.3.2)</small>

### Bug Fixes

- Fix `yore` script path ([f877a6b](https://github.com/pawamoy/yore/commit/f877a6bff48746724fb1c27c0d5ace378a62f02e) by Bartosz Sławecki). [PR-10](https://github.com/pawamoy/yore/pull/10)

## [0.3.1](https://github.com/pawamoy/yore/releases/tag/0.3.1) - 2025-02-24

<small>[Compare with 0.3.0](https://github.com/pawamoy/yore/compare/0.3.0...0.3.1)</small>

### Code Refactoring

- Move modules under `_internal`, update docs ([7d59de0](https://github.com/pawamoy/yore/commit/7d59de0593a79bb7be46fda3008bae36cb8eadc9) by Timothée Mazzucotelli).

## [0.3.0](https://github.com/pawamoy/yore/releases/tag/0.3.0) - 2025-02-24

<small>[Compare with 0.2.0](https://github.com/pawamoy/yore/compare/0.2.0...0.3.0)</small>

### Features

- Support Python 3.9 ([2add5f8](https://github.com/pawamoy/yore/commit/2add5f8d97dfb043ab5b4bb3afe08e7333392937) by Timothée Mazzucotelli). [Issue-9](https://github.com/pawamoy/yore/issues/9)

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
