import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
import qiskit
from qiskit_aer import AerSimulator
import sys
import os
import time
import platform
import subprocess

# Import our verified modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
# Import Configuration
sys.path.append(os.path.dirname(__file__)) # Add current dir
import parameters 

from arithmetic.modular_17 import Modular17
from arithmetic.ntt import QuantumNTT

class MiniDilithium:
    """
    A Toy implementation of Dilithium logic using Quantum Arithmetic.
    Configurable via parameters.py
    """
    def __init__(self, config=None):
        # Load Config
        if config is None:
            config = parameters.CURRENT_CONFIG
            
        self.config = config
        self.n = config.N
        self.q = config.q
        self.omega = config.omega
        self.psi = config.psi
        
        self.backend = Modular17()
        # Initialize Backend based on Config
        if config.backend_method == 'statevector':
            self.simulator = AerSimulator(method='statevector')
        else:
            self.simulator = AerSimulator(method=config.backend_method, shots=config.shots)
            
        self.ntt_engine = QuantumNTT(self.backend, self.n, self.q, self.omega)
        
        print(f"initialized: {config.name}")
        print(f"Backend: {config.backend_name} [{config.backend_method}]")

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
        
        # --- Handle Fixed/Custom Qubit Allocation ---
        if not self.config.use_auto_qubits:
            current_qubits = self.n * 5
            target = self.config.custom_qubit_count
            padding = target - current_qubits
            if padding > 0:
                pad_reg = QuantumRegister(padding, "pad")
                qc = QuantumCircuit(*regs, pad_reg)
                # Pad qubits remain |0> (idle), just consuming simulator memory
            elif padding < 0:
                 # WARNING: target < current_qubits
                 # Cannot simulate fewer qubits than logic requires.
                 # Fallback to minimum required with a warning on first run.
                 if not hasattr(self, "_warned_qubit_override"):
                     print(f"\n[WARNING] Custom Qubits ({target}) < Minimum Required ({current_qubits}).")
                     print(f"          Overriding to minimum: {current_qubits} qubits.")
                     self._warned_qubit_override = True
                 qc = QuantumCircuit(*regs) 
            else:
                 # Exact match, proceed normally
                 qc = QuantumCircuit(*regs) 
        else:
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
        # optimization_level=0: Skip slow circuit optimization (critical for large circuits)
        t_qc = transpile(qc, self.simulator, optimization_level=0)
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

    def print_specs(self, t_keygen, t_sign, t_verify):
        total_t = t_keygen + t_sign + t_verify
        cpu_name = parameters.get_cpu_info()
        
        print("\n" + "="*60)
        print("          SYSTEM & SIMULATION SPECIFICATIONS")
        print("="*60)
        print(f"Host OS:        {platform.system()} {platform.release()} ({platform.machine()})")
        print(f"Processor:      {cpu_name}")
        print(f"Python Version: {sys.version.split()[0]}")
        try:
            print(f"Qiskit Core:    {qiskit.__version__}")
        except: pass
        try:
            import qiskit_aer
            print(f"Qiskit Aer:     {qiskit_aer.__version__}")
        except ImportError:
            pass

        print("-" * 60)
        print("SIMULATION CONTEXT:")
        print(f"  - Config Name:       {self.config.name}")
        print(f"  - Parameter Set:     N={self.config.N}, q={self.config.q}")
        print(f"  - Roots Of Unity:    Omega={self.config.omega}, Psi={self.config.psi}")
        print(f"  - Simulator Backend: {self.config.backend_name} [{self.config.backend_method}]")
        
        # Approx active qubits: N * k bits + Aux
        active_qubits = self.config.N * self.config.k_bits + 3 
        print(f"  - Active Qubits:     ~{active_qubits} (per convolution op)")
        import math
        depth = f"~O({self.config.k_bits} * log {self.config.N})"
        print(f"  - Circuit Depth:     {depth}")

        print("-" * 60)
        print("PERFORMANCE TIMING (Single Thread):")
        print(f"  - [Stage 1] KeyGen:  {t_keygen:.4f} sec")
        print(f"  - [Stage 2] Sign:    {t_sign:.4f} sec")
        print(f"  - [Stage 3] Verify:  {t_verify:.4f} sec")
        print(f"  ------------------------------")
        print(f"  - TOTAL EXECUTION:   {total_t:.4f} sec")
        print("="*60 + "\n")

    def run_full_protocol(self):
        print("\n=== STAGE 6: FULL PROTOCOL SIMULATION ===")
        print(f"Config: {self.config.name}")
        
        t0 = time.time()

        # --- 1. KEYGEN ---
        print("\n[1] KeyGen: Generating Keys...")
        # Generate random polys for s1, s2
        # For determinism in demo, we can seed or use fixed pattern
        import random
        random.seed(42) # Deterministic for demo
        
        def random_poly(n, bound):
            return [random.randint(0, bound-1) for _ in range(n)]
            
        s1 = random_poly(self.n, 5) # Small coeffs
        s2 = random_poly(self.n, 5)
        print(f"  Secret s (s1, s2): {s1}, {s2}")
        
        # Public Matrix A (1x2 for simplicity: [p1, p2])
        A_row = [random_poly(self.n, self.q), random_poly(self.n, self.q)]
        print(f"  Public A (p1, p2): {A_row[0]}, {A_row[1]}")
        
        # t = A * s = p1*s1 + p2*s2
        print("  Computing t = A*s on Quantum Hardware...")
        # Transform A to NTT domain (simulate public/classical part)
        A_hat = [self.classical_dft(p) for p in A_row]
        
        # Validating Quantum Multiplication
        t_part1 = self.quantum_poly_mul(s1, A_hat[0], "s1*p1") # s1 * p1
        self.verify_mul_step(s1, A_hat[0], t_part1, "s1*p1")
        
        t_part2 = self.quantum_poly_mul(s2, A_hat[1], "s2*p2") # s2 * p2
        self.verify_mul_step(s2, A_hat[1], t_part2, "s2*p2")
        
        t = self.classical_add(t_part1, t_part2)
        print(f"  Public Key t: {t}")
        
        print(">>> KEYGEN COMPLETE")
            
        t1 = time.time()
        keygen_dur = t1 - t0
        
        # --- 2. SIGN ---
        print("\n[2] Sign: Creating Signature...")
        # Sample ephemeral vector y
        y1 = random_poly(self.n, 3)
        y2 = random_poly(self.n, 3)
        print(f"  Sampled y (y1, y2): {y1}, {y2}")
        
        # Compute w = A * y
        print("  Computing w = A*y on Quantum Hardware...")
        w_part1 = self.quantum_poly_mul(y1, A_hat[0], "y1*p1")
        self.verify_mul_step(y1, A_hat[0], w_part1, "y1*p1")
        
        w_part2 = self.quantum_poly_mul(y2, A_hat[1], "y2*p2")
        self.verify_mul_step(y2, A_hat[1], w_part2, "y2*p2")
        
        w = self.classical_add(w_part1, w_part2)
        print(f"  Commitment w: {w}")
        print(">>> COMMITMENT (w) GENERATION COMPLETE")

        # Create Challenge c (Simplified: random scalar polynomial)
        c = [0] * self.n
        c[0] = 1 # Polynomial c(x) = 1
        print(f"  Challenge c: {c}")
        
        # Compute z = y + c*s (Classically)
        # z1 = y1 + c*s1
        # z2 = y2 + c*s2
        # Here c=1, so z = y + s
        z1 = self.classical_add(y1, s1)
        z2 = self.classical_add(y2, s2)
        print(f"  Signature z (z1, z2): {z1}, {z2}")
        print(f"  Signature sent: (z, c)")
        print(">>> SIGNATURE GENERATION COMPLETE")
        
        t2 = time.time()
        sign_dur = t2 - t1
        
        # --- 3. VERIFY ---
        print("\n[3] Verify: Checking Signature...")
        # Verifier knows: A (public), t (public), z (singature), c (signature)
        # Check: A*z - c*t =? w
        
        print("  Verifier computes w' = A*z - c*t...")
        
        # 3.1 Compute A*z (Quantumly!)
        print("  Computing A*z on Quantum Hardware...")
        Az_part1 = self.quantum_poly_mul(z1, A_hat[0], "z1*p1")
        self.verify_mul_step(z1, A_hat[0], Az_part1, "z1*p1")

        Az_part2 = self.quantum_poly_mul(z2, A_hat[1], "z2*p2")
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
            
        t3 = time.time()
        verify_dur = t3 - t2
        
        # --- REPORT ---
        self.print_specs(keygen_dur, sign_dur, verify_dur)

if __name__ == "__main__":
    # You can switch configuration here:
    # config = parameters.DilithiumConfig.Mini() # For N=4 (Slow!)
    # config = parameters.DilithiumConfig.Micro() # For N=2 (Fast)
    
    # Use the default from parameters.py
    config = parameters.CURRENT_CONFIG
    
    # Optional: Override shots for noisy backends if needed
    # config.shots = 2048 

    # DISCLAIMER
    if config.N < 256:
        print("\n[NOTE] Running 'Toy' or 'Mini' Dilithium variant.")
        print("       These parameters are for algorithmic verification only.")
        print("       They do NOT provide cryptographic security (easy to break).")
        print("       Standard Dilithium requires N=256, q=8380417.")

    demo = MiniDilithium(config)
    demo.run_full_protocol()
