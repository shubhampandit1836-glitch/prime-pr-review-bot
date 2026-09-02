from app.diff_parser import parse_diff

SIMPLE_DIFF = """\
diff --git a/hello.py b/hello.py
index e69de29..a1b2c3d 100644
--- a/hello.py
+++ b/hello.py
@@ -1,3 +1,4 @@
 def greet():
-    print("hi")
+    print("hello")
+    print("world")
     return None
"""

MULTI_FILE_DIFF = """\
diff --git a/a.py b/a.py
index 111..222 100644
--- a/a.py
+++ b/a.py
@@ -1,2 +1,3 @@
 def a():
+    pass
     return 1
diff --git a/b.py b/b.py
index 333..444 100644
--- a/b.py
+++ b/b.py
@@ -1,2 +1,3 @@
 def b():
+    pass
     return 2
"""

DELETE_ONLY_DIFF = """\
diff --git a/c.py b/c.py
index 555..666 100644
--- a/c.py
+++ b/c.py
@@ -1,3 +1,2 @@
 def c():
-    unused = True
     return 3
"""


def test_parses_single_hunk():
    hunks = parse_diff(SIMPLE_DIFF)
    assert len(hunks) == 1
    assert hunks[0].file_path == "hello.py"
    assert "    print(\"hello\")" in hunks[0].added_lines
    assert "    print(\"world\")" in hunks[0].added_lines


def test_parses_multiple_files():
    hunks = parse_diff(MULTI_FILE_DIFF)
    file_paths = {h.file_path for h in hunks}
    assert file_paths == {"a.py", "b.py"}
    assert len(hunks) == 2


def test_skips_hunk_with_no_additions():
    hunks = parse_diff(DELETE_ONLY_DIFF)
    assert hunks == []


def test_empty_diff_returns_empty_list():
    assert parse_diff("") == []


def test_line_numbers_reflect_new_file():
    hunks = parse_diff(SIMPLE_DIFF)
    # target_start=1, target_length=4 → end_line = 1 + 4 - 1 = 4
    assert hunks[0].start_line == 1
    assert hunks[0].end_line == 4