import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit_aer import AerSimulator
import sys
import os

# Import our verified modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from arithmetic.modular_17 import Modular17
from arithmetic.ntt import QuantumNTT

class MiniDilithium:
    """
    A Toy implementation of Dilithium logic using Quantum Arithmetic.
    Parameters: N=2, q=17 (Micro Spec for fast Simulation)
    """
    def __init__(self):
        self.n = 2
        self.q = 17
        self.omega = 16 # Cyclic root (order 2)
        self.psi = 4   # Negacyclic root (psi^2 = 16 = -1)
        
        self.backend = Modular17()
        self.simulator = AerSimulator(method='statevector')
        self.ntt_engine = QuantumNTT(self.backend, self.n, self.q, self.omega)
        
        print(f"initialized Mini-Dilithium (N={self.n}, q={self.q})")
        print("Backend: Qiskit Aer Statevector Simulator")

    def classical_dft(self, vec):
        """Standard NTT for the public vector B (simulating classical part)"""
        # Pre-process (Psi map)
        vec_pre = [(vec[i] * pow(self.psi, i, self.q)) % self.q for i in range(self.n)]
        
        # DFT
        y = [0]*self.n
        for k in range(self.n):
            val = 0
            for j in range(self.n):
                term = (vec_pre[j] * pow(self.omega, j*k, self.q)) % self.q
                val = (val + term) % self.q
            y[k] = val
        return y

    def classical_idft(self, vec):
        """Inverse NTT for classical verification"""
        n_inv = pow(self.n, -1, self.q)
        # IDFT
        y = [0]*self.n
        for k in range(self.n):
            val = 0
            for j in range(self.n):
                # omega^{-jk}
                term = (vec[j] * pow(self.omega, -j*k, self.q)) % self.q
                val = (val + term) % self.q
            y[k] = (val * n_inv) % self.q
        
        # Post-process (Psi inverse map)
        out = [(y[i] * pow(self.psi, -i, self.q)) % self.q for i in range(self.n)]
        return out

    def verify_mul_step(self, poly_a, poly_b_hat, result_quantum, name):
        """Verifies if Quantum Mul result matches Classical Mul"""
        # 1. Classical A -> NTT(A)
        a_hat = self.classical_dft(poly_a)
        # 2. Pointwise C_hat = A_hat * B_hat
        c_hat = [(a * b) % self.q for a, b in zip(a_hat, poly_b_hat)]
        # 3. INTT(C_hat) -> C
        expected = self.classical_idft(c_hat)
        
        if expected == result_quantum:
             print(f"    [CHECK] {name}: OK (Quantum {result_quantum} == Classical {expected})")
             return True
        else:
             print(f"    [FAIL] {name}: Mismatch! Quantum {result_quantum} != Classical {expected}")
             return False

    def quantum_poly_mul(self, poly_a, poly_b_hat_classical, name="mul"):
        """Computes A * B using QuantumNTT."""
        regs = [QuantumRegister(5, f"r{i}") for i in range(self.n)]
        qc = QuantumCircuit(*regs)

        # 1. Encode Poly A
        for i, val in enumerate(poly_a):
            for bit in range(5):
                if (val >> bit) & 1:
                    qc.x(regs[i][bit])

        # 2. Forward NTT on A
        # Pre-process
        for i in range(self.n):
            factor = pow(self.psi, i, self.q)
            self.backend.mul_const_mod(qc, regs[i], factor, None)
            
        # NTT
        qc.compose(self.ntt_engine.build_ntt_circuit(regs, None, inverse=False), inplace=True)
        
        # 3. Pointwise
        for i in range(self.n):
            b_val = int(poly_b_hat_classical[i]) # Ensure int
            if b_val != 1:
                self.backend.mul_const_mod(qc, regs[i], b_val, None)

        # 4. Inverse NTT
        qc.compose(self.ntt_engine.build_ntt_circuit(regs, None, inverse=True), inplace=True)
        
        # Post-process
        for i in range(self.n):
            factor = pow(pow(self.psi, i, self.q), -1, self.q)
            self.backend.mul_const_mod(qc, regs[i], factor, None)

        qc.save_statevector()
        
        # Run
        t_qc = transpile(qc, self.simulator)
        job = self.simulator.run(t_qc)
        sv = np.asarray(job.result().get_statevector())
        
        # Decode
        prob = np.abs(sv)**2
        idx = np.argmax(prob)
        
        out = []
        for i in range(self.n):
            val = (idx >> (5*i)) & 0x1F
            out.append(val)
            
        return out
    
    def classical_add(self, poly_a, poly_b):
        """Pointwise addition mod q"""
        return [(a + b) % self.q for a, b in zip(poly_a, poly_b)]

    def classical_sub(self, poly_a, poly_b):
        """Pointwise subtraction mod q"""
        return [(a - b) % self.q for a, b in zip(poly_a, poly_b)]

    def classical_mul_scalar(self, poly, scalar):
        """Multiply polynomial by scalar mod q"""
        return [(c * scalar) % self.q for c in poly]

    def run_full_protocol(self):
        print("\n=== STAGE 6: FULL PROTOCOL SIMULATION (Mini-Dilithium) ===")
        print(f"Parameters: N={self.n}, q={self.q}")
        
        # --- 1. KEYGEN ---
        print("\n[1] KeyGen: Generating Keys...")
        # Secret vectors s1, s2
        s1 = [1, 2]
        s2 = [3, 1]
        print(f"  Secret s (s1, s2): {s1}, {s2}")
        
        # Public Matrix A (1x2 for simplicity: [p1, p2])
        A_row = [[2, 0], [1, 1]]
        print(f"  Public A (p1, p2): {A_row[0]}, {A_row[1]}")
        
        # t = A * s = p1*s1 + p2*s2
        print("  Computing t = A*s on Quantum Hardware...")
        # Transform A to NTT domain (simulate public/classical part)
        A_hat = [self.classical_dft(p) for p in A_row]
        
        # Validating Quantum Multiplication
        t_part1 = self.quantum_poly_mul(s1, A_hat[0]) # s1 * p1
        self.verify_mul_step(s1, A_hat[0], t_part1, "s1*p1")
        
        t_part2 = self.quantum_poly_mul(s2, A_hat[1]) # s2 * p2
        self.verify_mul_step(s2, A_hat[1], t_part2, "s2*p2")
        
        t = self.classical_add(t_part1, t_part2)
        print(f"  Public Key t: {t}")
        
        # Compute Expected classical t
        # (Assuming quantum mul passed, add is simple, so t is good. But let's check t itself is sane)
        if t == [4, 8]: # Known correct value for this fixed input
            print(">>> KEYGEN SUCCESSFUL")
        else:
            print(">>> KEYGEN FAILED (Value mismatch)")
        
        
        # --- 2. SIGN ---
        print("\n[2] Sign: Creating Signature...")
        # Sample ephemeral vector y
        y1 = [1, 0]
        y2 = [0, 1]
        print(f"  Sampled y (y1, y2): {y1}, {y2}")
        
        # Compute w = A * y
        print("  Computing w = A*y on Quantum Hardware...")
        w_part1 = self.quantum_poly_mul(y1, A_hat[0])
        self.verify_mul_step(y1, A_hat[0], w_part1, "y1*p1")
        
        w_part2 = self.quantum_poly_mul(y2, A_hat[1])
        self.verify_mul_step(y2, A_hat[1], w_part2, "y2*p2")
        
        w = self.classical_add(w_part1, w_part2)
        print(f"  Commitment w: {w}")
        
        # Verify w calculation
        if w == [1, 1]: # Known correct for inputs
             print(">>> COMMITMENT (w) GENERATION SUCCESSFUL")
        else:
             print(">>> COMMITMENT FAILED")

        # Create Challenge c (Simplified: random scalar polynomial)
        c = [1, 0] # Polynomial c(x) = 1
        print(f"  Challenge c: {c}")
        
        # Compute z = y + c*s (Classically)
        # z1 = y1 + c*s1
        # z2 = y2 + c*s2
        # Here c=1, so z = y + s
        z1 = self.classical_add(y1, s1)
        z2 = self.classical_add(y2, s2)
        print(f"  Signature z (z1, z2): {z1}, {z2}")
        print(f"  Signature sent: (z, c)")
        
        # We assume Sign phase is pure classical mixing after w is found.
        # But we verify z is consistent
        if z1 == [2, 2] and z2 == [3, 2]:
             print(">>> SIGNATURE GENERATION SUCCESSFUL")
        
        
        # --- 3. VERIFY ---
        print("\n[3] Verify: Checking Signature...")
        # Verifier knows: A (public), t (public), z (singature), c (signature)
        # Check: A*z - c*t =? w
        
        print("  Verifier computes w' = A*z - c*t...")
        
        # 3.1 Compute A*z (Quantumly!)
        print("  Computing A*z on Quantum Hardware...")
        Az_part1 = self.quantum_poly_mul(z1, A_hat[0])
        self.verify_mul_step(z1, A_hat[0], Az_part1, "z1*p1")

        Az_part2 = self.quantum_poly_mul(z2, A_hat[1])
        self.verify_mul_step(z2, A_hat[1], Az_part2, "z2*p2")

        Az = self.classical_add(Az_part1, Az_part2)
        print(f"  A*z: {Az}")
        
        # 3.2 Compute c*t (Classical, t is public)
        # c=1 => c*t = t
        ct = t
        
        # 3.3 Compute w' = Az - ct
        w_prime = self.classical_sub(Az, ct)
        print(f"  Computed w': {w_prime}")
        
        print(f"  Original w : {w}")
        
        if w_prime == w:
            print("\n>>> VERIFICATION SUCCESSFUL: Signature is valid!")
        else:
            print("\n>>> VERIFICATION FAILED: Signature invalid.")

if __name__ == "__main__":
    demo = MiniDilithium()
    demo.run_full_protocol()
