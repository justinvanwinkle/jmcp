def hello(name):
    """Say hello."""
    print(f"Hello {name}")


class Greeter:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hi {self.name}"


def use_greeter():
    g = Greeter("World")
    print(g.greet())
