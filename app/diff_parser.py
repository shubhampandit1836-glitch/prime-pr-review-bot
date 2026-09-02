from dataclasses import dataclass

from unidiff import PatchSet


@dataclass
class ChangedHunk:
    """
    One contiguous block of changes in one file. 'start_line' and
    'end_line' are the line numbers in the NEW version of the file
    (after the change) — this is what we need later to map a hunk back
    onto the file's AST and find which function/class it falls inside.
    """
    file_path: str
    start_line: int
    end_line: int
    added_lines: list[str]


def parse_diff(diff_text: str) -> list[ChangedHunk]:
    """
    Parse a unified diff into a flat list of changed hunks across all
    files. Deliberately skips deleted files entirely (nothing to review
    in code that no longer exists) and binary files (no meaningful diff
    to parse) — both would otherwise cause confusing downstream errors
    in the AST step.
    """
    patch_set = PatchSet(diff_text)
    hunks: list[ChangedHunk] = []

    for patched_file in patch_set:
        if patched_file.is_removed_file or patched_file.is_binary_file:
            continue

        file_path = patched_file.path

        for hunk in patched_file:
            added_lines = [line.value.rstrip("\n") for line in hunk if line.is_added]

            if not added_lines:
                # A hunk with only deletions (no additions) has nothing
                # new to review — skip it rather than passing empty
                # content down the pipeline.
                continue

            hunks.append(
                ChangedHunk(
                    file_path=file_path,
                    start_line=hunk.target_start,
                    end_line=hunk.target_start + hunk.target_length - 1,
                    added_lines=added_lines,
                )
            )

    return hunks