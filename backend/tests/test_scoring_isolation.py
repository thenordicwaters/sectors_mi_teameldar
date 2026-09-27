import ast
from pathlib import Path

FORBIDDEN_MODULES = {"httpx", "requests", "fastapi", "sqlite3"}


def test_methods_do_not_import_io_or_adapters() -> None:
    methods_root = (
        Path(__file__).resolve().parents[1] / "app" / "services" / "scoring" / "methods"
    )
    method_files = sorted(methods_root.glob("*.py"))
    assert method_files
    for path in method_files:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    _assert_allowed(path, alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                _assert_allowed(path, module)
                for alias in node.names:
                    _assert_allowed(path, alias.name)


def _assert_allowed(path: Path, name: str) -> None:
    parts = [part for part in name.split(".") if part]
    if not parts:
        return
    assert parts[0] not in FORBIDDEN_MODULES, f"{path.name} imports {name}"
    assert "adapters" not in parts, f"{path.name} imports adapters via {name}"
