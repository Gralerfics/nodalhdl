from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.basic.bits import *
from nodalhdl.timing.sta import *
from nodalhdl.timing.pipelining import *


def info(s: Structure, show_hdl = False):
    rid = RuntimeId.create()
    s.deduction(rid)
    print(s.runtime_info(rid))

    model = s.generation(rid)
    if show_hdl:
        print(model.emit_vhdl()["hdl_root_u.vhd"])
        # emit_to_files(model_s.emit_vhdl(), "C:/Workspace/test_project/test_project.srcs/sources_1/new")

def here(f):
    print(f"<<<<<<<<<<<<<<<<<<<< {f.__name__} >>>>>>>>>>>>>>>>>>>>")
    s = Structure()
    info(s, show_hdl = bool(f(s)))


@here
def Test_BitsAdd_BitsSubtract(s: Structure):
    a = s.add_port("a", Input[Bits[4]])
    b = s.add_port("b", Input[Auto])
    c = s.add_port("c", Output[Bits[6]])

    u = s.add_substructure("u", BitsAdd[Auto])
    # u = s.add_substructure("u", BitsSubtract[Auto])

    s.connect(a, u.IO.a)
    s.connect(b, u.IO.b)
    s.connect(u.IO.r, c)


@here
def Test_BitsInverse(s: Structure):
    a = s.add_port("a", Input[Bits[6]])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", BitsInverse[Auto])

    s.connect(a, u.IO.a)
    s.connect(u.IO.r, c)


@here
def Test_BitsEqualTo(s: Structure):
    a = s.add_port("a", Input[Bits[4]])
    b = s.add_port("b", Input[Auto])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", BitsEqualTo[Auto])

    s.connect(a, u.IO.a)
    s.connect(b, u.IO.b)
    s.connect(u.IO.r, c)


@here
def Test_BitsLessThan(s: Structure):
    a = s.add_port("a", Input[Bits[6]])
    b = s.add_port("b", Input[Auto])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", BitsLessThan[Auto])

    s.connect(a, u.IO.a)
    s.connect(b, u.IO.b)
    s.connect(u.IO.r, c)


@here
def Test_BitsNot(s: Structure):
    a = s.add_port("a", Input[Bits[6]])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", BitsNot[Auto])

    s.connect(a, u.IO.a)
    s.connect(u.IO.r, c)


@here
def Test_BitsAnd_BitsOr(s: Structure):
    a = s.add_port("a", Input[Bits[6]])
    b = s.add_port("b", Input[Auto])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", BitsAnd[Auto])
    # u = s.add_substructure("u", BitsOr[Auto])

    s.connect(a, u.IO.a)
    s.connect(b, u.IO.b)
    s.connect(u.IO.r, c)


@here
def Test_BitsReductionAnd_BitsReductionOr(s: Structure):
    a = s.add_port("a", Input[Bits[6]])
    c = s.add_port("c", Output[Auto])

    # u = s.add_substructure("u", BitsReductionAnd[Auto])
    u = s.add_substructure("u", BitsReductionOr[Auto])

    s.connect(a, u.IO.a)
    s.connect(u.IO.r, c)
    
    return True


@here
def Test_BitsVHDLOperator(s: Structure):
    a = s.add_port("a", Input[Auto])
    b = s.add_port("b", Input[Bits[5]])
    c = s.add_port("c", Output[Auto])

    u = s.add_substructure("u", BitsVHDLOperator[
        (Bits[3], Auto),
        Bits[8],
        "t0 <= i0;\nt1 <= i1;\no0 <= t1 & t0;",
        "signal t0: std_logic_vector(2 downto 0);\nsignal t1: std_logic_vector(4 downto 0);"
    ])
    
    s.connect(a, u.IO.i0)
    s.connect(b, u.IO.i1)
    s.connect(u.IO.o0, c)
    
    return True

