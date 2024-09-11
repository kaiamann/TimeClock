"""Provides a module that allows keeping track of working hours.

Provides a CLI with the following commands:
# TODO: list them here.
"""

def all_subclasses(cls: type):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])