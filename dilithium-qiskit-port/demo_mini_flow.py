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
    
    def demo_keygen_part(self):
        print("\n=== Demo: Vector-Matrix Multiplication (KeyGen Core) ===")
        print(f"Computing t = As (one row), where A is public, s is secret (N={self.n}).")
        
        # Micro Dilithium (N=2)
        # s1 = [1, 2], s2 = [3, 1]
        s1 = [1, 2]
        s2 = [3, 1]
        print(f"Secret s1: {s1}")
        print(f"Secret s2: {s2}")
        
        # p1 = [2, 0], p2 = [1, 1]
        p1 = [2, 0]
        p2 = [1, 1]
        print(f"Public p1: {p1}")
        print(f"Public p2: {p2}")
        
        print("\n--- Step 1: Compute NTT of Public Polys (Classical) ---")
        p1_hat = self.classical_dft(p1)
        p2_hat = self.classical_dft(p2)
        print(f"NTT(p1): {p1_hat}")
        print(f"NTT(p2): {p2_hat}")
        
        print("\n--- Step 2: Compute Quantum Convolutions ---")
        print("Calculating Term 1: s1 * p1 on Quantum Computer...")
        term1 = self.quantum_poly_mul(s1, p1_hat, "s1*p1")
        print(f"Result Term 1: {term1}")
        
        print("Calculating Term 2: s2 * p2 on Quantum Computer...")
        term2 = self.quantum_poly_mul(s2, p2_hat, "s2*p2")
        print(f"Result Term 2: {term2}")
        
        print("\n--- Step 3: Accumulate Results (Classical Adder for final assembly) ---")
        # In real hardware, this addition could also be quantum or classical post-measurement.
        # Since we measured the terms, we add classically here mod 17.
        t = [(t1 + t2) % self.q for t1, t2 in zip(term1, term2)]
        print(f"Final Result t = A*s : {t}")
        print("Done demo.")

if __name__ == "__main__":
    demo = MiniDilithium()
    demo.demo_keygen_part()
