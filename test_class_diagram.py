import ast

def extract_classes(tree):
    classes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            name = node.name
            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
            attrs = [a.targets[0].id for a in node.body
                     if isinstance(a, ast.Assign) and isinstance(a.targets[0], ast.Name)]
            classes[name] = {"bases": bases, "methods": methods, "attrs": attrs}
    return classes

def test_classes_valid():
    code = """
class A:
    x = 1
    def f(self): pass

class B(A):
    y = 2
    def g(self): pass
"""
    with open("class_test_valid.py", "w") as f:
        f.write(code)

    tree = ast.parse(open("class_test_valid.py").read())
    result = extract_classes(tree)
    print("\n✔ Valid Class Parsing:")
    for c, data in result.items():
        print(f"{c}: {data}")

def test_classes_none():
    with open("class_test_none.py", "w") as f:
        f.write("a = 10\nb = 20\n")

    tree = ast.parse(open("class_test_none.py").read())
    result = extract_classes(tree)
    print("\n✔ No Class Case:", result)

print("\n--- Testing Class Diagram ---")
test_classes_valid()
test_classes_none()
