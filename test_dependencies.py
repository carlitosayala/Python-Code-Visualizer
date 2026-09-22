import ast

def module_exists(name):
    try:
        __import__(name)
        return True
    except:
        return False

def test_dependencies():
    code = """
import os
import math
import made_up_module
from sys import path
from fake.mod import x
"""
    with open("dep_test.py", "w") as f:
        f.write(code)

    tree = ast.parse(open("dep_test.py").read())

    imports = []
    unresolved = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
                if not module_exists(alias.name):
                    unresolved.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
            if not module_exists(node.module):
                unresolved.append(node.module)

    print("\n✔ Module Imports Found:", imports)
    print("✔ Unresolved Imports:", unresolved)

print("\n--- Testing Dependencies ---")
test_dependencies()
