
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate
import numpy as np
from .modular_generic import ModularBackend

class Modular5(ModularBackend):
    """
    A concrete implementation of ModularBackend for q=5 (3 bits).
    q=5 is the smallest prime satisfying q = 1 mod 4.
    It supports 4-point NTT.
    Roots of unity order 4 in Z_5: 2 and 3.
    (2^1=2, 2^2=4, 2^3=8=3, 2^4=16=1)
    """
    def __init__(self):
        super().__init__(q=5)
        self.num_bits = 3 # 0..4 fits in 3 bits
        self.dim = 2**self.num_bits # 8

    def add_mod(self, qc, reg_a, reg_b, aux):
        """
        Computes |a>|b> -> |a>|(a+b)%5>
        """
        # Create explicit matrix for Add Mod 5
        # Total size 2^(3+3) = 64
        size = 2**(2*self.num_bits)
        matrix = np.zeros((size, size), dtype=complex)
        
        # Basis states: |HighBits_b>|LowBits_a> -> Incorrect. Qiskit ordering is q_n ... q_0.
        # But wait, qc.append(gate, list(reg_a) + list(reg_b))
        # This implies reg_a is lower index qubits, reg_b is upper index qubits IF we treat system as |reg_b>|reg_a> ? No.
        # Qiskit default Little Endian for statevector display, but for matrix input/output:
        # Index i -> bit sequence.
        # If we append [q_a0, q_a1, q_a2, q_b0, q_b1, q_b2].
        # The index i corresponds to q_b2...q_b0 q_a2...q_a0. (Order: Last qubit is MSB).
        # So b is high bits, a is low bits.
        
        for idx in range(size):
            # Extract a and b from index
            # a is lower 3 bits, b is upper 3 bits
            a = idx & 0x7
            b = (idx >> 3) & 0x7
            
            new_a = a
            new_b = b
            
            # Logic: only if valid inputs
            # Although in quantum, invalid inputs (5,6,7) must map somewhere unitary.
            # Identity map for them.
            if a < 5 and b < 5:
                new_b = (a + b) % 5
            
            # Reconstruct index
            new_idx = (new_b << 3) | new_a
            matrix[new_idx, idx] = 1.0
            
        gate = UnitaryGate(matrix, label="add_mod5")
        qc.append(gate, list(reg_a) + list(reg_b))

    def sub_mod(self, qc, reg_a, reg_b, aux):
        """
        Computes |a>|b> -> |a>|(a-b)%5>
        Note: The interface calls this with (target, source).
        So we want: target = target - source.
        """
        size = 2**(2*self.num_bits)
        matrix = np.zeros((size, size), dtype=complex)
        
        for idx in range(size):
            # a is lower 3 bits (target if passed first in list?), b is upper.
            # In call: append(gate, list(reg_a)+list(reg_b)).
            # So reg_a is low bits, reg_b is high bits.
            # But the method is likely called as sub_mod(qc, target, source).
            # So reg_a is target, reg_b is source.
            
            target = idx & 0x7 # reg_a
            source = (idx >> 3) & 0x7 # reg_b
            
            new_t = target
            new_s = source
            
            if target < 5 and source < 5:
                # Target = Target - Source
                val = (target - source) % 5
                new_t = val
                
            new_idx = (new_s << 3) | new_t
            matrix[new_idx, idx] = 1.0

        gate = UnitaryGate(matrix, label="sub_mod5")
        qc.append(gate, list(reg_a) + list(reg_b))
        
    def mul_const_mod(self, qc, reg_a, const, aux, reg_out=None):
        """
        |a> -> |(a*const)%5>
        In-place multiplication. Only valid if gcd(const, 5) = 1.
        """
        size = 2**self.num_bits # 8
        matrix = np.zeros((size, size), dtype=complex)
        
        for idx in range(size):
            a = idx
            new_a = a
            
            if a < 5:
                new_a = (a * const) % 5
            
            matrix[new_a, idx] = 1.0
            
        gate = UnitaryGate(matrix, label=f"mul_{const}")
        qc.append(gate, list(reg_a))
        
    def sub_mod_from(self, qc, target, source, aux):
         """Redirect to sub_mod for now, assumes consistent interface"""
         self.sub_mod(qc, target, source, aux)

