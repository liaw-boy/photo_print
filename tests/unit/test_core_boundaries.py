import ast
from pathlib import Path

CORE_DIR = Path(__file__).parent.parent.parent / "src" / "photo_border" / "core"
FORBIDDEN_MODULES = {"streamlit", "typer", "argparse", "click"}


def _imported_top_level_modules(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(), filename=str(py_file))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


class TestCoreHasNoUiDependency:
    def test_no_core_file_imports_forbidden_ui_modules(self):
        offenders = {}
        for py_file in CORE_DIR.glob("*.py"):
            found = _imported_top_level_modules(py_file) & FORBIDDEN_MODULES
            if found:
                offenders[py_file.name] = found

        assert not offenders, f"core/ 模組不應依賴 UI/CLI 框架: {offenders}"
