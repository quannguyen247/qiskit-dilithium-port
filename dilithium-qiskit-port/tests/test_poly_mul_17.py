import unittest
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit_aer import Aer
import sys
import os

# Adjust path to import src
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from arithmetic.modular_17 import Modular17
from arithmetic.ntt import QuantumNTT

class TestPolyMul17(unittest.TestCase):
    def setUp(self):
        self.backend = Modular17()
        self.n = 4
        self.q = 17
        self.omega = 4 # Cyclic root of unity (order 4 in Z17)
        self.psi = 2   # Negacyclic root (psi^2 = omega)
        self.ntt = QuantumNTT(self.backend, self.n, self.q, self.omega)
        self.simulator = Aer.get_backend('aer_simulator')
        self.simulator.set_options(method="statevector")

    def classical_dft(self, vec, omega):
        # Naive DFT for verification
        n = len(vec)
        y = [0]*n
        for k in range(n):
            val = 0
            for j in range(n):
                term = (vec[j] * pow(omega, j*k, self.q)) % self.q
                val = (val + term) % self.q
            y[k] = val
        return y

    def test_invertibility(self):
        """Test INTT(NTT(A)) == A (Cyclic)"""
        print("\nTesting Partial: NTT -> INTT Invertibility...")
        # Reduce scale if slow: N=2 (10 qubits) vs N=4 (20 qubits)
        n = 2
        input_vec = [1, 2] # N=2
        omega = 16 # Order 2 in Z17
        psi = 4
        
        ntt = QuantumNTT(self.backend, n, self.q, omega)
        
        regs = [QuantumRegister(5, f"r{i}") for i in range(n)]
        qc = QuantumCircuit(*regs)
        
        for i, val in enumerate(input_vec):
            for bit in range(5):
                if (val >> bit) & 1:
                    qc.x(regs[i][bit])
                    
        # Forward
        ntt_fwd = ntt.build_ntt_circuit(regs, None, inverse=False)
        qc.compose(ntt_fwd, inplace=True)
        
        # Inverse
        try:
            ntt_inv = ntt.build_ntt_circuit(regs, None, inverse=True)
        except TypeError:
            self.fail("QuantumNTT.build_ntt_circuit does not support 'inverse' parameter yet.")
            
        qc.compose(ntt_inv, inplace=True)
        
        qc.save_statevector()
        
        # Transpile for simulator
        t_qc = transpile(qc, self.simulator)
        job = self.simulator.run(t_qc)
        sv = np.asarray(job.result().get_statevector())
        
        nz = np.nonzero(sv)[0]
        self.assertEqual(len(nz), 1)
        idx = nz[0]
        
        out = []
        for i in range(n):
            val = (idx >> (5*i)) & 0x1F
            out.append(val)
        
        print(f"Recovered: {out}")
        self.assertEqual(out, input_vec)

    def test_n2_convolution(self):
        """Test A * B in Z_17[X]/(X^2+1) via Quantum NTT (N=2)"""
        print("\nTesting Full Convolution (N=2)...")
        a_vec = [1, 2]
        b_vec = [3, 4]
        # A(x) = 1 + 2x
        # B(x) = 3 + 4x
        # A*B = 3 + 4x + 6x + 8x^2 = 3 + 10x + 8(-1) = 3 - 8 + 10x = -5 + 10x = 12 + 10x
        expected = [12, 10]
        
        n = 2
        q = 17
        omega = 16 # Order 2
        psi = 4    # psi^2 = 16 = -1
        
        ntt = QuantumNTT(self.backend, n, q, omega)
        
        regs = [QuantumRegister(5, f"r{i}") for i in range(n)]
        qc = QuantumCircuit(*regs)
        
        # 1. Encode A
        for i, val in enumerate(a_vec):
            for bit in range(5):
                if (val >> bit) & 1:
                    qc.x(regs[i][bit])

        # 2. Pre-process A (Psi map)
        for i in range(n):
            factor = pow(psi, i, q)
            self.backend.mul_const_mod(qc, regs[i], factor, None)
            
        # 3. NTT A
        qc.compose(ntt.build_ntt_circuit(regs, None, inverse=False), inplace=True)
        
        # 4. Process B (Classical)
        b_pre = [(b_vec[i] * pow(psi, i, q)) % q for i in range(n)]
        b_hat = self.classical_dft(b_pre, omega)
        print(f"B_hat (Classical): {b_hat}")
        
        # 5. Pointwise Mul
        for i in range(n):
            self.backend.mul_const_mod(qc, regs[i], b_hat[i], None)
            
        # 6. INTT A
        qc.compose(ntt.build_ntt_circuit(regs, None, inverse=True), inplace=True)
        
        # 7. Post-process A
        for i in range(n):
            factor = pow(pow(psi, i, q), -1, q)
            self.backend.mul_const_mod(qc, regs[i], factor, None)
            
        qc.save_statevector()
        
        # Transpile for simulator
        t_qc = transpile(qc, self.simulator)
        job = self.simulator.run(t_qc)
        sv = np.asarray(job.result().get_statevector())
        
        # Decode state
        # State is 2*5 = 10 qubits. Easy.
        prob_dist = np.abs(sv)**2
        nz_indices = np.nonzero(prob_dist > 1e-5)[0] # Allow minor precision errors
        
        self.assertEqual(len(nz_indices), 1, f"Expected single state logic, got superposition on {nz_indices}")
        idx = nz_indices[0]
        
        out = []
        for i in range(n):
            val = (idx >> (5*i)) & 0x1F
            out.append(val)
        
        print(f"Recovered (N=2): {out}")
        self.assertEqual(out, expected)

    @unittest.skip("Too slow for local simulation (N=4 needs >20 qubits)")
    def test_full_negacyclic_convolution(self):
        """Test A * B in Z_17[X]/(X^4+1) via Quantum NTT"""
        print("\nTesting Full Convolution (Mini-Dilithium N=4)...")
        a_vec = [1, 2, 3, 4]
        b_vec = [5, 6, 7, 8]
        expected = [12, 15, 2, 9]
        
        regs = [QuantumRegister(5, f"r{i}") for i in range(4)]
        qc = QuantumCircuit(*regs)
        
        # 1. Encode A
        for i, val in enumerate(a_vec):
            for bit in range(5):
                if (val >> bit) & 1:
                    qc.x(regs[i][bit])

        # 2. Pre-process A (Psi map)
        # multiply reg[i] by psi^i
        for i in range(4):
            factor = pow(self.psi, i, self.q)
            self.backend.mul_const_mod(qc, regs[i], factor, None)
            
        # 3. NTT A
        qc.compose(self.ntt.build_ntt_circuit(regs, None, inverse=False), inplace=True)
        
        # 4. Process B (Classical)
        # Pre-process B
        b_pre = [(b_vec[i] * pow(self.psi, i, self.q)) % self.q for i in range(4)]
        # NTT B
        b_hat = self.classical_dft(b_pre, self.omega)
        print(f"B_hat (Classical): {b_hat}")
        
        # 5. Pointwise Mul (A = A * B_hat)
        for i in range(4):
            self.backend.mul_const_mod(qc, regs[i], b_hat[i], None)
            
        # 6. INTT A
        qc.compose(self.ntt.build_ntt_circuit(regs, None, inverse=True), inplace=True)
        
        # 7. Post-process A (Psi inverse map)
        # multiply reg[i] by psi^-i
        for i in range(4):
            factor = pow(pow(self.psi, i, self.q), -1, self.q)
            self.backend.mul_const_mod(qc, regs[i], factor, None)
            
        qc.save_statevector()
        
        basis_gates = self.simulator.configuration().basis_gates
        if 'unitary' not in basis_gates: basis_gates.append('unitary')
        
        t_qc = transpile(qc, self.simulator, basis_gates=basis_gates)
        job = self.simulator.run(t_qc)
        sv = np.asarray(job.result().get_statevector())
        
        nz = np.nonzero(sv)[0]
        self.assertEqual(len(nz), 1)
        idx = nz[0]
        
        out = []
        for i in range(4):
            val = (idx >> (5*i)) & 0x1F
            out.append(val)
        
        print(f"Convolution Result: {out}")
        self.assertEqual(out, expected)

if __name__ == '__main__':
    unittest.main()
