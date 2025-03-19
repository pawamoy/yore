from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, fields
from dataclasses import field as dataclass_field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from typing import Annotated as An

from typing_extensions import Doc

# DUE: EOL 3.10: Replace block with line 2.
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


_logger = logging.getLogger(__name__)


class Unset:
    """A sentinel value for unset configuration options."""

    def __init__(
        self,
        key: An[str, Doc("TOML key.")],
        transform: An[str | None, Doc("Name of the method to call to transform the config value.")] = None,
    ) -> None:
        self.key: An[str, Doc("TOML key.")] = key
        self.name: An[str, Doc("Transformed key name.")] = key.replace("-", "_").replace(".", "_")
        self.transform: An[str | None, Doc("Name of the method to call to transform the config value.")] = transform

    def __bool__(self) -> bool:
        """An unset value always evaluates to False."""
        return False

    def __repr__(self) -> str:
        return f"<Unset({self.name!r})>"

    def __str__(self) -> str:
        # The string representation is used in the CLI, to show the default values.
        return f"`{self.key}` config-value"


def config_field(
    key: An[str, Doc("Key within the config file.")],
    transform: An[str | None, Doc("Name of transformation method to apply.")] = None,
) -> An[Unset, Doc("Configuration field.")]:
    """Create a dataclass field with a TOML key."""
    return dataclass_field(default=Unset(key, transform=transform))


# DUE: EOL 3.9: Remove block.
_dataclass_opts: dict[str, bool] = {}
if sys.version_info >= (3, 10):
    _dataclass_opts["kw_only"] = True


# DUE: EOL 3.9: Replace `**_dataclass_opts` with `kw_only=True` within line.
@dataclass(**_dataclass_opts)
class Config:
    """Configuration for the insiders project."""

    prefix: An[list[str] | Unset, Doc("The prefix for Yore comments.")] = config_field("prefix")  # noqa: RUF009
    diff_highlight: An[str | Unset, Doc("The command to highlight diffs.")] = config_field("diff.highlight")  # noqa: RUF009

    @classmethod
    def _get(
        cls,
        data: An[Mapping[str, Any], Doc("Data to get value from.")],
        *keys: An[str, Doc("Keys to access nested dictionary.")],
        default: An[Unset, Doc("Default value if key is not found.")],
        transform: An[Callable[[Any], Any] | None, Doc("Transformation function to apply to the value.")] = None,
    ) -> An[Any, Doc("Value from the nested dictionary.")]:
        """Get a value from a nested dictionary."""
        for key in keys:
            if key not in data:
                return default
            data = data[key]
        if transform:
            return transform(data)
        return data

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

    @classmethod
    def from_file(
        cls,
        path: An[str | Path, Doc("Path to the configuration file.")],
    ) -> An[Config, Doc("Loaded configuration.")]:
        """Load configuration from a file."""
        with open(path, "rb") as file:
            return cls.from_data(tomllib.load(file))

    @classmethod
    def from_pyproject(
        cls,
        path: An[str | Path, Doc("Path to the pyproject.toml file.")],
    ) -> An[Config, Doc("Loaded configuration.")]:
        """Load configuration from pyproject.toml."""
        with open(path, "rb") as file:
            return cls.from_data(tomllib.load(file).get("tool", {}).get("yore", {}))

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
