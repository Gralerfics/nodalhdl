# https://ashkanyeganeh.com/wp-content/uploads/2020/03/computer-arithmetic-algorithms-2nd-edition-Behrooz-Parhami.pdf
# Page 275

def add(a: str, b: str, bits: int):
    return bin((int(a, base = 2) + int(b, base = 2)) % 2 ** bits)[2:].zfill(bits)

def flip(x: str):
    return "".join([str(49 - ord(c)) for c in x])

def complement(x: str):
    return add(flip(x), "1", len(x))

def divide(dividend: str, divisor: str):
    print(f"A = {dividend}")
    
    # init
    E = dividend[0]
    A = dividend[0] * len(divisor)
    Q = dividend
    Q_res = ""
    
    # divisor
    divisor_EA = divisor[0] + divisor
    divisor_EA_inv = complement(divisor_EA)
    print(f"B = {divisor_EA}, -B = {divisor_EA_inv}\n")
    
    # iteration
    print(f"R0\t{E} {A} {Q}\n")
    for idx in range(0, len(dividend)):
        # shift
        E = A[0]
        A = A[1:] + Q[0]
        Q = Q[1:]
        print(f"2R{idx}\t{E} {A} {Q} {Q_res}_")
        
        # +/- divisor
        if E[0] != divisor[0]:
            print(f"+B\t{divisor_EA[0]} {divisor_EA[1:]}")
            Q_res += "0"
            EA_add = add(E + A, divisor_EA, len(divisor_EA))
        else:
            print(f"-B\t{divisor_EA_inv[0]} {divisor_EA_inv[1:]}")
            Q_res += "1"
            EA_add = add(E + A, divisor_EA_inv, len(divisor_EA))
        E = EA_add[0]
        A = EA_add[1:]
        
        print(f"R{idx + 1}\t{E} {A} {Q} {Q_res}\n")
    
    # quotient convertion
    Q_res = flip(Q_res[0]) + Q_res[1:] + "1"
        # 这里 flip(Q_res[0]) 应和 Q_res[1] 一致, 否则应该是 overflow 了. 可以用于判断 overflow.
    
    # remainder correction
    if E[0] != dividend[0] and ("1" in E + A) or (E + A == divisor_EA) or (E + A == divisor_EA_inv):
        """
            1. 余数和被除数符号不同时修正;
            2. 即使符号不同, 余数为 0 时也不用修正 (没有 -0);
            3. 符号相同但余数和除数的绝对值相同时也需要修正.
            * 实质上后两点分别就是 0 <= r < |b| 的两个界.
            * TODO 有没有更好的判断或者处理方式.
        """
        if E[0] == divisor[0]:
            print(f"-B\t{divisor_EA_inv[0]} {divisor_EA_inv[1:]}")
            EA_add = add(E + A, divisor_EA_inv, len(divisor_EA))
            Q_res = add(Q_res, "1", len(Q_res))
        else:
            print(f"+B\t{divisor_EA[0]} {divisor_EA[1:]}")
            EA_add = add(E + A, divisor_EA, len(divisor_EA))
            Q_res = add(Q_res, "1" * len(Q_res), len(Q_res))
        E = EA_add[0]
        A = EA_add[1:]
        
        print(f"R{idx + 1}\t{E} {A} {Q}")
    
    return Q_res, A


Wi = 8
Wf = 0

a = -9
b = 4

Q, R = divide(
    bin(int(a * 2 ** Wf) % 2 ** (Wi + Wf))[2:].zfill(Wi + Wf) + "0" * Wf,
    bin(int(b * 2 ** Wf) % 2 ** (Wi + Wf))[2:].zfill(Wi + Wf)
)

q = ((int(Q, base = 2) + 2 ** (Wi + Wf - 1)) % 2 ** (Wi + Wf) - 2 ** (Wi + Wf - 1)) / 2 ** Wf
r = ((int(R, base = 2) + 2 ** (Wi + Wf - 1)) % 2 ** (Wi + Wf) - 2 ** (Wi + Wf - 1)) / 2 ** (Wf + Wf)

print(f"a = {a}, b = {b};\nq = {q}, r = {r};\na / b = {a / b};\nqb + r = {q * b + r}")


# print(divide(
#     "00100001",
#     "1001"
# ))

