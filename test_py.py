from nodalhdl.core.signal import Bundle
from nodalhdl.py.core import Engine

from typing import List


# Vec2 = Bundle[{"x": }]


def shader(x, y):
    return x + y


if __name__ == "__main__":
    engine = Engine()
    
    s = engine.combinational_to_structure(shader)
    
    pass

