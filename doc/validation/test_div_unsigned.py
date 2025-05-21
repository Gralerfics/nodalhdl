# https://witscad.com/course/computer-architecture/chapter/fixed-point-arithmetic-division

Wi = 10
Wf = 12

def add(a: str, b: str, bits: int):
    return bin((int(a, base = 2) + int(b, base = 2)) % 2 ** bits)[2:].zfill(bits)

def flip(x: str):
    return "".join([str(49 - ord(c)) for c in x])

def complement(x: str):
    return add(flip(x), "1", len(x))

def divide(dividend: str, divisor: str):
    # init
    E = "0"
    A = "0" * (Wi + Wf)
    Q = dividend + "0" * Wf
    Q_res = ""
    R_int = None
    
    # divisor
    divisor_EA = divisor[0] + divisor
    divisor_EA_inv = complement(divisor_EA)
    print(f"B = {divisor_EA}, -B = {divisor_EA_inv}\n")
    
    # iteration
    print(f"R0\t{E} {A} {Q}")
    for idx in range(0, Wi + Wf + Wf):
        # shift
        E = A[0]
        A = A[1:] + Q[0]
        Q = Q[1:]
        print(f"2R{idx}\t{E} {A} {Q} {Q_res}_")
        
        # +/- divisor
        if E[0] == "0":
            print(f"-B\t{divisor_EA_inv[0]} {divisor_EA_inv[1:]}")
            EA_add = add(E + A, divisor_EA_inv, len(divisor_EA))
        else:
            print(f"+B\t{divisor_EA[0]} {divisor_EA[1:]}")
            EA_add = add(E + A, divisor_EA, len(divisor_EA))
        E = EA_add[0]
        A = EA_add[1:]
        
        # q
        if E[0] == "0":
            Q_res += "1"
        else:
            Q_res += "0"
        
        print(f"R{idx + 1}\t{E} {A} {Q} {Q_res}")
        
        # mod
        if idx == Wi + Wf - 1:
            R_int = E + A
            if E[0] == "1":
                R_int = add(R_int, divisor_EA, len(divisor_EA))
            R_int = R_int[1:]
    
    # correction
    if E[0] == "1":
        print(f"+B\t{divisor_EA[0]} {divisor_EA[1:]}")
        EA_add = add(E + A, divisor_EA, len(divisor_EA))
        E = EA_add[0]
        A = EA_add[1:]
        print(f"R\t{E} {A} {Q} {Q_res}")
    
    return Q_res[Wf:], A, R_int


# divide(
#     "001010",
#     "010100"
# )

a = 12
b = 3.2

Q, R, M = divide(
    bin(int(a * 2 ** Wf))[2:].zfill(Wi + Wf),
    bin(int(b * 2 ** Wf))[2:].zfill(Wi + Wf)
)

q = int(Q, base = 2) / 2 ** Wf
r = int(R, base = 2) / 2 ** (Wf + Wf)
m = int(M, base = 2) / 2 ** Wf

print(f"a = {a}, b = {b};\nq = {q}, r = {r};\na / b = {a / b};\nqb + r = {q * b + r};\nm = {m}")


# TODO 可能有错漏, 主要看 signed 版本.

