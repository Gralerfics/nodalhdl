import math


def seq_until(n):
    res = []
    idx = k = 1
    while len(res) < n:
        res.append(idx)
        if idx == k * 3 + 1:
            res.append(idx)
            k = k * 3 + 1
        idx += 1
    return res

ITER = 16
SEQ = seq_until(ITER)
K = math.prod([math.sqrt(1 - 2 ** (-2 * i)) for i in SEQ])
K_INV = 1 / K


SQRT2 = math.sqrt(2)

A = 200
a = A / 2 ** 7

x = a + 1
y = a - 1

for idx in SEQ:
    dx = x / 2 ** idx
    dy = y / 2 ** idx
    if y < 0:
        x += dy
        y += dx
    else:
        x -= dy
        y -= dx

r = x * K_INV * 2 ** (7 // 2 - 1) * SQRT2

print(r)
print(math.sqrt(A))

# =======================================================================

# a = 200

# x = a + 100
# y = a - 100

# for idx in SEQ:
#     dx = x / 2 ** idx
#     dy = y / 2 ** idx
#     if y < 0:
#         x += dy
#         y += dx
#     else:
#         x -= dy
#         y -= dx

# r = x * K_INV / 2 / math.sqrt(100)

# print(r)
# print(math.sqrt(a))

# =======================================================================

# FAC = 2 ** 16

# a = 2 * FAC

# x = a + 1 * FAC
# y = a - 1 * FAC

# for idx in SEQ:
#     dx = x / 2 ** idx
#     dy = y / 2 ** idx
#     if y < 0:
#         x += dy
#         y += dx
#     else:
#         x -= dy
#         y -= dx

# r = x * K_INV / 2

# print(r / FAC)
# print(math.sqrt(a / FAC))

