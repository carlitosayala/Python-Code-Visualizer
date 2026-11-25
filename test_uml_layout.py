from python_code_visualizer import UMLCanvasApp


def test_horizontal_connection():
    child = (
        350,
        50,
        240,
        160,
    )

    parent = (
        50,
        50,
        240,
        160,
    )

    points = (
        UMLCanvasApp._connection_points(
            child,
            parent,
        )
    )

    assert points == (
        350,
        130.0,
        290,
        130.0,
    )

    print(
        "--- Testing UML Connections ---"
    )

    print(
        "PASS: horizontal inheritance "
        "connection points toward parent"
    )


def test_vertical_connection():
    child = (
        50,
        300,
        240,
        160,
    )

    parent = (
        50,
        50,
        240,
        160,
    )

    points = (
        UMLCanvasApp._connection_points(
            child,
            parent,
        )
    )

    assert points == (
        170.0,
        300,
        170.0,
        210,
    )

    print(
        "PASS: vertical inheritance "
        "connection points toward parent"
    )


if __name__ == "__main__":
    test_horizontal_connection()
    test_vertical_connection()