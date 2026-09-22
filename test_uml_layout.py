# Simulated class dictionary like the real app uses

classes = {
    "A": {"bases": [], "methods": ["f"], "attrs": ["x"]},
    "B": {"bases": ["A"], "methods": ["g"], "attrs": ["y"]},
    "C": {"bases": [], "methods": [], "attrs": []},
}

def layout(classes):
    positions = {}
    x = 50
    y = 50
    for cname in classes:
        w, h = 220, 140
        positions[cname] = (x, y, w, h)
        x += 300
        if x > 1500:
            x = 50
            y += 220
    return positions

print("\n--- Testing UML Layout ---")
pos = layout(classes)
for cname, p in pos.items():
    print(f"{cname}: {p}")
