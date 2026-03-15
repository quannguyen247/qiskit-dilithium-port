from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate
import numpy as np
from .modular_generic import ModularBackend

class Modular17(ModularBackend):
    """
    Implementation of modular arithmetic for q = 17 (5 bits).
    Supports Add, Sub, Mul_Const via cached unitaries.
    """
    def __init__(self):
        super().__init__(17)
        self.num_bits = 5
        self._cache = {}

    def _get_op_gate(self, op_type, param=None):
        """Builds and caches unitary gate for operations."""
        key = (op_type, param)
        if key in self._cache:
            return self._cache[key]
            
        dim = 2**self.num_bits
        size = 2**(2*self.num_bits) if op_type in ['add', 'sub'] else 2**self.num_bits
        
        matrix = np.eye(size, dtype=complex)
        
        if op_type == 'add':
            # Target b += a
            for i in range(size):
                b = i & 0x1F # Target (lower bits in index)
                a = (i >> 5) & 0x1F # Source (upper bits)
                if a < 17 and b < 17:
                    res = (b + a) % 17
                    if res != b:
                        matrix[i, i] = 0
                        target_idx = (a << 5) | res
                        matrix[target_idx, i] = 1
                        
        elif op_type == 'sub':
            # Target b -= a
            for i in range(size):
                b = i & 0x1F
                a = (i >> 5) & 0x1F
                if a < 17 and b < 17:
                    res = (b - a) % 17
                    if res != b:
                        matrix[i, i] = 0
                        target_idx = (a << 5) | res
                        matrix[target_idx, i] = 1
                        
        elif op_type == 'mul':
            const = param % 17
            for i in range(size):
                a = i
                if a < 17:
                    res = (a * const) % 17
                    if res != a:
                        matrix[i, i] = 0
                        matrix[res, i] = 1
        
        try:
            lbl = f"{op_type}_{param}" if param is not None else op_type
            gate = UnitaryGate(matrix, label=lbl, check_input=False)
        except TypeError:
            gate = UnitaryGate(matrix, label=lbl)
            
        self._cache[key] = gate
        return gate

    def add_mod(self, qc, reg_a, reg_b, aux):
        """Computes |a>|b> -> |a>|b+a>"""
        gate = self._get_op_gate('add')
        qc.append(gate, list(reg_b) + list(reg_a))

    def sub_mod(self, qc, reg_a, reg_b, aux):
        """Computes |a>|b> -> |a>|b-a>"""
        gate = self._get_op_gate('sub')
        qc.append(gate, list(reg_b) + list(reg_a))

    def mul_const_mod(self, qc, reg_a, constant, aux, reg_out=None):
        """Computes |a> -> |a*const>"""
        val = constant % 17
        if val == 1: return
        gate = self._get_op_gate('mul', val)
        qc.append(gate, list(reg_a))
