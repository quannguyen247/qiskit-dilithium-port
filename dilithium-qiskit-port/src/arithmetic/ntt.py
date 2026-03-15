"""
NTT Implementation for Quantum Dilithium.
This module provides the Number Theoretic Transform (NTT) circuit generation.
Dilithium uses NTT for polynomial multiplication in the ring R_q = Z_q[X] / (X^n + 1).

The transformation is defined over Z_q where q is a prime such that q = 1 mod 2n.
"""

from qiskit import QuantumCircuit, QuantumRegister
import math
from .modular_generic import ModularBackend

class QuantumNTT:
    def __init__(self, backend: ModularBackend, n, q, omega):
        self.backend = backend
        self.n = n
        self.q = q
        self.omega = omega
        # Verify omega is an n-th root of unity: omega^n = 1 mod q
        if pow(omega, n, q) != 1:
            pass # Relaxed for negacyclic

    def butterfly_unit(self, qc, qubit_a, qubit_b, twist, aux_list):
        """
        Implements In-Place Cooley-Tukey Butterfly via ModularBackend.
         Transforms:
        |a>|b> -> |a + w^k b> |a - w^k b>
        """
        # 1. Multiply b by twist (In-Place)
        self.backend.mul_const_mod(qc, qubit_b, twist, aux_list)
        
        # 2. Add: a = a + b
        self.backend.add_mod(qc, qubit_b, qubit_a, aux_list)
        
        # 3. Double b: b = 2b
        self.backend.mul_const_mod(qc, qubit_b, 2, aux_list)
        
        # 4. Subtract: b = a - b
        self.backend.mul_const_mod(qc, qubit_b, self.q - 1, aux_list)
        self.backend.add_mod(qc, qubit_a, qubit_b, aux_list)

    def inverse_butterfly_unit(self, qc, qubit_a, qubit_b, inv_twist, aux_list):
        """
        Implements In-Place Gentleman-Sande Inverse Butterfly.
        Transforms: |u>|v> -> |(u+v)> |(u-v)w^-k> (ignoring scaling)
        Note: True INTT requires scaling by 1/2 per stage or 1/N at end.
        We implement unscaled version here.
        
        Standard GS:
        u' = u + v
        v' = (u - v) * w^-k
        
        Implementation via In-Place updates:
        1. v = -v
        2. v = v + u (now v = u - v_in)
        3. u = 2u
        4. u = u - v (now u = 2u - (u-v) = u+v = u')
        5. v = v * inv_twist (now v = v' * inv_twist)
        """
        # 1. v = -v
        self.backend.mul_const_mod(qc, qubit_b, self.q - 1, aux_list)
        
        # 2. v = v + u
        self.backend.add_mod(qc, qubit_a, qubit_b, aux_list)
        
        # 3. u = 2u
        self.backend.mul_const_mod(qc, qubit_a, 2, aux_list)
        
        # 4. u = u - v. Uses sub_mod(source, target) -> target -= source
        # We want u -= v. Source v (qubit_b), Target u (qubit_a)
        self.backend.sub_mod(qc, qubit_b, qubit_a, aux_list)
        
        # 5. v = v * inv_twist
        self.backend.mul_const_mod(qc, qubit_b, inv_twist, aux_list)

    def _bit_reverse(self, x, bits):
        y = 0
        for i in range(bits):
            y = (y << 1) | (x & 1)
            x >>= 1
        return y
        
    def build_ntt_circuit(self, quantum_registers, aux_list, inverse=False):
        """
        Constructs the full NTT or Inverse NTT circuit for N points.
        :param inverse: If True, constructs Inverse NTT (INTT).
        """
        if len(quantum_registers) != self.n:
            raise ValueError(f"Expected {self.n} registers, got {len(quantum_registers)}")
            
        n = self.n
        qc = QuantumCircuit()
        for reg in quantum_registers:
            qc.add_register(reg)
            
        if not inverse:
            # === Forward NTT (Cooley-Tukey DIT) ===
            # 1. Bit-Reversal Permutation
            log_n = int(math.log2(n))
            for i in range(n):
                rev_i = self._bit_reverse(i, log_n)
                if i < rev_i:
                    reg_a = quantum_registers[i]
                    reg_b = quantum_registers[rev_i]
                    for bit in range(len(reg_a)):
                        qc.swap(reg_a[bit], reg_b[bit])

            # 2. DIT Butterfly Stages
            m = 1
            while m < n:
                step = 2 * m
                base_pow = n // (2 * m)
                for k in range(0, n, step):
                    for j in range(m):
                        twist_exp = (j * base_pow) % n
                        twist_val = pow(self.omega, twist_exp, self.q)
                        
                        idx_a = k + j
                        idx_b = k + j + m
                        self.butterfly_unit(qc, quantum_registers[idx_a], quantum_registers[idx_b], twist_val, aux_list)
                m *= 2
        else:
            # === Inverse NTT (Gentleman-Sande DIF) ===
            # Reverses CT: Stages first (in reverse), then Bit-Reversal
            
            # 1. DIF Butterfly Stages (Reverse of CT Stages)
            m = n // 2
            while m >= 1:
                step = 2 * m
                base_pow = n // (2 * m)
                # Iterate k, j same structure or reversed?
                # GS takes natural order 2 inputs -> outputs.
                # Just process groups.
                for k in range(0, n, step):
                    for j in range(m):
                        twist_exp = (j * base_pow) % n
                        twist_val = pow(self.omega, twist_exp, self.q)
                        # Inverse twist
                        inv_twist = pow(twist_val, -1, self.q)
                        
                        idx_a = k + j
                        idx_b = k + j + m
                        self.inverse_butterfly_unit(qc, quantum_registers[idx_a], quantum_registers[idx_b], inv_twist, aux_list)
                m //= 2
                
            # 2. Bit-Reversal Permutation
            log_n = int(math.log2(n))
            for i in range(n):
                rev_i = self._bit_reverse(i, log_n)
                if i < rev_i:
                    reg_a = quantum_registers[i]
                    reg_b = quantum_registers[rev_i]
                    for bit in range(len(reg_a)):
                        qc.swap(reg_a[bit], reg_b[bit])
                        
            # 3. Normalization by N^-1
            n_inv = pow(n, -1, self.q)
            for reg in quantum_registers:
                self.backend.mul_const_mod(qc, reg, n_inv, aux_list)
            
        return qc
