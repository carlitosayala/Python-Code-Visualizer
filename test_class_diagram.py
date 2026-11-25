import ast

from python_code_visualizer import extract_classes


def test_classes_valid():
    code = """
class A:
    x = 1

    def __init__(self):
        self.name = "A"
        self.value: int = 10

    def f(self):
        pass


class B(A):
    y = 2

    def __init__(self):
        self.description = "B"

    def g(self):
        self.description += "!"
"""

    result = extract_classes(
        ast.parse(code)
    )

    assert result["A"]["bases"] == []

    assert result["A"]["methods"] == [
        "__init__",
        "f",
    ]

    assert result["A"]["attrs"] == [
        "name",
        "value",
        "x",
    ]

    assert result["B"]["bases"] == [
        "A"
    ]

    assert result["B"]["methods"] == [
        "__init__",
        "g",
    ]

    assert result["B"]["attrs"] == [
        "description",
        "y",
    ]

    print("--- Testing Class Diagram ---")

    print(
        "PASS: inheritance detected"
    )

    print(
        "PASS: methods detected"
    )

    print(
        "PASS: class attributes detected"
    )

    print(
        "PASS: self.* instance "
        "attributes detected"
    )


def test_classes_none():
    result = extract_classes(
        ast.parse(
            "a = 10\n"
            "b = 20\n"
        )
    )

    assert result == {}

    print(
        "PASS: no-class case "
        "handled correctly"
    )


if __name__ == "__main__":
    test_classes_valid()
    test_classes_none()