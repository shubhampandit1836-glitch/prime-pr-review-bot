from app.diff_parser import ChangedHunk
from app.ast_context import get_hunk_context

SAMPLE_FILE = '''\
def standalone_function():
    x = 1
    y = 2
    return x + y


class Calculator:
    def add(self, a, b):
        result = a + b
        return result

    def subtract(self, a, b):
        result = a - b
        return result
'''


def test_finds_enclosing_standalone_function():
    hunk = ChangedHunk(file_path="sample.py", start_line=3, end_line=3, added_lines=["    y = 2"])
    context = get_hunk_context(hunk, SAMPLE_FILE)

    assert context.enclosing_node_type == "function_definition"
    assert context.enclosing_code is not None
    assert "def standalone_function():" in context.enclosing_code
    assert "return x + y" in context.enclosing_code
    assert "class Calculator" not in context.enclosing_code


def test_finds_innermost_method_not_outer_class():
    hunk = ChangedHunk(file_path="sample.py", start_line=9, end_line=9, added_lines=["        result = a + b"])
    context = get_hunk_context(hunk, SAMPLE_FILE)

    assert context.enclosing_node_type == "function_definition"
    assert context.enclosing_code is not None
    assert "def add(self, a, b):" in context.enclosing_code
    assert "def subtract" not in context.enclosing_code


def test_finds_different_method_in_same_class():
    hunk = ChangedHunk(file_path="sample.py", start_line=13, end_line=13, added_lines=["        result = a - b"])
    context = get_hunk_context(hunk, SAMPLE_FILE)

    assert context.enclosing_code is not None
    assert "def subtract(self, a, b):" in context.enclosing_code
    assert "def add" not in context.enclosing_code


def test_unsupported_file_extension_returns_none():
    hunk = ChangedHunk(file_path="config.yaml", start_line=1, end_line=1, added_lines=["key: value"])
    context = get_hunk_context(hunk, "key: value\n")

    assert context.enclosing_code is None
    assert context.enclosing_node_type is None


def test_line_outside_any_function_returns_none():
    # A hunk at a line with no enclosing function/class (e.g. module-level
    # import or blank line between definitions) should return None, not
    # crash or return the wrong node.
    module_level_code = "import os\n\ndef foo():\n    pass\n"
    hunk = ChangedHunk(file_path="sample.py", start_line=1, end_line=1, added_lines=["import os"])
    context = get_hunk_context(hunk, module_level_code)

    assert context.enclosing_code is None