class Resourcecounter:
    def __init__(self):
        self.t_count = 0
        self.clifford_count = 0 
        self.measurement_count = 0
        self.qubit_width = 0
        
    def add_gates(self, t=0, clifford=0, measure=0):
        self.t_count += t
        self.clifford_count += clifford
        self.measurement_count += measure
        
    def report(self):
        return {
            "T-count": self.t_count,
            "Clifford-count": self.clifford_count,
            "Measurements": self.measurement_count,
            "Width (Qubits)": self.qubit_width
        }

class DilithiumEstimator:
    def __init__(self, N, q):
        self.N = N
        self.q = q
        self.k = q.bit_length() # Bits per coefficient
        self.counter = Resourcecounter()
        
    def estimate_ripple_adder(self, bits):
        """
        Cuccaro Ripple Carry Adder (Input Carry = 0)
        Cost per bit: 2 Toffoli + 5 CNOT (MAJ/UMA blocks)
        Approximate T-count:
        1 Toffoli = 7 T gates + 8 Clifford (Standard decomposition)
        Per bit: 2*7 = 14 T-gates.
        """
        c_toffoli = 2 * bits
        c_cnot = 5 * bits
        
        # Toffoli decomp: 7 T, 8 Clifford
        t = c_toffoli * 7
        cliff = c_toffoli * 8 + c_cnot
        return t, cliff

    def estimate_mod_add(self):
        """
        Modular Addition (A + B mod q)
        Pattern: 
        1. Add A + B -> Sum (k+1 bits)
        2. Subtract q (Add -q)
        3. Check sign (MSB)
        4. Mux (Select Sum or Sum-q)
        
        Optimized usually:
        1. Compute A+B
        2. Compute A+B-q
        3. Swap based on sign bit
        (Requires ~3 adders)
        """
        # 3 Ripple Adders of k bits
        t_adder, cliff_adder = self.estimate_ripple_adder(self.k)
        
        total_t = 3 * t_adder
        total_cliff = 3 * cliff_adder
        return total_t, total_cliff

    def estimate_mod_mul_const(self):
        """
        Multiply by constant (shift-add).
        Average hamming weight of constant ~ k/2.
        So we do k/2 modular additions.
        """
        ops = self.k / 2
        t_add, cliff_add = self.estimate_mod_add()
        return ops * t_add, ops * cliff_add

    def estimate_butterfly(self):
        """
        CT/GS Butterfly:
        A' = A + B
        B' = (A - B) * w
        
        Ops: 
        1 ModAdd (A+B)
        1 ModSub (A-B) ~= ModAdd
        1 ModMulConst ( * w)
        """
        t_add, cliff_add = self.estimate_mod_add()
        t_mul, cliff_mul = self.estimate_mod_mul_const()
        
        total_t = 2 * t_add + t_mul
        total_cliff = 2 * cliff_add + cliff_mul
        return total_t, total_cliff

    def estimate_ntt(self):
        """
        Forward NTT.
        Layers: log2(N)
        Butterflies per layer: N/2
        Total Butterflies: (N/2) * log2(N)
        """
        import math
        layers = int(math.log2(self.N))
        butterflies = (self.N // 2) * layers
        
        t_bf, cliff_bf = self.estimate_butterfly()
        
        total_t = butterflies * t_bf
        total_cliff = butterflies * cliff_bf
        
        self.counter.add_gates(t=total_t, clifford=total_cliff)
        
        # Width: N coeffs * k bits + Aux
        # Aux for adder is usually 1 or 2 bits, reused.
        self.counter.qubit_width = self.N * self.k + 2 
        
    def estimate_pointwise_mul(self, vector_len):
        """
        Pointwise Mul of two encoded polynomials A * B mod q.
        This is expensive: N General Modular Multiplications.
        (Unless B is constant/classical, but generally assumed quantum-quantum for worst case).
        
        If we assume worst case:
        General ModMul (k bits) ~ k ModAdd (shift-add controlled).
        """
        t_add, cliff_add = self.estimate_mod_add()
        t_mul = self.k * t_add
        cliff_mul = self.k * cliff_add
        
        total_t = vector_len * t_mul
        total_cliff = vector_len * cliff_mul
        
        self.counter.add_gates(t=total_t, clifford=total_cliff)

    def run_full_stack_estimate(self):
        print(f"Estimating Resources for Dilithium (N={self.N}, q={self.q}, k={self.k} bits)")
        
        # 1. NTT on Poly A
        print("- Component: NTT (Forward)...")
        self.estimate_ntt()
        
        # 2. Pointwise Mul
        # (Assuming Poly multiplication involves 1 NTT and 1 Pointwise, simplified)
        # Actually A*B = INTT( NTT(A) . NTT(B) )
        # So we need 3 NTTs (2 Fwd, 1 Inv) + 1 Pointwise.
        # But usually B is public (NTT classical), so only NTT(A), Pointwise, INTT.
        # Let's estimate that flow: A(Quantum) * B(Classical).
        
        print("- Component: Pointwise Mul (Quantum-Classical)...")
        # If B is classical, it's just N constant multiplications.
        t_mul, cliff_mul = self.estimate_mod_mul_const()
        self.counter.add_gates(t=self.N * t_mul, clifford=self.N * cliff_mul)
        
        print("- Component: INTT (Inverse)...")
        self.estimate_ntt()
        
        results = self.counter.report()
        print("\n=== Estimation Report ===")
        print(f"Total T-gates: {results['T-count']:,}")
        print(f"Total Clifford: {results['Clifford-count']:,}")
        print(f"Est. Logical Qubits: {results['Width (Qubits)']:,}")
        return results

if __name__ == "__main__":
    # Dilithium2 Parameters
    # q = 8380417 (23 bits)
    # N = 256
    estimator = DilithiumEstimator(256, 8380417)
    estimator.run_full_stack_estimate()