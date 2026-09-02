from dataclasses import dataclass

from tree_sitter_languages import get_parser

from app.diff_parser import ChangedHunk

# File extension → tree-sitter language name. Extend this as more
# languages are needed — deliberately starting with just Python since
# that's what this project's own test fixtures use; adding a language
# is one line here plus tree_sitter_languages already has the grammar.
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
}

# Node types that count as "enclosing context" per language. Different
# languages name these differently in their grammars (e.g. Python has
# function_definition, JS has function_declaration) — kept as a dict so
# adding a language later doesn't require touching the walking logic.
CONTAINER_NODE_TYPES = {
    "python": {"function_definition", "class_definition"},
}


@dataclass
class HunkContext:
    """
    A changed hunk, enriched with the source of its enclosing function
    or class. 'enclosing_code' is None when a hunk isn't inside any
    function/class (e.g. a change at module level, or an unsupported
    file type) — callers must handle that case explicitly rather than
    the AST layer silently guessing.
    """
    hunk: ChangedHunk
    enclosing_code: str | None
    enclosing_node_type: str | None


def _get_language_for_file(file_path: str) -> str | None:
    for ext, language in EXTENSION_TO_LANGUAGE.items():
        if file_path.endswith(ext):
            return language
    return None


def _find_enclosing_node(node, target_line: int, container_types: set[str]):
    """
    Walk the syntax tree looking for the innermost function/class node
    whose line range contains target_line. Recurses into children first
    so that a nested function inside a class returns the function, not
    the outer class — the tightest-matching context is the most useful
    one for a reviewer or LLM to see.
    """
    best_match = None

    if node.type in container_types:
        start = node.start_point[0] + 1  # tree-sitter rows are 0-indexed
        end = node.end_point[0] + 1
        if start <= target_line <= end:
            best_match = node

    for child in node.children:
        child_match = _find_enclosing_node(child, target_line, container_types)
        if child_match is not None:
            best_match = child_match  # prefer the deepest/innermost match

    return best_match


def get_hunk_context(hunk: ChangedHunk, full_file_content: str) -> HunkContext:
    """
    Given a changed hunk and the FULL current content of the file it
    belongs to (not just the diff), find and return the enclosing
    function/class source. The caller is responsible for fetching the
    full file content — this function only does the AST parsing and
    walking, keeping it independently testable without any GitHub API
    dependency.
    """
    language = _get_language_for_file(hunk.file_path)

    if language is None:
        return HunkContext(hunk=hunk, enclosing_code=None, enclosing_node_type=None)

    parser = get_parser(language)
    tree = parser.parse(full_file_content.encode("utf-8"))

    # Use the middle line of the hunk as the anchor point — for a
    # multi-line hunk, this is more robust than the first line, which
    # can sometimes land exactly on a function's own signature line
    # and produce an off-by-one edge case at the boundary.
    anchor_line = (hunk.start_line + hunk.end_line) // 2

    container_types = CONTAINER_NODE_TYPES.get(language, set())
    enclosing_node = _find_enclosing_node(tree.root_node, anchor_line, container_types)

    if enclosing_node is None:
        return HunkContext(hunk=hunk, enclosing_code=None, enclosing_node_type=None)

    enclosing_code = full_file_content.encode("utf-8")[
        enclosing_node.start_byte:enclosing_node.end_byte
    ].decode("utf-8")

    return HunkContext(
        hunk=hunk,
        enclosing_code=enclosing_code,
        enclosing_node_type=enclosing_node.type,
    )