"""
    glsl-like vec behavioral.
    assisted by ChatGPT.
"""

class vec:
    def __init__(self, *args):
        self._data = list(args)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, i):
        return self._data[i]

    def __setitem__(self, i, val):
        self._data[i] = val

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        cls = type(self).__name__
        return f"{cls}({', '.join(map(str, self._data))})"

    def _op(self, other, func):
        if isinstance(other, vec):
            if len(self) != len(other):
                raise ValueError("vector lengths do not match")
            return type(self)(*(func(a, b) for a, b in zip(self, other)))
        else:
            return type(self)(*(func(a, other) for a in self))

    def _rop(self, other, func):
        return type(self)(*(func(other, a) for a in self))

    def __add__(self, other): return self._op(other, lambda a, b: a + b)
    def __sub__(self, other): return self._op(other, lambda a, b: a - b)
    def __mul__(self, other): return self._op(other, lambda a, b: a * b)
    def __truediv__(self, other): return self._op(other, lambda a, b: a / b)

    def __radd__(self, other): return self._rop(other, lambda a, b: a + b)
    def __rsub__(self, other): return self._rop(other, lambda a, b: a - b)
    def __rmul__(self, other): return self._rop(other, lambda a, b: a * b)
    def __rtruediv__(self, other): return self._rop(other, lambda a, b: a / b)


class vec2(vec):
    def __init__(self, x = 0, y = 0):
        super().__init__(x, y)


class vec3(vec):
    def __init__(self, x = 0, y = 0, z = 0):
        super().__init__(x, y, z)


class vec4(vec):
    _index_map = {
        'x': 0, 'y': 1, 'z': 2, 'w': 3,
        'r': 0, 'g': 1, 'b': 2, 'a': 3
    }

    def __init__(self, x = 0, y = 0, z = 0, w = 0):
        super().__init__(x, y, z, w)

    def __getattr__(self, attr):
        if all(c in self._index_map for c in attr):
            indices = [self._index_map[c] for c in attr]
            components = [self[i] for i in indices]
            if len(components) == 1:
                return components[0]
            elif len(components) == 2:
                return vec2(*components)
            elif len(components) == 3:
                return vec3(*components)
            elif len(components) == 4:
                return vec4(*components)
        raise AttributeError(f"vec4 object has no attribute '{attr}'")

    def __setattr__(self, attr, value):
        if attr == "_data":
            super().__setattr__(attr, value)
            return
        if all(c in self._index_map for c in attr):
            indices = [self._index_map[c] for c in attr]
            if isinstance(value, vec):
                value = list(value)
            if isinstance(value, (list, tuple)):
                if len(value) != len(indices):
                    raise ValueError(f"Expected {len(indices)} values, got {len(value)}")
                for i, v in zip(indices, value):
                    self[i] = v
            elif len(indices) == 1:
                self[indices[0]] = value
            else:
                raise ValueError(f"Cannot assign single value to multiple components: {attr}")
        else:
            super().__setattr__(attr, value)


if __name__ == "__main__":
    v = vec4(1, 2, 3, 4)

    print(v.x)         # 1
    print(v.rgba)      # vec4(1, 2, 3, 4)
    print(v.xy)        # vec2(1, 2)
    print(v.rgb + 1)   # vec3(2, 3, 4)
    print(v.rgb * 2)   # vec3(2, 4, 6)

    v.xy = vec2(10, 20)
    print(v)           # vec4(10, 20, 3, 4)

    v.rgb = vec3(7, 8, 9)
    print(v)           # vec4(7, 8, 9, 4)

    u = vec4(1, 2, 3, 4)
    w = v + u
    print(w)           # vec4(8, 10, 12, 8)

    print((1 + v).xyz) # vec3(8, 9, 10)


"""
    functions.
"""
import math

from nodalhdl.py.core import *


def fract(x):
    if isinstance(x, ComputeElement):
        raise NotImplementedError
    elif isinstance(x, vec):
        return type(x)(*(fract(a) for a in x))
    elif isinstance(x, (float, int)):
        return x - math.floor(x)
    else:
        raise NotImplementedError


def min(x, y):
    if isinstance(x, ComputeElement) and isinstance(y, ComputeElement):
        raise NotImplementedError
    elif isinstance(x, ComputeElement) and isinstance(y, (float, int)):
        raise NotImplementedError
    elif isinstance(y, ComputeElement) and isinstance(x, (float, int)):
        return min(y, x)
    elif isinstance(x, vec) and isinstance(y, vec):
        if len(x) == len(y):
            return type(x)(*(min(a, b) for a, b in zip(x, y)))
        else:
            raise Exception("vecs should have the same length")
    else:
        return x if x < y else y

