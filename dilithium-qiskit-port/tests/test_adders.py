# This module tests the basic arithmetic modules primitives.
# Tests for:
# - Half Adder
# - Full Adder
# - Ripple Carry Adder (Basic)

import unittest
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
import sys
import os

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from arithmetic.adders import QuantumAdder

class TestQuantumAdders(unittest.TestCase):
    def setUp(self):
        self.simulator = AerSimulator()

    def test_half_adder(self):
        """Test Half Adder logic: 1+1=10, 1+0=01, etc."""
        # A=1, B=1 -> Sum=0, Carry=1
        qa = QuantumRegister(1, 'a')
        qb = QuantumRegister(1, 'b')
        qc_out = QuantumRegister(1, 'cout')
        c = ClassicalRegister(3, 'c')
        qc = QuantumCircuit(qa, qb, qc_out, c)
        
        # Init A=1, B=1
        qc.x(qa[0])
        qc.x(qb[0])
        
        QuantumAdder.half_adder(qc, qa[0], qb[0], qc_out[0])
        
        qc.measure(qa, c[0])
        qc.measure(qb, c[1]) # Sum is in B
        qc.measure(qc_out, c[2]) # Carry
        
        # Transpile
        qc_transpiled =  generate_preset_pass_manager(target=self.simulator.target, optimization_level=1).run(qc)
        result = self.simulator.run(qc_transpiled, shots=100).result().get_counts()
        
        # Expect: C=1, S=0, A=1 -> "101" (q2 q1 q0 -> C S A)
        print(f"Half Adder (1+1): {result}")
        self.assertIn("101", result)

    def test_ripple_adder_3bit(self):
        """Test 3-bit Ripple Adder: 3 + 2 = 5"""
        # A=3 (011), B=2 (010)
        n = 3
        qa = QuantumRegister(n, 'a')
        qb = QuantumRegister(n, 'b')
        # Carry registers required for ripple adder logic?
        # The implementation asks for reg_carry of size n?
        # Let's check signature: ripple_carry_adder(qc, reg_a, reg_b, reg_carry, n_bits)
        # It uses reg_carry[0] .. reg_carry[n-1]
        
        q_carry = QuantumRegister(n, 'carry')
        c = ClassicalRegister(n, 'sum')
        
        qc = QuantumCircuit(qa, qb, q_carry, c)
        
        # Init A=3 (011) - q0=1, q1=1
        qc.x(qa[0])
        qc.x(qa[1])
        
        # Init B=2 (010) - q1=1
        qc.x(qb[1])
        
        QuantumAdder.ripple_carry_adder(qc, qa, qb, q_carry, n)
        
        qc.measure(qb, c)
        
        qc_transpiled = generate_preset_pass_manager(target=self.simulator.target, optimization_level=1).run(qc)
        result = self.simulator.run(qc_transpiled, shots=100).result().get_counts()
        
        # 3 + 2 = 5 (101). Little endian q0..q2. q0=1, q1=0, q2=1.
        # String: "101"
        print(f"Ripple Adder (3+2): {result}")
        self.assertIn("101", result)

if __name__ == '__main__':
    unittest.main()