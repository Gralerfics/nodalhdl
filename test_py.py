from nodalhdl.py.core import Engine

from typing import List


def add(x, y):
    return x + y    


if __name__ == "__main__":
    engine = Engine()
    
    s_add = engine.combinational_to_structure(add)
    
    pass

