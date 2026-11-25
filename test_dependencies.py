import ast

from python_code_visualizer import (
    extract_dependencies,
    module_exists,
)


def test_dependencies():
    code = """
import os
import math
import made_up_module
from sys import path
from fake.mod import x
"""

    imports = extract_dependencies(
        ast.parse(code)
    )

    assert imports == [
        "fake.mod",
        "made_up_module",
        "math",
        "os",
        "sys",
    ]

    assert module_exists("os")
    assert module_exists("math")
    assert module_exists("sys")

    assert not module_exists(
        "made_up_module"
    )

    assert not module_exists(
        "fake.mod"
    )

    print(
        "--- Testing Dependencies ---"
    )

    print(
        "PASS: imports found:",
        imports,
    )

    print(
        "PASS: missing modules detected"
    )


def test_relative_import():
    imports = extract_dependencies(
        ast.parse(
            "from .helpers import thing"
        )
    )

    assert imports == [
        ".helpers"
    ]

    assert module_exists(
        ".helpers"
    )

    print(
        "PASS: relative imports "
        "handled without crashing"
    )


if __name__ == "__main__":
    test_dependencies()
    test_relative_import()