import ast

from python_code_visualizer import build_call_graph


def test_call_graph_valid():
    code = """
def a():
    pass

def b():
    a()

def c():
    b()

a()
c()
"""

    graph = build_call_graph(
        ast.parse(code)
    )

    calls = graph["calls"]

    assert calls["<module>"] == {
        "a",
        "c",
    }

    assert calls["a"] == set()

    assert calls["b"] == {
        "a"
    }

    assert calls["c"] == {
        "b"
    }

    print("--- Testing Call Graph ---")
    print("PASS: <module> -> a(), c()")
    print("PASS: a() -> no calls")
    print("PASS: b() -> a()")
    print("PASS: c() -> b()")


def test_method_call_graph():
    code = """
class Worker:
    def start(self):
        self.finish()

    def finish(self):
        print("done")
"""

    graph = build_call_graph(
        ast.parse(code)
    )

    calls = graph["calls"]

    assert calls["Worker.start"] == {
        "self.finish"
    }

    assert calls["Worker.finish"] == {
        "print"
    }

    print(
        "PASS: class methods are "
        "qualified by class name"
    )


def test_syntax_error():
    try:
        ast.parse(
            "def broken(:\n"
            "    pass"
        )

        raise AssertionError(
            "Expected SyntaxError"
        )

    except SyntaxError:
        print(
            "PASS: syntax error "
            "detected correctly"
        )


if __name__ == "__main__":
    test_call_graph_valid()
    test_method_call_graph()
    test_syntax_error()