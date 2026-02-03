from jmcp.tools import code_navigation


def test_goto_definition_greeter():
    # usage: g = Greeter("World") in use_greeter
    # use_greeter is at bottom of file.
    # Greeter usage is inside use_greeter function.

    # We need exact line/col.
    # Let's read the file to find line.
    from pathlib import Path

    module_path = Path("tests/src/fake_lib/module.py")
    lines = module_path.read_text().splitlines()

    usage_line = -1
    for i, line in enumerate(lines):
        if 'g = Greeter("World")' in line:
            usage_line = i + 1
            break

    assert usage_line != -1

    # Col of Greeter
    #    g = Greeter("World")
    # 012345678
    # G starts at 8 (4 spaces indent + g = ) = 4 + 4 = 8?
    # No, 4 spaces. "    g = Greeter"
    # 012345678
    # G is at index 8.

    import time

    start_time = time.time()
    result = "No definition found."
    found = False
    while time.time() - start_time < 5:
        # Try a range of columns around the identifier to be safe
        for offset in range(0, 5):
            result = code_navigation.execute(str(module_path), usage_line, 8 + offset)
            if "class Greeter:" in result:
                found = True
                break
        if found:
            break
        time.sleep(0.1)

    # Expect definition of Greeter
    # class Greeter:
    assert found, f"Failed to find definition. Last result: {result}"
    assert "class Greeter:" in result
    assert "tests/src/fake_lib/module.py" in result
