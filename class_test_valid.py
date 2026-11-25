class A:
    x = 1

    def __init__(self):
        self.name = "A"
        self.value = 10

    def f(self):
        pass


class B(A):
    y = 2

    def __init__(self):
        self.description = "B"

    def g(self):
        self.description += "!"