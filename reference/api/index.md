# yore

yore package.

Manage legacy code with comments.

Classes:

- **`CommandCheck`** – Command to check Yore comments.
- **`CommandDiff`** – Command to diff Yore comments.
- **`CommandFix`** – Command to fix Yore comments.
- **`CommandMain`** – Command to manage legacy code in your code base with YORE comments.
- **`Config`** – Configuration for the insiders project.
- **`Unset`** – A sentinel value for unset configuration options.
- **`YoreComment`** – A Yore comment.

Functions:

- **`config_field`** – Create a dataclass field with a TOML key.
- **`get_pattern`** – Get the Yore comment pattern with a specific prefix.
- **`main`** – Run the main program.
- **`yield_buffer_comments`** – Yield all Yore comments in a buffer.
- **`yield_directory_comments`** – Yield all Yore comments in a directory.
- **`yield_file_comments`** – Yield all Yore comments in a file.
- **`yield_files`** – Yield all files in a directory.
- **`yield_path_comments`** – Yield all Yore comments in a file or directory.

Attributes:

- **`COMMENT_PATTERN`** (`str`) – The Yore comment pattern, as a regular expression.
- **`COMMENT_PREFIXES`** (`set[str]`) – The supported comment prefixes.
- **`DEFAULT_EXCLUDE`** – The default patterns to exclude when scanning directories.
- **`DEFAULT_PREFIX`** – The default prefix for Yore comments.
- **`Scope`** – The scope of a comment.
- **`YoreKind`** – The supported kinds of Yore comments.
- **`python_dates`** – A dictionary of Python versions and their Beginning/End of Life dates.

## COMMENT_PATTERN

```
COMMENT_PATTERN: str = "\n    (?P<kind>bol|bump|eol)\\ (?P<version>[^:]+):\\ (?:\n        remove\\ (?P<remove>block|file|line)\n        |\n        replace\\ (?P<replace>block|file|line)\\ with\\ (?:\n            line\\ (?P<line>\\d+)\n            |\n            lines\\ (?P<lines>[\\d, -]+)\n            |\n            `(?P<string>.+?)`\n        )\n        |\n        (?P<regex>regex-)?replace\\ `(?P<pattern1>.+?)`\\ with\\ `(?P<pattern2>.*?)`\\ within\\ (?P<within>block|file|line)\n    )\n"

```

The Yore comment pattern, as a regular expression.

## COMMENT_PREFIXES

```
COMMENT_PREFIXES: set[str] = {
    "\\#\\ ",
    "//\\ ",
    "--\\ ",
    ";",
    "%\\ ",
    "'\\ ?",
    "/\\*\\ ",
    "<!--\\ ",
    "\\{\\#-?\\ ",
    "\\(\\*\\ ",
}

```

The supported comment prefixes.

## DEFAULT_EXCLUDE

```
DEFAULT_EXCLUDE = ['.*', '__py*', 'build', 'dist']

```

The default patterns to exclude when scanning directories.

## DEFAULT_PREFIX

```
DEFAULT_PREFIX = 'YORE'

```

The default prefix for Yore comments.

## Scope

```
Scope = Literal['block', 'file', 'line']

```

The scope of a comment.

## YoreKind

```
YoreKind = Literal['bump', 'eol', 'bol']

```

The supported kinds of Yore comments.

## python_dates

```
python_dates = _LazyPythonDates()

```

A dictionary of Python versions and their Beginning/End of Life dates.

## CommandCheck

```
CommandCheck(
    paths: list[Path] = list(),
    bump: str | None = None,
    eol_within: timedelta | None = None,
    bol_within: timedelta | None = None,
    prefix: str = DEFAULT_PREFIX,
)

```

Command to check Yore comments.

Methods:

- **`__call__`** – Check Yore comments.

Attributes:

- **`bol_within`** (`timedelta | None`) – The time delta to start checking before the Beginning of Life of a Python version.
- **`bump`** (`str | None`) – The next version of your project.
- **`eol_within`** (`timedelta | None`) – The time delta to start checking before the End of Life of a Python version.
- **`paths`** (`list[Path]`) – Path to files or directories to check.
- **`prefix`** (`str`) – The prefix for Yore comments.

### bol_within

```
bol_within: timedelta | None = None

```

The time delta to start checking before the Beginning of Life of a Python version. It is provided in a human-readable format, like `2 weeks` or `1 month`. Spaces are optional, and the unit can be shortened to a single letter: `d` for days, `w` for weeks, `m` for months, and `y` for years.

### bump

```
bump: str | None = None

```

The next version of your project.

### eol_within

```
eol_within: timedelta | None = None

```

The time delta to start checking before the End of Life of a Python version. It is provided in a human-readable format, like `2 weeks` or `1 month`. Spaces are optional, and the unit can be shortened to a single letter: `d` for days, `w` for weeks, `m` for months, and `y` for years.

### paths

```
paths: list[Path] = field(default_factory=list)

```

Path to files or directories to check.

### prefix

```
prefix: str = DEFAULT_PREFIX

```

The prefix for Yore comments.

### __call__

```
__call__() -> int

```

Check Yore comments.

Source code in `src/yore/_internal/cli.py`

```
def __call__(self) -> int:
    """Check Yore comments."""
    ok = True
    paths = self.paths or [Path(".")]
    for path in paths:
        for comment in yield_path_comments(path, prefix=self.prefix):
            ok &= comment.check(bump=self.bump, eol_within=self.eol_within, bol_within=self.bol_within)
    return 0 if ok else 1

```

## CommandDiff

```
CommandDiff(
    paths: list[Path] = list(),
    bump: str | None = None,
    eol_within: timedelta | None = None,
    bol_within: timedelta | None = None,
    highlight: str | None = None,
    prefix: str = DEFAULT_PREFIX,
)

```

Command to diff Yore comments.

Methods:

- **`__call__`** – Diff Yore comments.

Attributes:

- **`bol_within`** (`timedelta | None`) – The time delta to start diffing before the Beginning of Life of a Python version.
- **`bump`** (`str | None`) – The next version of your project.
- **`eol_within`** (`timedelta | None`) – The time delta to start diffing before the End of Life of a Python version.
- **`highlight`** (`str | None`) – The command to highlight diffs.
- **`paths`** (`list[Path]`) – Path to files or directories to diff.
- **`prefix`** (`str`) – The prefix for Yore comments.

### bol_within

```
bol_within: timedelta | None = None

```

The time delta to start diffing before the Beginning of Life of a Python version. It is provided in a human-readable format, like `2 weeks` or `1 month`. Spaces are optional, and the unit can be shortened to a single letter: `d` for days, `w` for weeks, `m` for months, and `y` for years.

### bump

```
bump: str | None = None

```

The next version of your project.

### eol_within

```
eol_within: timedelta | None = None

```

The time delta to start diffing before the End of Life of a Python version. It is provided in a human-readable format, like `2 weeks` or `1 month`. Spaces are optional, and the unit can be shortened to a single letter: `d` for days, `w` for weeks, `m` for months, and `y` for years.

### highlight

```
highlight: str | None = None

```

The command to highlight diffs.

### paths

```
paths: list[Path] = field(default_factory=list)

```

Path to files or directories to diff.

### prefix

```
prefix: str = DEFAULT_PREFIX

```

The prefix for Yore comments.

### __call__

```
__call__() -> int

```

Diff Yore comments.

Source code in `src/yore/_internal/cli.py`

```
def __call__(self) -> int:
    """Diff Yore comments."""
    lines = self._diff_paths(self.paths or [Path(".")])
    if self.highlight:
        process = subprocess.Popen(self.highlight, shell=True, text=True, stdin=subprocess.PIPE)  # noqa: S602
        for line in lines:
            process.stdin.write(line)  # type: ignore[union-attr]
        process.stdin.close()  # type: ignore[union-attr]
        process.wait()
        return int(process.returncode)
    for line in lines:
        print(line, end="")
    return 0

```

## CommandFix

```
CommandFix(
    paths: list[Path] = list(),
    bump: str | None = None,
    eol_within: timedelta | None = None,
    bol_within: timedelta | None = None,
    prefix: str = DEFAULT_PREFIX,
)

```

Command to fix Yore comments.

Methods:

- **`__call__`** – Fix Yore comments.

Attributes:

- **`bol_within`** (`timedelta | None`) – The time delta to start fixing before the Beginning of Life of a Python version.
- **`bump`** (`str | None`) – The next version of your project.
- **`eol_within`** (`timedelta | None`) – The time delta to start fixing before the End of Life of a Python version.
- **`paths`** (`list[Path]`) – Path to files or directories to fix.
- **`prefix`** (`str`) – The prefix for Yore comments.

### bol_within

```
bol_within: timedelta | None = None

```

The time delta to start fixing before the Beginning of Life of a Python version. It is provided in a human-readable format, like `2 weeks` or `1 month`. Spaces are optional, and the unit can be shortened to a single letter: `d` for days, `w` for weeks, `m` for months, and `y` for years.

### bump

```
bump: str | None = None

```

The next version of your project.

### eol_within

```
eol_within: timedelta | None = None

```

The time delta to start fixing before the End of Life of a Python version. It is provided in a human-readable format, like `2 weeks` or `1 month`. Spaces are optional, and the unit can be shortened to a single letter: `d` for days, `w` for weeks, `m` for months, and `y` for years.

### paths

```
paths: list[Path] = field(default_factory=list)

```

Path to files or directories to fix.

### prefix

```
prefix: str = DEFAULT_PREFIX

```

The prefix for Yore comments.

### __call__

```
__call__() -> int

```

Fix Yore comments.

Source code in `src/yore/_internal/cli.py`

```
def __call__(self) -> int:
    """Fix Yore comments."""
    paths = self.paths or [Path(".")]
    for path in paths:
        if path.is_file():
            self._fix(path)
        else:
            for file in yield_files(path):
                self._fix(file)
    return 0

```

## CommandMain

```
CommandMain(
    subcommand: Subcommands[
        CommandCheck | CommandDiff | CommandFix
    ],
    config: Config = _load_config(),
    version: bool = False,
    debug_info: bool = False,
)

```

Command to manage legacy code in your code base with YORE comments.

Attributes:

- **`config`** (`Config`) – Path to the configuration file.
- **`debug_info`** (`bool`) – Print debug information.
- **`subcommand`** (`Subcommands[CommandCheck | CommandDiff | CommandFix]`) – The selected subcommand.
- **`version`** (`bool`) – Version CLI option.

### config

```
config: Config = field(default_factory=_load_config)

```

Path to the configuration file.

### debug_info

```
debug_info: bool = False

```

Print debug information.

### subcommand

```
subcommand: Subcommands[
    CommandCheck | CommandDiff | CommandFix
]

```

The selected subcommand.

### version

```
version: bool = False

```

Version CLI option.

## Config

```
Config(
    prefix: list[str] | Unset = config_field("prefix"),
    diff_highlight: str | Unset = config_field(
        "diff.highlight"
    ),
)

```

Configuration for the insiders project.

Methods:

- **`from_data`** – Load configuration from data.
- **`from_default_locations`** – Load configuration from the default locations.
- **`from_file`** – Load configuration from a file.
- **`from_pyproject`** – Load configuration from pyproject.toml.

Attributes:

- **`diff_highlight`** (`str | Unset`) – The command to highlight diffs.
- **`prefix`** (`list[str] | Unset`) – The prefix for Yore comments.

### diff_highlight

```
diff_highlight: str | Unset = config_field("diff.highlight")

```

The command to highlight diffs.

### prefix

```
prefix: list[str] | Unset = config_field('prefix')

```

The prefix for Yore comments.

### from_data

```
from_data(data: Mapping[str, Any]) -> Config

```

Load configuration from data.

Parameters:

- #### **`data`**

  (`Mapping[str, Any]`) – Data to load configuration from.

Returns:

- `Config` – Loaded configuration.

Source code in `src/yore/_internal/config.py`

```
@classmethod
def from_data(
    cls,
    data: An[Mapping[str, Any], Doc("Data to load configuration from.")],
) -> An[Config, Doc("Loaded configuration.")]:
    """Load configuration from data."""
    # Check for unknown configuration keys.
    field_keys = [field.default.key for field in fields(cls)]  # type: ignore[union-attr]
    unknown_keys = []
    for top_level_key, top_level_value in data.items():
        if isinstance(top_level_value, dict):
            for key in top_level_value.keys():  # noqa: SIM118
                final_key = f"{top_level_key}.{key}"
                if final_key not in field_keys:
                    unknown_keys.append(final_key)
        elif top_level_key not in field_keys:
            unknown_keys.append(top_level_key)
    if unknown_keys:
        _logger.warning(f"Unknown configuration keys: {', '.join(unknown_keys)}")

    # Create a configuration instance.
    return cls(
        **{
            field.name: cls._get(
                data,
                *field.default.key.split("."),  # type: ignore[union-attr]
                default=field.default,  # type: ignore[arg-type]
                transform=getattr(cls, field.default.transform or "", None),  # type: ignore[union-attr]
            )
            for field in fields(cls)
        },
    )

```

### from_default_locations

```
from_default_locations() -> Config

```

Load configuration from the default locations.

Returns:

- `Config` – Loaded configuration.

Source code in `src/yore/_internal/config.py`

```
@classmethod
def from_default_locations(cls) -> An[Config, Doc("Loaded configuration.")]:
    """Load configuration from the default locations."""
    paths = ("config/yore.toml", "yore.toml", "pyproject.toml")
    cwd = Path.cwd()
    while True:
        for path in paths:
            if (cwd / path).exists():
                if path == "pyproject.toml":
                    return cls.from_pyproject(cwd / path)
                return cls.from_file(cwd / path)
        if cwd == cwd.parent:
            break
        cwd = cwd.parent
    return cls()

```

### from_file

```
from_file(path: str | Path) -> Config

```

Load configuration from a file.

Parameters:

- #### **`path`**

  (`str | Path`) – Path to the configuration file.

Returns:

- `Config` – Loaded configuration.

Source code in `src/yore/_internal/config.py`

```
@classmethod
def from_file(
    cls,
    path: An[str | Path, Doc("Path to the configuration file.")],
) -> An[Config, Doc("Loaded configuration.")]:
    """Load configuration from a file."""
    with open(path, "rb") as file:
        return cls.from_data(tomllib.load(file))

```

### from_pyproject

```
from_pyproject(path: str | Path) -> Config

```

Load configuration from pyproject.toml.

Parameters:

- #### **`path`**

  (`str | Path`) – Path to the pyproject.toml file.

Returns:

- `Config` – Loaded configuration.

Source code in `src/yore/_internal/config.py`

```
@classmethod
def from_pyproject(
    cls,
    path: An[str | Path, Doc("Path to the pyproject.toml file.")],
) -> An[Config, Doc("Loaded configuration.")]:
    """Load configuration from pyproject.toml."""
    with open(path, "rb") as file:
        return cls.from_data(tomllib.load(file).get("tool", {}).get("yore", {}))

```

## Unset

```
Unset(key: str, transform: str | None = None)

```

A sentinel value for unset configuration options.

Parameters:

- ### **`key`**

  (`str`) – TOML key.

- ### **`transform`**

  (`str | None`, default: `None` ) – Name of the method to call to transform the config value.

Methods:

- **`__bool__`** – An unset value always evaluates to False.

Attributes:

- **`key`** (`str`) – TOML key.
- **`name`** (`str`) – Transformed key name.
- **`transform`** (`str | None`) – Name of the method to call to transform the config value.

Source code in `src/yore/_internal/config.py`

```
def __init__(
    self,
    key: An[str, Doc("TOML key.")],
    transform: An[str | None, Doc("Name of the method to call to transform the config value.")] = None,
) -> None:
    self.key: An[str, Doc("TOML key.")] = key
    self.name: An[str, Doc("Transformed key name.")] = key.replace("-", "_").replace(".", "_")
    self.transform: An[str | None, Doc("Name of the method to call to transform the config value.")] = transform

```

### key

```
key: str = key

```

TOML key.

### name

```
name: str = replace('.', '_')

```

Transformed key name.

### transform

```
transform: str | None = transform

```

Name of the method to call to transform the config value.

### __bool__

```
__bool__() -> bool

```

An unset value always evaluates to False.

Source code in `src/yore/_internal/config.py`

```
def __bool__(self) -> bool:
    """An unset value always evaluates to False."""
    return False

```

## YoreComment

```
YoreComment(
    file: Path,
    lineno: int,
    raw: str,
    prefix: str,
    suffix: str,
    kind: YoreKind,
    version: str,
    remove: Scope | None = None,
    replace: Scope | None = None,
    line: int | None = None,
    lines: list[int] | None = None,
    string: str | None = None,
    regex: bool = False,
    pattern1: str | None = None,
    pattern2: str | None = None,
    within: Scope | None = None,
)

```

A Yore comment.

Methods:

- **`check`** – Check the comment.
- **`fix`** – Fix the comment and code below it.

Attributes:

- **`bol`** (`date`) – The Beginning of Life date for the Python version.
- **`comment`** (`str`) – The comment without the prefix.
- **`eol`** (`date`) – The End of Life date for the Python version.
- **`file`** (`Path`) – The file containing comment.
- **`is_bol`** (`bool`) – Whether the comment is an End of Life comment.
- **`is_bump`** (`bool`) – Whether the comment is a bump comment.
- **`is_eol`** (`bool`) – Whether the comment is an End of Life comment.
- **`kind`** (`YoreKind`) – The kind of comment.
- **`line`** (`int | None`) – The line to replace.
- **`lineno`** (`int`) – The line number of the comment.
- **`lines`** (`list[int] | None`) – The lines to replace.
- **`pattern1`** (`str | None`) – The pattern to replace.
- **`pattern2`** (`str | None`) – The replacement pattern.
- **`prefix`** (`str`) – The prefix of the comment.
- **`raw`** (`str`) – The raw comment.
- **`regex`** (`bool`) – Whether to use regex for replacement.
- **`remove`** (`Scope | None`) – The removal scope.
- **`replace`** (`Scope | None`) – The replacement scope.
- **`string`** (`str | None`) – The string to replace.
- **`suffix`** (`str`) – The suffix of the comment.
- **`version`** (`str`) – The EOL/bump version.
- **`within`** (`Scope | None`) – The scope to replace within.

### bol

```
bol: date

```

The Beginning of Life date for the Python version.

### comment

```
comment: str

```

The comment without the prefix.

### eol

```
eol: date

```

The End of Life date for the Python version.

### file

```
file: Path

```

The file containing comment.

### is_bol

```
is_bol: bool

```

Whether the comment is an End of Life comment.

### is_bump

```
is_bump: bool

```

Whether the comment is a bump comment.

### is_eol

```
is_eol: bool

```

Whether the comment is an End of Life comment.

### kind

```
kind: YoreKind

```

The kind of comment.

### line

```
line: int | None = None

```

The line to replace.

### lineno

```
lineno: int

```

The line number of the comment.

### lines

```
lines: list[int] | None = None

```

The lines to replace.

### pattern1

```
pattern1: str | None = None

```

The pattern to replace.

### pattern2

```
pattern2: str | None = None

```

The replacement pattern.

### prefix

```
prefix: str

```

The prefix of the comment.

### raw

```
raw: str

```

The raw comment.

### regex

```
regex: bool = False

```

Whether to use regex for replacement.

### remove

```
remove: Scope | None = None

```

The removal scope.

### replace

```
replace: Scope | None = None

```

The replacement scope.

### string

```
string: str | None = None

```

The string to replace.

### suffix

```
suffix: str

```

The suffix of the comment.

### version

```
version: str

```

The EOL/bump version.

### within

```
within: Scope | None = None

```

The scope to replace within.

### check

```
check(
    *,
    bump: str | None = None,
    eol_within: timedelta | None = None,
    bol_within: timedelta | None = None,
) -> bool

```

Check the comment.

Parameters:

- #### **`bump`**

  (`str | None`, default: `None` ) – The next version of the project.

- #### **`eol_within`**

  (`timedelta | None`, default: `None` ) – The time delta to start warning before the End of Life of a Python version.

- #### **`bol_within`**

  (`timedelta | None`, default: `None` ) – The time delta to start warning before the Beginning of Life of a Python version.

Returns:

- `bool` – True when there is nothing to do, False otherwise.

Source code in `src/yore/_internal/lib.py`

```
def check(
    self,
    *,
    bump: str | None = None,
    eol_within: TimeDelta | None = None,
    bol_within: TimeDelta | None = None,
) -> bool:
    """Check the comment.

    Parameters:
        bump: The next version of the project.
        eol_within: The time delta to start warning before the End of Life of a Python version.
        bol_within: The time delta to start warning before the Beginning of Life of a Python version.

    Returns:
        True when there is nothing to do, False otherwise.
    """
    msg_location = f"{self.file}:{self.lineno}:"
    if self.is_eol:
        if eol_within and _within(eol_within, self.eol):
            delta = f"since {self.eol}" if _past(self.eol) else f"in ~{naturaldelta(_delta(self.eol))}"
            _logger.warning(f"{msg_location} {delta} {self.comment}")
        elif _within(TimeDelta(days=0), self.eol):
            _logger.error(f"{msg_location} since {self.eol} {self.comment}")
        else:
            return True
    elif self.is_bol:
        if bol_within and _within(bol_within, self.bol):
            delta = f"since {self.eol}" if _past(self.eol) else f"in ~{naturaldelta(_delta(self.eol))}"
            _logger.warning(f"{msg_location} {delta} {self.comment}")
        elif _within(TimeDelta(days=0), self.bol):
            _logger.error(f"{msg_location} since {self.bol} {self.comment}")
        else:
            return True
    elif self.is_bump and bump and Version(bump) >= Version(self.version):
        _logger.error(f"{msg_location} version {self.version} >= {self.comment}")
    else:
        return True
    return False

```

### fix

```
fix(
    buffer: list[str] | None = None,
    *,
    bump: str | None = None,
    eol_within: timedelta | None = None,
    bol_within: timedelta | None = None,
) -> bool

```

Fix the comment and code below it.

Parameters:

- #### **`buffer`**

  (`list[str] | None`, default: `None` ) – The buffer to fix. If not provided, read from and write to the file.

- #### **`bump`**

  (`str | None`, default: `None` ) – The next version of the project.

- #### **`eol_within`**

  (`timedelta | None`, default: `None` ) – The time delta to start fixing before the End of Life of a Python version.

- #### **`bol_within`**

  (`timedelta | None`, default: `None` ) – The time delta to start fixing before the Beginning of Life of a Python version.

Returns:

- `bool` – Whether the comment was fixed.

Source code in `src/yore/_internal/lib.py`

```
def fix(
    self,
    buffer: list[str] | None = None,
    *,
    bump: str | None = None,
    eol_within: TimeDelta | None = None,
    bol_within: TimeDelta | None = None,
) -> bool:
    """Fix the comment and code below it.

    Parameters:
        buffer: The buffer to fix. If not provided, read from and write to the file.
        bump: The next version of the project.
        eol_within: The time delta to start fixing before the End of Life of a Python version.
        bol_within: The time delta to start fixing before the Beginning of Life of a Python version.

    Returns:
        Whether the comment was fixed.
    """
    write = buffer is None
    buffer = buffer or self.file.read_text().splitlines(keepends=True)

    # Check if the fix should be applied.
    if (
        (self.is_eol and ((eol_within and _within(eol_within, self.eol)) or _within(TimeDelta(days=0), self.eol)))
        or (
            self.is_bol and ((bol_within and _within(bol_within, self.bol)) or _within(TimeDelta(days=0), self.bol))
        )
        or (self.is_bump and bump and Version(bump) >= Version(self.version))
    ):
        # Start at the commnent line, immediately remove it.
        start = self.lineno - 1
        del buffer[start]

        if self.remove:
            start, end = _scope_range(self.remove, buffer, start)
            del buffer[start:end]
            if write and self.remove == "file":
                self.file.unlink()

        elif self.replace:
            # Line numbers/ranges are relative to block starts, absolute for the "file" scope.
            start, end = _scope_range(self.replace, buffer, start)
            if self.line:
                replacement = [buffer[start + self.line - 1]]
            elif self.lines:
                replacement = [buffer[start + line] for line in self.lines]
            elif self.string:
                replacement = [self.string + "\n"]
            else:
                raise RuntimeError("No replacement specified")
            replacement = _reindent(replacement, _indent(buffer[start]))
            buffer[start:end] = replacement

        elif self.within:
            # Line numbers/ranges are relative to block starts, absolute for the "file" scope.
            start, end = _scope_range(self.within, buffer, start)
            block = buffer[start:end]
            if self.regex:
                pattern1: Pattern = re.compile(self.pattern1)
                replacement = [pattern1.sub(self.pattern2, line) for line in block]
            else:
                replacement = [line.replace(self.pattern1, self.pattern2) for line in block]  # type: ignore[arg-type]
            replacement = _reindent(replacement, _indent(buffer[start]))
            buffer[start:end] = replacement

        if write and buffer:
            self.file.write_text("".join(buffer))

        return True
    return False

```

## config_field

```
config_field(
    key: str, transform: str | None = None
) -> Unset

```

Create a dataclass field with a TOML key.

Parameters:

- ### **`key`**

  (`str`) – Key within the config file.

- ### **`transform`**

  (`str | None`, default: `None` ) – Name of transformation method to apply.

Returns:

- `Unset` – Configuration field.

Source code in `src/yore/_internal/config.py`

```
def config_field(
    key: An[str, Doc("Key within the config file.")],
    transform: An[str | None, Doc("Name of transformation method to apply.")] = None,
) -> An[Unset, Doc("Configuration field.")]:
    """Create a dataclass field with a TOML key."""
    return dataclass_field(default=Unset(key, transform=transform))

```

## get_pattern

```
get_pattern(prefix: str = DEFAULT_PREFIX) -> Pattern

```

Get the Yore comment pattern with a specific prefix.

Parameters:

- ### **`prefix`**

  (`str`, default: `DEFAULT_PREFIX` ) – The prefix to use in the pattern.

Returns:

- `Pattern` – The Yore comment pattern.

Source code in `src/yore/_internal/lib.py`

```
@cache
def get_pattern(prefix: str = DEFAULT_PREFIX) -> Pattern:
    """Get the Yore comment pattern with a specific prefix.

    Parameters:
        prefix: The prefix to use in the pattern.

    Returns:
        The Yore comment pattern.
    """
    return re.compile(
        _PATTERN_PREFIX.replace("PREFIX", prefix) + COMMENT_PATTERN + _PATTERN_SUFFIX,
        re.VERBOSE | re.IGNORECASE,
    )

```

## main

```
main(args: list[str] | None = None) -> int

```

Run the main program.

This function is executed when you type `yore` or `python -m yore`.

Parameters:

- ### **`args`**

  (`list[str] | None`, default: `None` ) – Arguments passed from the command line.

Returns:

- `int` – An exit code.

Source code in `src/yore/_internal/cli.py`

```
def main(
    args: An[list[str] | None, Doc("Arguments passed from the command line.")] = None,
) -> An[int, Doc("An exit code.")]:
    """Run the main program.

    This function is executed when you type `yore` or `python -m yore`.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    output = cappa.Output(error_format=f"[bold]{_NAME}[/]: [bold red]error[/]: {{message}}")
    completion_option: cappa.Arg = cappa.Arg(
        long=True,
        action=cappa.ArgAction.completion,
        choices=["complete", "generate"],
        help="Print shell-specific completion source.",
    )
    help_option: cappa.Arg = cappa.Arg(
        short="-h",
        long=True,
        action=cappa.ArgAction.help,
        help="Print the program help and exit.",
    )
    help_formatter = cappa.HelpFormatter(default_format="Default: {default}.")

    try:
        return cappa.invoke(
            CommandMain,
            argv=args,
            output=output,
            help=help_option,
            completion=completion_option,
            help_formatter=help_formatter,
        )
    except cappa.Exit as exit:
        return int(1 if exit.code is None else exit.code)

```

## yield_buffer_comments

```
yield_buffer_comments(
    file: Path,
    lines: list[str],
    *,
    prefix: str = DEFAULT_PREFIX,
) -> Iterator[YoreComment]

```

Yield all Yore comments in a buffer.

Parameters:

- ### **`file`**

  (`Path`) – The file to check.

- ### **`lines`**

  (`list[str]`) – The buffer to check (pre-read lines).

- ### **`prefix`**

  (`str`, default: `DEFAULT_PREFIX` ) – The prefix to look for in the comments.

Yields:

- `YoreComment` – Yore comments.

Source code in `src/yore/_internal/lib.py`

```
def yield_buffer_comments(file: Path, lines: list[str], *, prefix: str = DEFAULT_PREFIX) -> Iterator[YoreComment]:
    """Yield all Yore comments in a buffer.

    Parameters:
        file: The file to check.
        lines: The buffer to check (pre-read lines).
        prefix: The prefix to look for in the comments.

    Yields:
        Yore comments.
    """
    prepattern = _get_prematching_pattern(prefix)
    pattern = get_pattern(prefix)
    for lineno, line in enumerate(lines, 1):
        if prepattern.match(line):
            if match := pattern.match(line):
                yield _match_to_comment(match, file, lineno)
            else:
                _logger.error(f"{file}:{lineno}: invalid Yore comment")

```

## yield_directory_comments

```
yield_directory_comments(
    directory: Path, *, prefix: str = DEFAULT_PREFIX
) -> Iterator[YoreComment]

```

Yield all Yore comments in a directory.

Parameters:

- ### **`directory`**

  (`Path`) – The directory to check.

- ### **`prefix`**

  (`str`, default: `DEFAULT_PREFIX` ) – The prefix to look for in the comments.

Yields:

- `YoreComment` – Yore comments.

Source code in `src/yore/_internal/lib.py`

```
def yield_directory_comments(directory: Path, *, prefix: str = DEFAULT_PREFIX) -> Iterator[YoreComment]:
    """Yield all Yore comments in a directory.

    Parameters:
        directory: The directory to check.
        prefix: The prefix to look for in the comments.

    Yields:
        Yore comments.
    """
    for file in yield_files(directory):
        yield from yield_file_comments(file, prefix=prefix)

```

## yield_file_comments

```
yield_file_comments(
    file: Path, *, prefix: str = DEFAULT_PREFIX
) -> Iterator[YoreComment]

```

Yield all Yore comments in a file.

Parameters:

- ### **`file`**

  (`Path`) – The file to check.

- ### **`prefix`**

  (`str`, default: `DEFAULT_PREFIX` ) – The prefix to look for in the comments.

Yields:

- `YoreComment` – Yore comments.

Source code in `src/yore/_internal/lib.py`

```
def yield_file_comments(file: Path, *, prefix: str = DEFAULT_PREFIX) -> Iterator[YoreComment]:
    """Yield all Yore comments in a file.

    Parameters:
        file: The file to check.
        prefix: The prefix to look for in the comments.

    Yields:
        Yore comments.
    """
    try:
        lines = file.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return
    yield from yield_buffer_comments(file, lines, prefix=prefix)

```

## yield_files

```
yield_files(
    directory: Path, exclude: list[str] | None = None
) -> Iterator[Path]

```

Yield all files in a directory.

Source code in `src/yore/_internal/lib.py`

```
def yield_files(directory: Path, exclude: list[str] | None = None) -> Iterator[Path]:
    """Yield all files in a directory."""
    exclude = DEFAULT_EXCLUDE if exclude is None else exclude
    _logger.debug(f"{directory}: scanning...")
    try:
        git_files = subprocess.run(
            ["git", "ls-files", "-z"],  # noqa: S607
            capture_output=True,
            cwd=directory,
            text=True,
            check=False,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        for path in directory.iterdir():
            if path.is_file():
                yield path
            elif path.is_dir() and not any(path.match(pattern) for pattern in exclude):
                yield from yield_files(path, exclude=exclude)
    else:
        for filepath in git_files.strip("\0").split("\0"):
            yield directory / filepath

```

## yield_path_comments

```
yield_path_comments(
    path: Path, *, prefix: str = DEFAULT_PREFIX
) -> Iterator[YoreComment]

```

Yield all Yore comments in a file or directory.

Parameters:

- ### **`path`**

  (`Path`) – The file or directory to check.

- ### **`prefix`**

  (`str`, default: `DEFAULT_PREFIX` ) – The prefix to look for in the comments.

Yields:

- `YoreComment` – Yore comments.

Source code in `src/yore/_internal/lib.py`

```
def yield_path_comments(path: Path, *, prefix: str = DEFAULT_PREFIX) -> Iterator[YoreComment]:
    """Yield all Yore comments in a file or directory.

    Parameters:
        path: The file or directory to check.
        prefix: The prefix to look for in the comments.

    Yields:
        Yore comments.
    """
    if path.is_dir():
        yield from yield_directory_comments(path, prefix=prefix)
    else:
        yield from yield_file_comments(path, prefix=prefix)

```
