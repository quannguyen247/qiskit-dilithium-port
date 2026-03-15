from qiskit import QuantumCircuit, QuantumRegister
import sys
import os

# Adjust path for import if needed (for direct running)
if __package__ is None or __package__ == '':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from arithmetic.modular import ModularArithmetic
    from arithmetic.multipliers import QuantumMultiplier
else:
    from ..arithmetic.modular import ModularArithmetic
    from ..arithmetic.multipliers import QuantumMultiplier

class QuantumPolynomial:
    """
    Represents a polynomial with N coefficients in the small field Z_7.
    """
    def __init__(self, name, num_coeffs=4, coeff_bits=3):
        self.num_coeffs = num_coeffs
        self.coeff_bits = coeff_bits
        self.name = name
        
        # Each coefficient needs:
        # A register. For Input A, it's 3 bits. For Accumulator B, it might be 4 bits.
        # To simplify, we make all registers 4 bits to be safe, or manage them externally.
        # But wait, input A is strictly mod 7 (3 bits). Accumulator needs 4 bits.
        # Let's define:
        # If this is an Accumulator Poly (Type B): 4 bits per coeff
        # If this is an Input Poly (Type A): 3 bits per coeff
        # For generality in this class, we allow configuring bits.
        self.registers = [QuantumRegister(coeff_bits, f"{name}_{i}") for i in range(num_coeffs)]
        
    def add_to_circuit(self, qc):
        """Adds all registers of this poly to the circuit"""
        for reg in self.registers:
            qc.add_register(reg)
            
    def set_values(self, qc, values):
        """
        Initialize coefficients with integer values.
        values: list of ints, e.g. [1, 6, 2, 0]
        """
        for i, val in enumerate(values):
            if i >= self.num_coeffs: break
            # Convert int to binary and apply X gates
            for bit in range(self.registers[i].size):
                if (val >> bit) & 1:
                    qc.x(self.registers[i][bit])

    @staticmethod
    def build_addition_circuit(poly_a, poly_b, val_a=None, val_b=None):
        """
        Builds a circuit that adds Poly A and Poly B.
        Result is stored in Poly B (accumulator).
        """
        if poly_a.num_coeffs != poly_b.num_coeffs:
            raise ValueError("Polynomials must have same number of coefficients")
        
        N = poly_a.num_coeffs
        
        qc = QuantumCircuit()
        poly_a.add_to_circuit(qc)
        poly_b.add_to_circuit(qc)
        
        # Aux registers for addition (needed for ModularArithmetic.add_mod7)
        # add_mod7 needs 3 aux qubits if input is 3/4 bits.
        reg_aux = QuantumRegister(3, "aux")
        qc.add_register(reg_aux)
        
        # Init values
        if val_a:
            poly_a.set_values(qc, val_a)
        if val_b:
            poly_b.set_values(qc, val_b)
            
        # Add coil-by-coil
        for i in range(N):
            ModularArithmetic.add_mod7(qc, poly_a.registers[i], poly_b.registers[i], reg_aux)
            
        # Measurement (Optional for testing)
        # We add classical output to see result of B
        cr = []
        for i in range(N):
            from qiskit import ClassicalRegister
            c_reg = ClassicalRegister(poly_b.coeff_bits, f"c_{i}")
            qc.add_register(c_reg)
            cr.append(c_reg)
            
        for i in range(N):
            qc.measure(poly_b.registers[i], cr[i])
            
        return qc

    @staticmethod
    def build_multiplication_circuit(poly_a, poly_b, val_a=None, val_b=None):
        """
        Builds a circuit that multiplies Poly A and Poly B (mod X^N + 1 mod q).
        This is a full O(N^2) schoolbook multiplication with negacyclic convolution.
        """
        if poly_a.num_coeffs != poly_b.num_coeffs:
            raise ValueError("Polynomials must have same number of coefficients")
        
        N = poly_a.num_coeffs
        
        # Create Circuit
        qc = QuantumCircuit()
        poly_a.add_to_circuit(qc)
        poly_b.add_to_circuit(qc)
        
        # Result Polynomial C
        # Must be 4 bits per coefficient to handle intermediate addition before reduction? 
        # ModularArithmetic.add_mod7 takes reg_b as 4 bits.
        poly_c = QuantumPolynomial("C", num_coeffs=N, coeff_bits=4) 
        poly_c.add_to_circuit(qc)
        
        # Shared Resources
        # We need a scratch register for the multiplication result (10 bits)
        reg_scratch_mul = QuantumRegister(10, "scratch_mul")
        qc.add_register(reg_scratch_mul)
        
        # We need a target register for the multiplication output (3 bits)
        # This will hold a_i * b_j
        reg_temp_prod = QuantumRegister(3, "temp_prod")
        qc.add_register(reg_temp_prod)
        
        # We need aux for addition (3 bits)
        reg_aux_add = QuantumRegister(3, "aux_add")
        qc.add_register(reg_aux_add)
        
        # --- INITIALIZATION ---
        if val_a:
            poly_a.set_values(qc, val_a)
        if val_b:
            poly_b.set_values(qc, val_b)
            
        # --- MULTIPLICATION LOGIC ---
        # c_k = sum_{i+j=k} a_i b_j - sum_{i+j=k+N} a_i b_j
        
        for k in range(N):
            # Compute c[k]
            # Accumulate terms
            for i in range(N):
                for j in range(N):
                    # Check if this pair contributes to term k
                    # Negacyclic: i+j = k OR i+j = k + N
                    
                    is_neg = False
                    if (i + j) == k:
                        is_neg = False
                    elif (i + j) == (k + N):
                        is_neg = True
                    else:
                        continue # Not contributing to k
                    
                    # 1. Compute Product: temp = a[i] * b[j]
                    # We use a helper function to wrap the static method into an instruction
                    # to make uncomputation easy via .inverse()
                    
                    # Create a sub-circuit for multiplication to easily invert it
                    # We can just append the instructions directly since we manually uncompute later?
                    # No, uncompute is reverse operations.
                    # Qiskit's QuantumCircuit.append() with an instruction is cleanest.
                    # But QuantumMultiplier.mul_mod7 takes `qc`.
                    # Let's just call it directly, then add inverse instructions?
                    # No, manual uncompute is error prone.
                    # Let's define specific gate.
                    
                    # Definition of Mul Gate
                    # Inputs: 3 (A), 3 (B), 3 (Out), 10 (Scratch)
                    # Total 19 qubits.
                    mul_gate = QuantumCircuit(19, name="mul_mod7")
                    QuantumMultiplier.mul_mod7(mul_gate, 
                                             mul_gate.qubits[0:3], 
                                             mul_gate.qubits[3:6], 
                                             mul_gate.qubits[6:9], 
                                             mul_gate.qubits[9:19])
                    mul_instr = mul_gate.to_instruction()
                    
                    # Apply Mul
                    qc.append(mul_instr, 
                              poly_a.registers[i][:] + 
                              poly_b.registers[j][:] + 
                              reg_temp_prod[:] + 
                              reg_scratch_mul[:]
                             )
                    
                    # 2. Check Negation
                    # If is_neg is True, we subtract.
                    # Subtraction mod 7 is Addition of (-x).
                    # -x mod 7 is bitwise NOT of x (if 0 is 0/7).
                    # Warning: We rely on add_mod7 handling 7 as 0. 
                    # If temp_prod is 0 (000), NOT is 111 (7).
                    # modular.add_mod7 handles 0-7 range inputs correctly? Check.
                    # Yes, ripple carry works for 3-bit. 7+x = x mod 8?
                    # Wait, 7+x mod 7 = x.
                    # But add_mod7 is a generic adder followed by reduction.
                    # 7 is handled as 7. Reduction subtracts 7 if >= 7.
                    # So 7+x -> subtracts 7 -> x. Correct.
                    # So bitwise NOT is valid negation.
                    
                    if is_neg:
                        qc.x(reg_temp_prod)
                        
                    # 3. Add to Accumulator C[k]
                    # mul_mod7 returns 3 bits. C[k] is 3 bits.
                    # But accumulator can overflow?
                    # No, add_mod7 calls sub_q_if_greater, so it keeps C[k] mod 7.
                    ModularArithmetic.add_mod7(qc, reg_temp_prod, poly_c.registers[k], reg_aux_add)
                    
                    # 4. Restore Negation (Symmetric)
                    if is_neg:
                        qc.x(reg_temp_prod)
                        
                    # 5. Uncompute Product
                    # IMPORTANT: When appending gate with qubit list, ensure list size matches gate size (19).
                    # mul_instr inputs: A(3) + B(3) + Out(3) + Scratch(10) = 19.
                    # Current list: a[i](3) + b[j](3) + temp_prod(3) + scratch_mul(10).
                    # Looks correct.
                    qc.append(mul_instr.inverse(), 
                              poly_a.registers[i][:] + 
                              poly_b.registers[j][:] + 
                              reg_temp_prod[:] + 
                              reg_scratch_mul[:]
                             )
                             
        # Add Classical Registers for Output
        # poly_c uses 4 bits per coefficient to accommodate potential carries during addition
        cr = []
        for i in range(N):
            from qiskit import ClassicalRegister
            c_reg = ClassicalRegister(4, f"c_{i}")
            qc.add_register(c_reg)
            cr.append(c_reg)
            
        # Measure
        for i in range(N):
            # Qubit count must match clbit count
            qc.measure(poly_c.registers[i], cr[i])
            
        return qc

