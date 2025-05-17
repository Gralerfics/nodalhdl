from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.basic.bits import *
from nodalhdl.basic.arith import *

from nodalhdl.core.hdl import emit_to_files


def info(s: Structure, show_hdl = None):
    rid = RuntimeId.create()
    s.deduction(rid)
    print(s.runtime_info(rid))

    model = s.generation(rid)
    if show_hdl:
        vhdl = model.emit_vhdl()
        if show_hdl == "emit":
            emit_to_files(vhdl, "C:/Workspace/test_project/test_project.srcs/sources_1/new")
        else:
            print(vhdl.get(show_hdl, vhdl.keys()))

def here(f):
    print(f"<<<<<<<<<<<<<<<<<<<< {f.__name__} >>>>>>>>>>>>>>>>>>>>")
    s = Structure()
    r = f(s)
    if r is not None and not isinstance(r, str):
        r = "hdl_root_u.vhd"
    info(s, show_hdl = r if r else None)


@here
def Test_BitsAdd_BitsSubtract(s: Structure):
    a = s.add_port("a", Input[Bits[4]])
    b = s.add_port("b", Input[Auto])
    c = s.add_port("c", Output[Bits[6]])

    u = s.add_substructure("u", BitsAdd(Auto))
    # u = s.add_substructure("u", BitsSubtract(Auto))

    s.connect(a, u.IO.a)
    s.connect(b, u.IO.b)
    s.connect(u.IO.r, c)


@here
def Test_BitsInverse(s: Structure):
    a = s.add_port("a", Input[Bits[6]])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", BitsInverse(Auto))

    s.connect(a, u.IO.a)
    s.connect(u.IO.r, c)


@here
def Test_BitsEqualTo(s: Structure):
    a = s.add_port("a", Input[Bits[4]])
    b = s.add_port("b", Input[Auto])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", BitsEqualTo(Auto))

    s.connect(a, u.IO.a)
    s.connect(b, u.IO.b)
    s.connect(u.IO.r, c)


@here
def Test_BitsLessThan(s: Structure):
    a = s.add_port("a", Input[Bits[6]])
    b = s.add_port("b", Input[Auto])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", BitsLessThan(Auto))

    s.connect(a, u.IO.a)
    s.connect(b, u.IO.b)
    s.connect(u.IO.r, c)


@here
def Test_BitsNot(s: Structure):
    a = s.add_port("a", Input[Bits[6]])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", BitsNot(Auto))

    s.connect(a, u.IO.a)
    s.connect(u.IO.r, c)


@here
def Test_BitsAnd_BitsOr(s: Structure):
    a = s.add_port("a", Input[Bits[6]])
    b = s.add_port("b", Input[Auto])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", BitsAnd(Auto))
    # u = s.add_substructure("u", BitsOr(Auto))

    s.connect(a, u.IO.a)
    s.connect(b, u.IO.b)
    s.connect(u.IO.r, c)


@here
def Test_BitsReductionAnd_BitsReductionOr(s: Structure):
    a = s.add_port("a", Input[Bits[6]])
    c = s.add_port("c", Output[Auto])

    # u = s.add_substructure("u", BitsReductionAnd(Auto))
    u = s.add_substructure("u", BitsReductionOr(Auto))

    s.connect(a, u.IO.a)
    s.connect(u.IO.r, c)


@here
def Test_BinaryMultiplexer(s: Structure):
    a = s.add_port("a", Input[Auto])
    b = s.add_port("b", Input[Auto])
    sel = s.add_port("sel", Input[Bit])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", BinaryMultiplexer(UInt[12]))

    s.connect(a, u.IO.i0)
    s.connect(b, u.IO.i1)
    s.connect(sel, u.IO.sel)
    s.connect(c, u.IO.o)
    
    # return "hdl_BinaryMultiplexer_UInt_12.vhd"


@here
def Test_CustomVHDLOperator(s: Structure):
    a = s.add_port("a", Input[Auto])
    b = s.add_port("b", Input[Bits[5]])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", CustomVHDLOperator(
        {"aa": Bits[3], "bb": Auto},
        {"cc": Bits[8]},
        "t0 <= aa;\nt1 <= bb;\ncc <= t1 & t0;",
        "signal t0: std_logic_vector(2 downto 0);\nsignal t1: std_logic_vector(4 downto 0);"
    ))

    s.connect(a, u.IO.aa)
    s.connect(b, u.IO.bb)
    s.connect(u.IO.cc, c)


@here
def Test_Arith_Constants(s: Structure):
    a = s.add_port("a", Output[Auto])
    b = s.add_port("b", Output[Auto])
    c = s.add_port("c", Output[Auto])

    P = Bundle[{
        "a": UInt[4],
        "b": Bits[8],
        "c": Bundle[{
            "x": SInt[3],
            "y": SInt[5],
            "z": Bundle[{
                "n": UInt[8]
            }]
        }]
    }]

    p = P({
        "a": 20,
        "b": "00010010",
        "c": {
            "x": -5,
            "y": -2
        }
    })

    u = s.add_substructure("u", Constants(
        aaa = UInt[8](42),
        bbb = UInt[8](42), # p, # TODO BundleValue 重构之后还没重新实现
        ccc = SFixedPoint[4, 2](1.5)
    ))

    s.connect(u.IO.aaa, a)
    s.connect(u.IO.bbb, b)
    s.connect(u.IO.ccc, c)
    
    # return "hdl_CustomVHDLOperator_72493f969d0f2dcd.vhd"
    # return "hdl_root.vhd"


@here
def Test_Multiply_Bits(s: Structure):
    a = s.add_port("a", Input[Auto])
    b = s.add_port("b", Input[Auto])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", Multiply(Bits[5], Bits[7]))

    s.connect(a, u.IO.a)
    s.connect(b, u.IO.b)
    s.connect(c, u.IO.r)
    
    # return "emit"
    # return "hdl_Multiply_Bits_5_Bits_7.vhd"


@here
def Test_Multiply_SInt(s: Structure):
    a = s.add_port("a", Input[Auto])
    b = s.add_port("b", Input[Auto])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", Multiply(SInt[3], SInt[5], int_truncate = False))

    s.connect(a, u.IO.a)
    s.connect(b, u.IO.b)
    s.connect(c, u.IO.r)
    
    # return "emit"


@here
def Test_Multiply_SFixedPoint(s: Structure):
    a = s.add_port("a", Input[Auto])
    b = s.add_port("b", Input[Auto])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", Multiply(SFixedPoint[7, 4], SFixedPoint[7, 4]))

    s.connect(a, u.IO.a)
    s.connect(b, u.IO.b)
    s.connect(c, u.IO.r)
    
    return "emit"

