# This module tests the mul_mod7 function in QuantumMultiplier.
import unittest
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
import sys
import os

# Adjust path to import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from arithmetic.multipliers import QuantumMultiplier

class TestQuantumMultiplier(unittest.TestCase):
    def setUp(self):
        self.simulator = AerSimulator()

    def test_mul_3bit_integer(self):
        """Test a simple 3-bit integer multiplication."""
        # A=2 (010), B=3 (011) -> Out=6 (000110)
        q_a = QuantumRegister(3, 'a')
        q_b = QuantumRegister(3, 'b')
        q_out = QuantumRegister(6, 'out')
        # mul_integer_3bit now requires 6 aux qubits (passed as list)
        q_aux = QuantumRegister(6, 'aux') 
        c = ClassicalRegister(6, 'c')
        
        # Create circuit
        qc = QuantumCircuit(q_a, q_b, q_out, q_aux, c)
        
        # Initialization
        # A=2 (binary 010): Set q_a[1]
        qc.x(q_a[1])
        # B=3 (binary 011): Set q_b[0], q_b[1]
        qc.x(q_b[0])
        qc.x(q_b[1])
        
        # Run 3-bit integer multiplication
        # Pass q_aux as a list of qubits
        QuantumMultiplier.mul_integer_3bit(qc, q_a, q_b, q_out, list(q_aux))
        
        # Measure output
        qc.measure(q_out, c)
        
        # Use generate_preset_pass_manager for transpilation
        pm = generate_preset_pass_manager(target=self.simulator.target, optimization_level=1)
        qc_transpiled = pm.run(qc)
        
        # Execute
        job = self.simulator.run(qc_transpiled, shots=100)
        result = job.result()
        counts = result.get_counts()
        
        # Expected: 6 -> 110 (binary). 
        # Qiskit bit ordering is q_n ... q_0.
        # So for 6 bits: 000110
        print(f"Mul Integer Counts: {counts}")
        self.assertIn("000110", counts)
        
    def test_mul_mod7(self):
        """Test 3 * 4 = 12 = 5 mod 7"""
        # A=3 (011), B=4 (100) -> Out=5 (101)
        q_a = QuantumRegister(3, 'a')
        q_b = QuantumRegister(3, 'b')
        q_out = QuantumRegister(3, 'out')
        # We need 10 scratch bits (6 product + 3 aux + 1 overflow)
        q_scratch = QuantumRegister(10, 'scratch') 
        c = ClassicalRegister(3, 'c')
        qc = QuantumCircuit(q_a, q_b, q_out, q_scratch, c)
        
        # Init A=3
        qc.x(q_a[0])
        qc.x(q_a[1])
        # Init B=4
        qc.x(q_b[2])
        
        QuantumMultiplier.mul_mod7(qc, q_a, q_b, q_out, q_scratch)
        
        qc.measure(q_out, c)
        
        # Use generate_preset_pass_manager
        pm = generate_preset_pass_manager(target=self.simulator.target, optimization_level=1)
        qc_transpiled = pm.run(qc)
        
        job = self.simulator.run(qc_transpiled, shots=100)
        result = job.result()
        counts = result.get_counts()
        
        # Expected: 5 -> 101.
        print(f"Mul Mod7 Counts: {counts}")
        self.assertIn("101", counts)

if __name__ == '__main__':
    unittest.main()
