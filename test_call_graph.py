import ast

def safe_parse(path):
    try:
        with open(path, "r") as f:
            return ast.parse(f.read())
    except SyntaxError:
        print("✔ Syntax error detected correctly.")
        return None

def test_call_graph_valid():
    code = """
def a(): pass
def b(): a()
def c(): b()
a(); c()
"""
    with open("valid_call_test.py", "w") as f:
        f.write(code)

    tree = safe_parse("valid_call_test.py")
    if tree:
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)

        print("Call Graph:", sorted(set(calls)))

def test_call_graph_syntax_error():
    code = "def broken(:\n    pass"
    with open("syntax_error_test.py", "w") as f:
        f.write(code)

    safe_parse("syntax_error_test.py")

print("\n--- Testing Call Graph ---")
test_call_graph_valid()
test_call_graph_syntax_error()
