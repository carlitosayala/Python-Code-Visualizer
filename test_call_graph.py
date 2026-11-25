import tkinter as tk

from python_code_visualizer import UMLCanvasApp


def test_call_graph_valid():
    root = tk.Tk()
    root.withdraw()

    app = UMLCanvasApp(root)
    app.file_path = "valid_call_test.py"

    app.generate_call_graph()

    output = app.output.get("1.0", tk.END)

    expected_results = [
        "<module> -> a()",
        "<module> -> c()",
        "a() -> no calls",
        "b() -> a()",
        "c() -> b()"
    ]

    print("\n--- Testing Call Graph ---")

    for expected in expected_results:
        assert expected in output
        print(f"✔ Found: {expected}")

    root.destroy()


def test_call_graph_syntax_error():
    root = tk.Tk()
    root.withdraw()

    app = UMLCanvasApp(root)
    app.file_path = "syntax_error_test.py"

    result = app.parse_safely()

    assert result is None
    print("✔ Syntax error detected correctly.")

    root.destroy()


test_call_graph_valid()
test_call_graph_syntax_error()