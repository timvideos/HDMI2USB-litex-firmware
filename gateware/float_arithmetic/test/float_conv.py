import numpy as np

def float2binint(f):
    x = int(bin(np.float16(f).view('H'))[2:].zfill(16),2)
    return x


def binint2float(x):
    xs = bin(x)[2:].zfill(16)
    frac = '1'+xs[6:16]
    fracn = int(frac,2)
    exp = xs[1:6]
    expn = int(exp,2) -15

    if expn == -15 :
        expn = -14
        frac = '0'+xs[6:16]
        fracn = int(frac,2)

    sign = xs[0]
    signv = int(sign,2)

    y = ((-1)**signv)*(2**(expn))*fracn*(2**(-10))
    return y
