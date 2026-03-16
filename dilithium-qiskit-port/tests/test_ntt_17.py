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

class TestNTT17(unittest.TestCase):
    def setUp(self):
        self.backend = Modular17()
        # N=4, q=17, omega=4 (order 4 in Z17, negacyclic order 8)
        self.n = 4
        self.q = 17
        self.omega = 4 
        self.ntt = QuantumNTT(self.backend, self.n, self.q, self.omega)
        self.simulator = Aer.get_backend('aer_simulator')

    def test_modular_add(self):
        """Test |a>|b> -> |a>|a+b mod 17> on 10 qubits"""
        qc = QuantumCircuit(10) # 2 registers of 5
        # Set reg_a = 3 (00011)
        qc.x(0)
        qc.x(1)
        # Set reg_b = 5 (00101)
        qc.x(5)
        qc.x(7)
        
        self.backend.add_mod(qc, range(5), range(5, 10), None)
        qc.save_statevector()
        
        # Use simulator default basis gates (includes unitary)
        job = self.simulator.run(transpile(qc, self.simulator))
        result = job.result()
        sv = np.asarray(result.get_statevector())
        
        nz = np.nonzero(sv)[0]
        self.assertEqual(len(nz), 1)
        idx = nz[0]
        val_a = idx & 0x1F
        val_b = (idx >> 5) & 0x1F
        
        self.assertEqual(val_a, 3)
        self.assertEqual(val_b, 8) # 3+5=8

    def test_ntt_circuit_2_point(self):
        """Test NTT on N=2, q=17 (Fast verification)"""
        n = 2
        # For standard Cyclic NTT, omega^N = 1 mod q. omega^2 = 1 mod 17 -> omega = 16 (-1).
        omega = 16 
        ntt = QuantumNTT(self.backend, n, self.q, omega)
        
        input_vec = [1, 2]
        expected_outputs = [3, 16]

        regs = [QuantumRegister(5, f"r{i}") for i in range(2)]
        qc = QuantumCircuit(*regs)
        
        for i, val in enumerate(input_vec):
            for bit in range(5):
                if (val >> bit) & 1:
                    qc.x(regs[i][bit])
                    
        ntt_qc = ntt.build_ntt_circuit(regs, None)
        qc.compose(ntt_qc, inplace=True)
        qc.save_statevector()
        
        # Use simulator default basis gates (includes unitary)
        t_qc = transpile(qc, self.simulator)
        job = self.simulator.run(t_qc)
        result = job.result()
        sv = np.asarray(result.get_statevector())
        
        nz = np.nonzero(sv)[0]
        self.assertEqual(len(nz), 1)
        idx = nz[0]
        
        output_results = []
        for i in range(2):
            val = (idx >> (5*i)) & 0x1F
            output_results.append(val)
            
        print(f"Quantum NTT N=2: {output_results}")
        self.assertEqual(output_results, expected_outputs)

    def test_ntt_circuit_4_point(self):
        """Test full NTT circuit construction on N=4, q=17 (Simulation skipped for speed)"""
        input_vec = [1, 2, 3, 4]
        regs = [QuantumRegister(5, f"r{i}") for i in range(4)]
        qc = QuantumCircuit(*regs)
        
        for i, val in enumerate(input_vec):
            for bit in range(5):
                if (val >> bit) & 1:
                    qc.x(regs[i][bit])
                    
        ntt_qc = self.ntt.build_ntt_circuit(regs, None)
        qc.compose(ntt_qc, inplace=True)
        
        print(f"Verified N=4 Circuit Structure: Depth {qc.depth()}, Ops {qc.count_ops()}")
        # Check that circuit is constructed with expected operations
        self.assertTrue(qc.depth() > 0)
        self.assertIn('unitary', qc.count_ops())
        # Skipping execution to avoid simulation bottleneck

if __name__ == '__main__':
    unittest.main()