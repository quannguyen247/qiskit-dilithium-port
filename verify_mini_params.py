"""
Script kiểm chứng bộ tham số rút gọn (Mini-Dilithium) cho Giai đoạn 4.
Mục tiêu: Đảm bảo N=4, q=17 thỏa mãn đầy đủ tính chất đại số của Dilithium (NTT, Negacyclic Convolution).
"""

def verify_parameters():
    print("=== VERIFYING MINI-DILITHIUM PARAMETERS ===")
    N = 4
    q = 17
    print(f"Parameters: N={N}, q={q}")

    # 1. Check NTT Condition: q = 1 mod 2N
    # 2N = 8.
    check = (q - 1) % (2 * N) == 0
    print(f"Condition q = 1 mod 2N ({2*N}): {'PASSED' if check else 'FAILED'} (16 % 8 == 0)")
    if not check:
        return False

    # 2. Find primitive 2N-th root of unity (root needed for Negacyclic NTT)
    # We need w such that w^N = -1 mod q.
    # Which implies w^2N = 1 mod q.
    # In Z_17, we need element of order 8.
    roots = []
    for x in range(1, q):
        # check order
        order = 0
        val = 1
        for k in range(1, q):
            val = (val * x) % q
            if val == 1:
                order = k
                break
        if order == 8:
            roots.append(x)
            
    print(f"Primitive 2N-th (8th) roots of unity in Z_{q}: {roots}")
    
    if not roots:
        print("CRITICAL ERROR: No suitable root of unity found!")
        return False
        
    omega = roots[0] # Pick the first one, usually smallest or standard
    # In Dilithium spec, they pick specific roots. Let's pick 2 if available. 
    # 2^4 = 16 = -1. 2^8 = 1. Yes, 2 is a root.
    if 2 in roots:
        omega = 2
    
    print(f"Selected omega (zeta): {omega}")
    print(f"Check: omega^N = {omega}^{N} = {pow(omega, N, q)} (Expected q-1 = {q-1})")
    
    # 3. Simulate Classical NTT with these parameters
    # Input polys
    a = [1, 2, 3, 4]
    b = [5, 6, 7, 8]
    print(f"\nTest Polynomials:\nA(x) = {a}\nB(x) = {b}")
    
    # Reference Multiplication (Schoolbook) in Z_17[X]/(X^4 + 1)
    # Ref: (1 + 2x + 3x^2 + 4x^3)(5 + 6x + 7x^2 + 8x^3)
    # Calculate regular product then mod X^4+1
    full_prod = [0] * (2*N)
    for i in range(N):
        for j in range(N):
            full_prod[i+j] += a[i] * b[j]
            
    # Reduce mod X^4 + 1: x^4 = -1, x^5 = -x, etc.
    res_ref = [0] * N
    for i in range(2*N):
        coeff = full_prod[i]
        if i < N:
            res_ref[i] = (res_ref[i] + coeff) % q
        else:
            # i >= N. coeff * x^i = coeff * x^(i-N) * x^N = coeff * x^(i-N) * (-1)
            deg = i - N
            res_ref[deg] = (res_ref[deg] - coeff) % q
            
    print(f"Expected Result (Schoolbook): {res_ref}")
    
    # 4. NTT Multiplication (The Logic we will implement in Quantum)
    # Standard Dilithium Cooley-Tukey NTT
    # Zeta generator: powers of omega
    
    def ntt(poly, n, q, w):
        # Simple recursive or iterative NTT
        # For N=4, let's just do the DFT formula with twist for Negacyclic
        # Dilithium NTT maps a -> A where A[i] = sum(a[j] * w^( (2i+1)*j )) ? 
        # Actually Dilithium uses a specific explicit formula.
        # But generally: Number Theoretic Transform for Negacyclic convolution
        # uses twist factors psi^j where psi^2 = omega? 
        # Standard approach: Pre-multiply inputs by psi^i, do standard NTT, Post-multiply...
        # OR define NTT over roots of X^N+1 directly (which are odd powers of primitive 2N-th root).
        
        # Roots of X^4+1 are: w^1, w^3, w^5, w^7 (where w is 8-th root).
        # Let's verify: (w^k)^4 = w^4k = (-1)^k. If k is odd, -1. Correct.
        
        # Transform A: evaluation at [w^1, w^3, w^5, w^7]
        points = [pow(w, 2*i + 1, q) for i in range(n)]
        y = []
        for point in points:
            val = 0
            for i, coeff in enumerate(poly):
                val = (val + coeff * pow(point, i, q)) % q
            y.append(val)
        return y

    def intt(Y, n, q, w):
        # Inverse
        # Interpolation.
        # Since we evaluated at roots, we can use standard Inverse formula but careful with weights.
        # For simplicity in this verifiction script, let's use the explicit inverse matrix logic
        # or just solving the linear system.
        # But we want to check if Pointwise Mul works.
        pass
        return []

    A_w = ntt(a, N, q, omega)
    B_w = ntt(b, N, q, omega)
    C_w = [(x * y) % q for x, y in zip(A_w, B_w)]
    
    # Inverse NTT to find c
    # Instead of full INTT code, let's brute force search for c that matches C_w
    # This proves existence and uniqueness.
    
    found_c = None
    import itertools
    for candidate in itertools.product(range(q), repeat=N):
        cand_w = ntt(candidate, N, q, omega)
        if cand_w == C_w:
            found_c = list(candidate)
            break
            
    print(f"NTT Result (Pointwise Mul -> INTT): {found_c}")
    
    if found_c == res_ref:
        print(">>> SUCCESS: Parameters N=4, q=17 preserve Negacyclic Convolution perfectly.")
        return True
    else:
        print(">>> FAIL: Mismatch between Schoolbook and NTT.")
        return False

if __name__ == "__main__":
    verify_parameters()
