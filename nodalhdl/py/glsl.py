# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

"""
    glsl-like vec behavioral.
    assisted by ChatGPT.
"""
class vec:
    _swizzle_map = {
        'x': 0, 'y': 1, 'z': 2, 'w': 3,
        'r': 0, 'g': 1, 'b': 2, 'a': 3
    }

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

    # swizzle getter
    def __getattr__(self, attr):
        if all(c in self._swizzle_map for c in attr):
            indices = [self._swizzle_map[c] for c in attr]
            if any(i >= len(self) for i in indices):
                raise AttributeError(f"Swizzle '{attr}' out of bounds for Vec{len(self)}")
            values = [self[i] for i in indices]
            if len(values) == 1:
                return values[0]
            return _vec_factory(*values)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")

    # swizzle setter
    def __setattr__(self, attr, value):
        if attr.startswith("_"):
            super().__setattr__(attr, value)
            return
        if all(c in self._swizzle_map for c in attr):
            indices = [self._swizzle_map[c] for c in attr]
            if any(i >= len(self) for i in indices):
                raise AttributeError(f"Swizzle '{attr}' out of bounds for Vec{len(self)}")
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

    # arithmetic operations
    def _op(self, other, func):
        if isinstance(other, vec):
            if len(self) != len(other):
                raise ValueError("Vector length mismatch")
            return _vec_factory(*(func(a, b) for a, b in zip(self, other)))
        else:
            return _vec_factory(*(func(a, other) for a in self))

    def _rop(self, other, func):
        return _vec_factory(*(func(other, a) for a in self))

    def __add__(self, other): return self._op(other, lambda a, b: a + b)
    def __sub__(self, other): return self._op(other, lambda a, b: a - b)
    def __mul__(self, other): return self._op(other, lambda a, b: a * b)
    def __truediv__(self, other): return self._op(other, lambda a, b: a / b)

    def __radd__(self, other): return self._rop(other, lambda a, b: a + b)
    def __rsub__(self, other): return self._rop(other, lambda a, b: a - b)
    def __rmul__(self, other): return self._rop(other, lambda a, b: a * b)
    def __rtruediv__(self, other): return self._rop(other, lambda a, b: a / b)

def _vec_factory(*args):
    l = len(args)
    if l == 2: return vec2(*args)
    if l == 3: return vec3(*args)
    if l == 4: return vec4(*args)
    raise ValueError(f"No vec type for {l} components")

class vec2(vec):
    def __init__(self, x = 0, y = 0):
        super().__init__(x, y)

class vec3(vec):
    def __init__(self, x = 0, y = 0, z = 0):
        super().__init__(x, y, z)

class vec4(vec):
    def __init__(self, x = 0, y = 0, z = 0, w = 0):
        super().__init__(x, y, z, w)


if __name__ == "__main__":
    v2 = vec2(1, 2)
    print(v2.x)          # 1
    print(v2.yx)         # Vec2(2, 1)

    v3 = vec3(1, 2, 3)
    print(v3.zxy)        # Vec3(3, 1, 2)
    v3.yz = [9, 8]
    print(v3)            # Vec3(1, 9, 8)

    v4 = vec4(1, 2, 3, 4)
    print(v4.rgb)        # Vec3(1, 2, 3)
    v4.rgba = [10, 20, 30, 40]
    print(v4)            # Vec4(10, 20, 30, 40)

    print(v4 + 1)        # Vec4(11, 21, 31, 41)
    print(2 * v2)        # Vec2(2, 4)
    print((v3 + vec3(1, 1, 1)).xyz)  # Vec3(2, 10, 9)


"""
    functions.
"""
from nodalhdl.core.signal import *
from nodalhdl.basic.bits import *
from nodalhdl.py.core import *
from nodalhdl.py.core import _constant

import math

from typing import Union


def fract(x):
    if isinstance(x, ComputeElement):
        _s = x.s
        
        if x.type.base_belong(FixedPoint):
            u = _s.add_substructure(f"fract", CustomVHDLOperator(
                {"i": x.type},
                {"o": x.type},
                f"o <= (o'high downto {x.type.W_frac} => '0'){f" & i({x.type.W_frac - 1} downto 0)" if x.type.W_frac > 0 else ""};",
                _unique_name = f"Fract_{x.type}"
            ))
            _s.connect(x.node, u.IO.i)
            return ComputeElement(_s, runtime_node = u.IO.o)
        else:
            raise NotImplementedError
    elif isinstance(x, vec):
        return type(x)(*(fract(a) for a in x))
    elif isinstance(x, (float, int)):
        return x - math.floor(x)
    else:
        raise NotImplementedError


def ceil(x): # TODO to be checked
    if isinstance(x, ComputeElement):
        _s = x.s
        
        if x.type.base_belong(FixedPoint):
            if x.type.W_frac > 0:
                u = _s.add_substructure(f"ceil", CustomVHDLOperator(
                    {"i": x.type},
                    {"o": x.type},
                    f"o({x.type.W_frac - 1} downto 0) <= (others => '0');\n" +
                        f"plus_one <= std_logic_vector(unsigned(i) + to_unsigned({1 << x.type.W_frac}, {x.type.W}));" +
                        f"o(o'high downto {x.type.W_frac}) <= i(i'high downto {x.type.W_frac}) when i({x.type.W_frac - 1} downto 0) = ({x.type.W_frac - 1} downto 0 => '0') else plus_one(o'high downto {x.type.W_frac});",
                    f"signal plus_one: std_logic_vector({x.type.W} - 1 downto 0);",
                    _unique_name = f"Ceil_{x.type}"
                ))
                _s.connect(x.node, u.IO.i)
                return ComputeElement(_s, runtime_node = u.IO.o)
            else:
                return x # integer
        else:
            raise NotImplementedError
    elif isinstance(x, vec):
        return type(x)(*(ceil(a) for a in x))
    elif isinstance(x, (float, int)):
        return math.ceil(x)
    else:
        raise NotImplementedError


def _minmax(x, y, mode = "min"):
    if isinstance(x, ComputeElement) and isinstance(y, ComputeElement):
        assert x.s == y.s and x.type.equal(y.type) # should be equivalent
        _s = x.s
        target_t = x.type
        
        if target_t.base_belong(SFixedPoint): # signed
            vhdl_type = "signed"
        elif target_t.base_belong(Bits): # unsigned
            vhdl_type = "unsigned"
        else:
            raise NotImplementedError
        
        u = _s.add_substructure(f"{mode}", CustomVHDLOperator(
            {"a": target_t, "b": target_t},
            {"o": target_t},
            f"o <= a when {vhdl_type}(a) {"<" if mode == "min" else ">"} {vhdl_type}(b) else b;",
            _unique_name = f"M{mode[1:]}_{target_t}"
        ))
        _s.connect(x.node, u.IO.a)
        _s.connect(y.node, u.IO.b)
        return ComputeElement(_s, runtime_node = u.IO.o)
    elif isinstance(x, ComputeElement) and isinstance(y, (float, int)):
        y_ce = _constant(x.s, x.type(y))
        return _minmax(x, y_ce, mode)
    elif isinstance(y, ComputeElement) and isinstance(x, (float, int)):
        return _minmax(y, x, mode)
    elif isinstance(x, vec) and isinstance(y, vec):
        if len(x) == len(y):
            return type(x)(*(_minmax(a, b, mode) for a, b in zip(x, y)))
        else:
            raise Exception("vecs should have the same length")
    elif isinstance(x, vec) and isinstance(y, (float, int)):
        return type(x)(*(_minmax(a, y, mode) for a in x))
    elif isinstance(y, vec) and isinstance(x, (float, int)):
        return _minmax(y, x, mode)
    else:
        return (x if x < y else y) if mode == "min" else (x if x > y else y)

def min(x, y): return _minmax(x, y, mode = "min")
def max(x, y): return _minmax(x, y, mode = "max")


def clamp(x, lower_bound: Union[float, int], upper_bound: Union[float, int]):
    return min(max(x, lower_bound), upper_bound)

