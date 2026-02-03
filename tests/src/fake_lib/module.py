from .deep.nested import deep_func


def hello(name):
    """Say hello."""


class Greeter:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hi {self.name}"


def use_greeter():
    g = Greeter("World")
    g.greet()
    deep_func()
