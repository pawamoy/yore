# Usage

Yore lets you write `# YORE` comments in your code base to mark some lines of blocks of code as being legacy code: only there to support "old" versions of Python, or for backward compatibility with previous versions of your own project.

## Syntax

The syntax is as follows:

```python
# YORE: <eol|bol|bump> <VERSION>: remove <file|block|line>.
# YORE: <eol|bol|bump> <VERSION>: replace <file|block|line> with line <LINENO>.
# YORE: <eol|bol|bump> <VERSION>: replace <file|block|line> with lines <LINE-RANGE1[, LINE-RANGE2...]>.
# YORE: <eol|bol|bump> <VERSION>: replace <file|block|line> with `<STRING>`.
# YORE: <eol|bol|bump> <VERSION>: [regex-]replace `<PATTERN1>` with `<PATTERN2>` within <file|block|line>.
```

Terms between `<` and `>` *must* be provided, while terms between `[` and `]` are optional. Uppercase terms are placeholders that you should replace with actual values, while lowercase terms are keywords that you should use literally. Everything except placeholders is case-insensitive.

Terms `eol`, `bol` and `bump` mean "End of Life", "Beginning of Life" and "version bump", respectively.

Line number and line ranges are relative to the start of blocks for the "block" scope, but absolute for the "file" scope. 

## Examples

All the following examples are real-life examples extracted from another project ([Griffe](https://mkdocstrings.github.io/griffe/)).

*Remove the module-level `__getattr__` function when we bump the project to version 1.0.0.*

```python
# YORE: Bump 1.0.0: Remove block.
def __getattr__(name: str) -> Any:
    if name == "load_git":
        warnings.warn(
            f"Importing {name} from griffe.git is deprecated. Import it from griffe.loader instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        from griffe.loader import load_git

        return load_git
    raise AttributeError
```

*Simplify `ast.unparse` import when Python 3.8 reaches its End of Life.*

```python
# YORE: EOL 3.8: Replace block with line 4.
if sys.version_info < (3, 9):
    from astunparse import unparse
else:
    from ast import unparse
```

*Replace `lstrip` by `removeprefix` when Python 3.8 reaches its End of Life.*

```python
# YORE: EOL 3.8: Replace `lstrip` with `removeprefix` within line.
return [cpn.lstrip("_") for cpn in a.split(".")] == [cpn.lstrip("_") for cpn in b.split(".")]
```

*Simplify union of accepted types when we bump the project to version 1.0.0.*

```python
def load_extensions(
    # YORE: Bump 1.0.0: Replace ` | Sequence[LoadableExtension],` with `` within line.
    *exts: LoadableExtension | Sequence[LoadableExtension],
): ...
```

*Remove parameter from a signature when we bump the project to version 1.0.0.*

```python
def load(
    ...
    # YORE: Bump 1.0.0: Remove line.
    module: str | Path | None = None,
    ...
):
    ...
```

*Replace line with something else when we bump the project to version 1.0.0.*

```python
# YORE: Bump 1.0.0: Replace line with `return self.public`.
return _True if self.public else _False
```

## Blocks

A block is a list of consecutive non-blank or over-indented lines.

```python
# YORE: This is a block.
print("hello")
print("world")

# YORE: This is another block.
print("goodbye")
```

Here we see that the blank line marked the end of the first block. But if the lines following a blank lines are over-indented, they will still count as being part of the block:

```python
def function():    
    # YORE: This is a block.
    print("hello")
    if some_condition:
        do_this()

        # Blank line above, but next lines are over-indented
        # compared to the first line of the block `print("hello")`.
        do_that()
```

If the indentation goes back to the initial level, but there is no blank line right before it, the block continues:

```python
def function():
    # YORE: This is a block.
    print("hello")
    if some_condition:
        do_this()

        do_that()
    if something_else:  # This is still part of the block!
        and_do_this()
```

If you don't want the `something_else` condition and code to be part of the block, separate it with a blank line:

```python
def function():
    # YORE: This is a block.
    print("hello")
    if some_condition:
        do_this()

        do_that()

    if something_else:  # This is not part of the first block anymore.
        and_do_this()
```

A line that is less indented that the initial line will also terminate a block.

```python
if something:
    # YORE: Start of a block. Initial indent = 4.
    print("hello")
if something_else:  # Indent = 0, not part of the block above.
    print("goodbye")
```

## Commands

### `yore check`

Once you have written a few Yore-comments in your code base, you can check them with the `yore check` command. If a comment is outdated, for example the current version of the project is equal to or higher than a "bump" comment, Yore will warn you. Similarly, if a Python version has reached its end of life, and Yore finds an "eol" comment for this version, it will warn you. If you want to be warned before the EOL (End of Life) date of a Python version, use the `-E`, `--eol-within` option. If you want to be warned before the BOL (Beginning of Life) date of a Python version, use the `-B`, `--bol-within` option. To specify the upcoming project version, use the `-b`, `--bump` option.

```console
% yore check --warn-before-eol '5 months' --bump 1.0
./src/griffe/encoders.py:91: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/dataclasses.py:155: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/dataclasses.py:530: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/dataclasses.py:540: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/dataclasses.py:553: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/mixins.py:412: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/mixins.py:418: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/mixins.py:425: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/mixins.py:433: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/mixins.py:437: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/tests.py:320: Python 3.8 will reach its End of Life within approx. 4 months
./src/griffe/expressions.py:1169: Python 3.8 will reach its End of Life within approx. 4 months
./src/griffe/agents/nodes/_runtime.py:24: Python 3.8 will reach its End of Life within approx. 4 months
./src/griffe/agents/nodes/_values.py:11: Python 3.8 will reach its End of Life within approx. 4 months
./src/griffe/git.py:19: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/extensions/base.py:464: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/extensions/base.py:477: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/extensions/base.py:491: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/loader.py:97: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/loader.py:130: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/loader.py:163: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/loader.py:742: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/loader.py:811: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/loader.py:835: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/loader.py:888: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
./src/griffe/loader.py:905: Code is scheduled for update/removal in 1.0.0 which is older than or equal to 1
```

By default Yore will search and scan Python modules in the current working directory (excluding cache folders, virtualenvs, etc.), but you can specify multiple paths on the command line:

```bash
yore check src scripts/this_module.py docs/*.py
# same thing for yore fix
```

### `yore fix`

Once you are ready, you can apply transformations to your code base with the `yore fix` command. It will apply what the comments instruct and remove or replace line or blocks of code, but only when a Python version has reached its End of Life date or when the provided upcoming project version is equal to or higher than the one specified in the comments. All comments that would not emit warnings will be left untouched.

```console
% yore fix -f5m -b1
fixed 1 comment in ./src/griffe/encoders.py
fixed 4 comments in ./src/griffe/dataclasses.py
fixed 5 comments in ./src/griffe/mixins.py
fixed 1 comment in ./src/griffe/tests.py
fixed 1 comment in ./src/griffe/expressions.py
fixed 1 comment in ./src/griffe/agents/nodes/_runtime.py
fixed 1 comment in ./src/griffe/agents/nodes/_values.py
fixed 1 comment in ./src/griffe/git.py
fixed 3 comments in ./src/griffe/extensions/base.py
fixed 8 comments in ./src/griffe/loader.py
```

Here is output of `git diff` after running `yore fix` on the code base:

```diff
diff --git a/src/griffe/agents/nodes/_runtime.py b/src/griffe/agents/nodes/_runtime.py
index 5e3e01c6..1671fdc2 100644
--- a/src/griffe/agents/nodes/_runtime.py
+++ b/src/griffe/agents/nodes/_runtime.py
@@ -21,8 +21,7 @@ _cyclic_relationships = {
 
 
 def _same_components(a: str, b: str, /) -> bool:
-    # YORE: EOL 3.8: Replace `lstrip` with `removeprefix` within line.
-    return [cpn.lstrip("_") for cpn in a.split(".")] == [cpn.lstrip("_") for cpn in b.split(".")]
+    return [cpn.removeprefix("_") for cpn in a.split(".")] == [cpn.removeprefix("_") for cpn in b.split(".")]
 
 
 class ObjectNode:
diff --git a/src/griffe/agents/nodes/_values.py b/src/griffe/agents/nodes/_values.py
index 59bfacac..2f6eaa88 100644
--- a/src/griffe/agents/nodes/_values.py
+++ b/src/griffe/agents/nodes/_values.py
@@ -8,11 +8,7 @@ from typing import TYPE_CHECKING
 
 from griffe.logger import get_logger
 
-# YORE: EOL 3.8: Replace block with line 4.
-if sys.version_info < (3, 9):
-    from astunparse import unparse
-else:
-    from ast import unparse
+from ast import unparse
 
 if TYPE_CHECKING:
     from pathlib import Path
diff --git a/src/griffe/dataclasses.py b/src/griffe/dataclasses.py
index 22ddf24e..cfdc7926 100644
--- a/src/griffe/dataclasses.py
+++ b/src/griffe/dataclasses.py
@@ -152,9 +152,6 @@ class Docstring:
         Returns:
             A dictionary.
         """
-        # YORE: Bump 1.0.0: Remove block.
-        if docstring_parser is not None:
-            warnings.warn("Parameter `docstring_parser` is deprecated and has no effect.", stacklevel=1)
 
         base: dict[str, Any] = {
             "value": self.value,
@@ -527,8 +524,7 @@ class Object(ObjectAliasMixin):
         """Whether this object is a namespace subpackage."""
         return False
 
-    # YORE: Bump 1.0.0: Replace ` | set[str]` with `` within line.
-    def has_labels(self, *labels: str | set[str]) -> bool:
+    def has_labels(self, *labels: str) -> bool:
         """Tell if this object has all the given labels.
 
         Parameters:
@@ -537,21 +533,8 @@ class Object(ObjectAliasMixin):
         Returns:
             True or False.
         """
-        # YORE: Bump 1.0.0: Remove block.
-        all_labels = set()
-        for label in labels:
-            if isinstance(label, str):
-                all_labels.add(label)
-            else:
-                warnings.warn(
-                    "Passing a set of labels to `has_labels` is deprecated. Pass multiple strings instead.",
-                    DeprecationWarning,
-                    stacklevel=2,
-                )
-                all_labels.update(label)
 
-        # YORE: Bump 1.0.0: Replace `all_labels` with `set(labels)` within line.
-        return all_labels.issubset(self.labels)
+        return set(labels).issubset(self.labels)
 
     def filter_members(self, *predicates: Callable[[Object | Alias], bool]) -> dict[str, Object | Alias]:
         """Filter and return members based on predicates.
diff --git a/src/griffe/encoders.py b/src/griffe/encoders.py
index e99fc1d4..3deea7db 100644
--- a/src/griffe/encoders.py
+++ b/src/griffe/encoders.py
@@ -88,13 +88,6 @@ class JSONEncoder(json.JSONEncoder):
         super().__init__(*args, **kwargs)
         self.full: bool = full
 
-        # YORE: Bump 1.0.0: Remove block.
-        self.docstring_parser: Parser | None = docstring_parser
-        self.docstring_options: dict[str, Any] = docstring_options or {}
-        if docstring_parser is not None:
-            warnings.warn("Parameter `docstring_parser` is deprecated and has no effect.", stacklevel=1)
-        if docstring_options is not None:
-            warnings.warn("Parameter `docstring_options` is deprecated and has no effect.", stacklevel=1)
 
     def default(self, obj: Any) -> Any:
         """Return a serializable representation of the given object.
diff --git a/src/griffe/expressions.py b/src/griffe/expressions.py
index c03d0a96..d9d6ebfd 100644
--- a/src/griffe/expressions.py
+++ b/src/griffe/expressions.py
@@ -1166,17 +1166,6 @@ _node_map: dict[type, Callable[[Any, Module | Class], Expr]] = {
     ast.YieldFrom: _build_yield_from,
 }
 
-# YORE: EOL 3.8: Remove block.
-if sys.version_info < (3, 9):
-
-    def _build_extslice(node: ast.ExtSlice, parent: Module | Class, **kwargs: Any) -> Expr:
-        return ExprExtSlice([_build(dim, parent, **kwargs) for dim in node.dims])
-
-    def _build_index(node: ast.Index, parent: Module | Class, **kwargs: Any) -> Expr:
-        return _build(node.value, parent, **kwargs)
-
-    _node_map[ast.ExtSlice] = _build_extslice
-    _node_map[ast.Index] = _build_index
 
 
 def _build(node: ast.AST, parent: Module | Class, **kwargs: Any) -> Expr:
diff --git a/src/griffe/extensions/base.py b/src/griffe/extensions/base.py
index c6b1cf79..e3fc801e 100644
--- a/src/griffe/extensions/base.py
+++ b/src/griffe/extensions/base.py
@@ -461,8 +461,7 @@ LoadableExtension = Union[str, Dict[str, Any], ExtensionType, Type[ExtensionType
 
 
 def load_extensions(
-    # YORE: Bump 1.0.0: Replace ` | Sequence[LoadableExtension],` with `` within line.
-    *exts: LoadableExtension | Sequence[LoadableExtension],
+    *exts: LoadableExtension
 ) -> Extensions:
     """Load configured extensions.
 
@@ -474,22 +473,8 @@ def load_extensions(
     """
     extensions = Extensions()
 
-    # YORE: Bump 1.0.0: Remove block.
-    all_exts: list[LoadableExtension] = []
-    for ext in exts:
-        if isinstance(ext, (list, tuple)):
-            warnings.warn(
-                "Passing multiple extensions as a single list or tuple is deprecated. "
-                "Please pass them as separate arguments instead.",
-                DeprecationWarning,
-                stacklevel=2,
-            )
-            all_exts.extend(ext)
-        else:
-            all_exts.append(ext)  # type: ignore[arg-type]
 
-    # YORE: Bump 1.0.0: Replace `all_exts` with `exts` within line.
-    for extension in all_exts:
+    for extension in exts:
         ext = _load_extension(extension)
         if isinstance(ext, list):
             extensions.add(*ext)
diff --git a/src/griffe/git.py b/src/griffe/git.py
index d91fcb7f..77bd09c5 100644
--- a/src/griffe/git.py
+++ b/src/griffe/git.py
@@ -16,19 +16,6 @@ from griffe.exceptions import GitError
 WORKTREE_PREFIX = "griffe-worktree-"
 
 
-# YORE: Bump 1.0.0: Remove block.
-def __getattr__(name: str) -> Any:
-    if name == "load_git":
-        warnings.warn(
-            f"Importing {name} from griffe.git is deprecated. Import it from griffe.loader instead.",
-            DeprecationWarning,
-            stacklevel=2,
-        )
-
-        from griffe.loader import load_git
-
-        return load_git
-    raise AttributeError
 
 
 def assert_git_repo(path: str | Path) -> None:
diff --git a/src/griffe/loader.py b/src/griffe/loader.py
index 52cd5523..c908ee0b 100644
--- a/src/griffe/loader.py
+++ b/src/griffe/loader.py
@@ -94,30 +94,6 @@ class GriffeLoader:
             "time_spent_inspecting": 0,
         }
 
-    # YORE: Bump 1.0.0: Remove block.
-    def load_module(
-        self,
-        module: str | Path,
-        *,
-        submodules: bool = True,
-        try_relative_path: bool = True,
-        find_stubs_package: bool = False,
-    ) -> Object:
-        """Renamed `load`. Load an object as a Griffe object, given its dotted path.
-
-        This method was renamed [`load`][griffe.loader.GriffeLoader.load].
-        """
-        warnings.warn(
-            "The `load_module` method was renamed `load`, and is deprecated.",
-            DeprecationWarning,
-            stacklevel=2,
-        )
-        return self.load(  # type: ignore[return-value]
-            module,
-            submodules=submodules,
-            try_relative_path=try_relative_path,
-            find_stubs_package=find_stubs_package,
-        )
 
     def load(
         self,
@@ -127,8 +103,6 @@ class GriffeLoader:
         submodules: bool = True,
         try_relative_path: bool = True,
         find_stubs_package: bool = False,
-        # YORE: Bump 1.0.0: Remove line.
-        module: str | Path | None = None,
     ) -> Object | Alias:
         """Load an object as a Griffe object, given its Python or file path.
 
@@ -160,16 +134,6 @@ class GriffeLoader:
         Returns:
             A Griffe object.
         """
-        # YORE: Bump 1.0.0: Remove block.
-        if objspec is None and module is None:
-            raise TypeError("load() missing 1 required positional argument: 'objspec'")
-        if objspec is None:
-            objspec = module
-            warnings.warn(
-                "Parameter 'module' was renamed 'objspec' and made positional-only.",
-                DeprecationWarning,
-                stacklevel=2,
-            )
 
         obj_path: str
         package = None
@@ -739,8 +703,6 @@ def load(
     force_inspection: bool = False,
     store_source: bool = True,
     find_stubs_package: bool = False,
-    # YORE: Bump 1.0.0: Remove line.
-    module: str | Path | None = None,
     resolve_aliases: bool = False,
     resolve_external: bool | None = None,
     resolve_implicit: bool = False,
@@ -808,8 +770,6 @@ def load(
         submodules=submodules,
         try_relative_path=try_relative_path,
         find_stubs_package=find_stubs_package,
-        # YORE: Bump 1.0.0: Remove line.
-        module=module,
     )
     if resolve_aliases:
         loader.resolve_aliases(implicit=resolve_implicit, external=resolve_external)
@@ -832,8 +792,6 @@ def load_git(
     allow_inspection: bool = True,
     force_inspection: bool = False,
     find_stubs_package: bool = False,
-    # YORE: Bump 1.0.0: Remove line.
-    module: str | Path | None = None,
     resolve_aliases: bool = False,
     resolve_external: bool | None = None,
     resolve_implicit: bool = False,
@@ -885,9 +843,6 @@ def load_git(
         if isinstance(objspec, Path):
             objspec = worktree / objspec
 
-        # YORE: Bump 1.0.0: Remove block.
-        if isinstance(module, Path):
-            module = worktree / module
 
         return load(
             objspec,
@@ -902,8 +857,6 @@ def load_git(
             allow_inspection=allow_inspection,
             force_inspection=force_inspection,
             find_stubs_package=find_stubs_package,
-            # YORE: Bump 1.0.0: Remove line.
-            module=module,
             resolve_aliases=resolve_aliases,
             resolve_external=resolve_external,
             resolve_implicit=resolve_implicit,
diff --git a/src/griffe/mixins.py b/src/griffe/mixins.py
index 91006b5d..c030dabc 100644
--- a/src/griffe/mixins.py
+++ b/src/griffe/mixins.py
@@ -409,33 +409,28 @@ class ObjectAliasMixin(GetMembersMixin, SetMembersMixin, DelMembersMixin, Serial
         """
         # Give priority to the `public` attribute if it is set.
         if self.public is not None:  # type: ignore[attr-defined]
-            # YORE: Bump 1.0.0: Replace line with `return self.public`.
-            return _True if self.public else _False  # type: ignore[return-value,attr-defined]
+            return self.public
 
         # If the object is defined at the module-level and is listed in `__all__`, it is public.
         # If the parent module defines `__all__` but does not list the object, it is private.
         if self.parent and self.parent.is_module and bool(self.parent.exports):  # type: ignore[attr-defined]
-            # YORE: Bump 1.0.0: Replace line with `return self.name in self.parent.exports`.
-            return _True if self.name in self.parent.exports else _False  # type: ignore[attr-defined,return-value]
+            return self.name in self.parent.exports
 
         # Special objects are always considered public.
         # Even if we don't access them directly, they are used through different *public* means
         # like instantiating classes (`__init__`), using operators (`__eq__`), etc..
         if self.is_private:
-            # YORE: Bump 1.0.0: Replace line with `return False`.
-            return _False  # type: ignore[return-value]
+            return False
 
         # TODO: In a future version, we will support two conventions regarding imports:
         # - `from a import x as x` marks `x` as public.
         # - `from a import *` marks all wildcard imported objects as public.
         # The following condition effectively filters out imported objects.
         if self.is_alias and not (self.inherited or (self.parent and self.parent.is_alias)):  # type: ignore[attr-defined]
-            # YORE: Bump 1.0.0: Replace line with `return False`.
-            return _False  # type: ignore[return-value]
+            return False
 
         # If we reached this point, the object is public.
-        # YORE: Bump 1.0.0: Replace line with `return True`.
-        return _True  # type: ignore[return-value]
+        return True
 
     @property
     def is_deprecated(self) -> bool:
diff --git a/src/griffe/tests.py b/src/griffe/tests.py
index 75d07975..e0b2effc 100644
--- a/src/griffe/tests.py
+++ b/src/griffe/tests.py
@@ -317,11 +317,7 @@ def module_vtree(path: str, *, leaf_package: bool = True, return_leaf: bool = Fa
     parts = path.split(".")
     modules = [Module(name, filepath=Path(*parts[:index], "__init__.py")) for index, name in enumerate(parts)]
     if not leaf_package:
-        # YORE: EOL 3.8: Replace block with line 2.
-        try:
-            filepath = modules[-1].filepath.with_stem(parts[-1])  # type: ignore[union-attr]
-        except AttributeError:
-            filepath = modules[-1].filepath.with_name(f"{parts[-1]}.py")  # type: ignore[union-attr]
+        filepath = modules[-1].filepath.with_stem(parts[-1])  # type: ignore[union-attr]
 
         modules[-1]._filepath = filepath
     return vtree(*modules, return_leaf=return_leaf)  # type: ignore[return-value]
```

We recommend you run a formatting pass on the code after `yore fix`, for example using [Ruff](https://astral.sh/ruff) or [Black](https://github.com/psf/black).

## Limitations

There is no way yet to remove a line from a multiline docstring.
