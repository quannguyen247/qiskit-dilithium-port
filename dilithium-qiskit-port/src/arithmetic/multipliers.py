# Module 3: Quantum Multipliers
# Implements a * b mod q

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
import sys
import os

# Adjust path for import if run directly
if __package__ is None or __package__ == '':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from arithmetic.modular import ModularArithmetic
else:
    from .modular import ModularArithmetic

class QuantumMultiplier:
    """
    Implements multiplication operations.
    """
    
    @staticmethod
    def mul_integer_3bit(qc, reg_a, reg_b, reg_out, reg_aux_list):
        """
        Multiplies two 3-bit integers reg_a and reg_b.
        Result is stored in reg_out (must be 6 bits initialized to 0).
        reg_aux_list: Must provide at least 6 clean ancilla qubits.
        Using 6 ancilla allows fully reversible implementation without intermediate resets.
        """
        # Unwrap aux
        aux0 = reg_aux_list[0]
        aux1 = reg_aux_list[1]
        aux2 = reg_aux_list[2]
        aux3 = reg_aux_list[3]
        aux4 = reg_aux_list[4]
        aux5 = reg_aux_list[5]

        # 1. Partial Product 0 (b0 * A) -> reg_out[0..2]
        qc.ccx(reg_a[0], reg_b[0], reg_out[0])
        qc.ccx(reg_a[1], reg_b[0], reg_out[1])
        qc.ccx(reg_a[2], reg_b[0], reg_out[2])
        
        # 2. Partial Product 1 (b1 * A) -> Add to reg_out[1..3]
        
        # Bit 0 (out[1])
        qc.mcx([reg_a[0], reg_b[1], reg_out[1]], aux0)      # Carry(Bit0) -> aux0
        qc.ccx(reg_a[0], reg_b[1], reg_out[1])             # Sum(Bit0) -> out[1]
        
        # Bit 1 (out[2])
        qc.mcx([reg_a[1], reg_b[1], reg_out[2]], aux1)     # Carry(Bit1)_part1 -> aux1
        qc.mcx([reg_a[1], reg_b[1], aux0], aux1)           # Carry(Bit1)_part2 -> aux1
        qc.ccx(reg_out[2], aux0, aux1)                     # Carry(Bit1)_part3 -> aux1
        qc.ccx(reg_a[1], reg_b[1], reg_out[2])             # Sum(Bit1)_part1 -> out[2]
        qc.cx(aux0, reg_out[2])                            # Sum(Bit1)_part2 -> out[2]
        
        # Bit 2 (out[3])
        # Requires new clean aux for Carry(Bit2)
        # Input carry was aux1. Outputs to aux2.
        qc.mcx([reg_a[2], reg_b[1], reg_out[3]], aux2)     # Carry(Bit2)
        qc.mcx([reg_a[2], reg_b[1], aux1], aux2)
        qc.ccx(reg_out[3], aux1, aux2)
        qc.ccx(reg_a[2], reg_b[1], reg_out[3])
        qc.cx(aux1, reg_out[3])
        
        # Bit 3 (out[4]) - Final carry from PP1
        qc.cx(aux2, reg_out[4])
        
        # 3. Partial Product 2 (b2 * A) -> Add to reg_out[2..4]
        # Uses aux3, aux4, aux5
        
        # Bit 0 (out[2])
        qc.mcx([reg_a[0], reg_b[2], reg_out[2]], aux3)      # Carry -> aux3
        qc.ccx(reg_a[0], reg_b[2], reg_out[2])
        
        # Bit 1 (out[3])
        qc.mcx([reg_a[1], reg_b[2], reg_out[3]], aux4)      # Carry -> aux4
        qc.mcx([reg_a[1], reg_b[2], aux3], aux4)
        qc.ccx(reg_out[3], aux3, aux4)
        qc.ccx(reg_a[1], reg_b[2], reg_out[3])
        qc.cx(aux3, reg_out[3])
        
        # Bit 2 (out[4])
        qc.mcx([reg_a[2], reg_b[2], reg_out[4]], aux5)      # Carry -> aux5
        qc.mcx([reg_a[2], reg_b[2], aux4], aux5)
        qc.ccx(reg_out[4], aux4, aux5)
        qc.ccx(reg_a[2], reg_b[2], reg_out[4])
        qc.cx(aux4, reg_out[4])
        
        # Bit 3 (out[5]) - Final Carry
        qc.cx(aux5, reg_out[5])

    @staticmethod
    def mul_mod7(qc, reg_a, reg_b, reg_out, reg_scratch):
        """
        Computes (a * b) mod 7.
        reg_a: 3 bits
        reg_b: 3 bits
        reg_out: 3 bits (Result)
        reg_scratch: needs roughly 10 bits.
        """
        # [0..5] = Product (P) (6 bits)
        # [6,7] = aux from scratch
        # [8,9] = aux from scratch
        
        reg_product = [reg_scratch[0], reg_scratch[1], reg_scratch[2], reg_scratch[3], reg_scratch[4], reg_scratch[5]]
        
        # We need 6 aux qubits for mul_integer_3bit to avoid resets.
        # We have reg_scratch[6..9] (4 qubits) + reg_out (3 qubits)
        # Total 7 available.
        # Pass them as a list.
        reg_mul_aux = [
            reg_scratch[6], reg_scratch[7], reg_scratch[8], reg_scratch[9],
            reg_out[0], reg_out[1]
        ]
        
        # 1. Compute P = A * B
        QuantumMultiplier.mul_integer_3bit(qc, reg_a, reg_b, reg_product, reg_mul_aux)
        
        # 2. Split P into High and Low
        # P = High * 8 + Low = High + Low (mod 7)
        # Low = P[0..2]
        # High = P[3..5]
        
        # We want reg_out = (High + Low) mod 7.
        
        # Step A: Copy Low to reg_out
        qc.cx(reg_product[0], reg_out[0])
        qc.cx(reg_product[1], reg_out[1])
        qc.cx(reg_product[2], reg_out[2])
        
        # Step B: Add High to reg_out
        reg_high = [reg_product[3], reg_product[4], reg_product[5]]
        
        # We need 3 aux qubits for add_mod7.
        # We use reg_scratch[6], reg_scratch[7], reg_scratch[8]
        # This requires reg_scratch to have size at least 9.
        
        # Ensure we have enough scratch space
        reg_add_aux = [reg_scratch[6], reg_scratch[7], reg_scratch[8]]
        
        # We need a 4th bit for reg_out (overflow detection) to pass to add_mod7
        # We use reg_scratch[9] if available.
        # Assuming reg_scratch has size >= 10.
        reg_overflow = reg_scratch[9]
        
        # Extended output register: [out0, out1, out2, overflow]
        reg_out_extended = [reg_out[0], reg_out[1], reg_out[2], reg_overflow]

        ModularArithmetic.add_mod7(qc, reg_high, reg_out_extended, reg_add_aux)
        
        # Cleanup overflow bit (assumed 0 mod 7 handled by sub_q_if_greater)
        # We can leave it or uncompute if we know how.
        # It's an output bit of addition logic (reg_b[3]).
        pass
