from qiskit import transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.polynomials.quantum_poly import QuantumPolynomial

def test_poly_addition():
    print("=== Testing Quantum Polynomial Addition ===")
    
    # Qubit Optimization: Reduced num_coeffs from 4 to 3 to fit < 30 qubits.
    # Cost: A(3*3) + B(3*4) + Aux(3) = 9 + 12 + 3 = 24 Qubits. Safety margin!
    
    # 1. Setup Polynomials
    poly_a = QuantumPolynomial("A", num_coeffs=3, coeff_bits=3)
    poly_b = QuantumPolynomial("B", num_coeffs=3, coeff_bits=4)
    
    # 2. Define Inputs (Last coeff 3 dropped)
    val_a = [1, 2, 6]
    val_b = [3, 5, 2]
    
    # Expected: (A + B) mod 7
    # 1+3=4
    # 2+5=7 -> 0
    # 6+2=8 -> 1
    # Result: [4, 0, 1]
    expected = [4, 0, 1]
    
    print(f"Input A: {val_a}")
    print(f"Input B: {val_b}")
    print(f"Expect : {expected}")
    
    # 3. Build Circuit with INITIAL VALUES
    # Passing values here ensures X gates are applied BEFORE measurement
    qc = QuantumPolynomial.build_addition_circuit(poly_a, poly_b, val_a=val_a, val_b=val_b)
    
    # 4. (Deprecated) Initialize State manually after build would be wrong if build includes measure.
    # poly_a.set_values(qc, val_a) <- This was the bug causing [0,0,0]
    
    # 5. Run Simulation
    print("Simulating...")
    # Use standard BasicSimulator if Aer is heavy, but Aer is fine.
    sim = AerSimulator()
    print("Transpiling with Pass Manager (Level 1)...")
    pm = generate_preset_pass_manager(backend=sim, optimization_level=1)
    qc_transpiled = pm.run(qc)
    print("Running simulation...")
    result = sim.run(qc_transpiled, shots=10).result().get_counts()
    
    # 6. Parse Result
    most_frequent = max(result, key=result.get)
    print(f"Raw Result (Bitstring): {most_frequent}")
    
    # Parsing: Qiskit returns "Zn ... Z0" where Zi is bitstring of register i.
    # The order of classical registers added determines the output string structure.
    # We added cr[0], cr[1], cr[2]...
    # So the string is "bits_of_cr2 bits_of_cr1 bits_of_cr0" (space separated usually)
    # The split() handles spaces.
    
    # Note: If no spaces in raw string (depends on qiskit version/backend), we might need fixed width slicing.
    # Qiskit Aer usually returns clean bitstring "1110 0001 ..." if `memory=True` or registers separate.
    # But `get_counts` returns one fused string "000100000100".
    
    # Let's inspect length.
    # Total bits = 3 coeffs * 4 bits = 12 bits.
    parts = []
    # If string has spaces:
    if ' ' in most_frequent:
        parts = most_frequent.split()
    else:
        # Slice manually. Each register is 4 bits.
        # String is reversed register order: C2 C1 C0.
        # Total length 12. 
        # C2: chars [0:4] ? No, Qiskit prints MSB first. 
        # C2 is last added? 
        # Rule: "The last register added is the leftmost in the string".
        # We added reg 0, then 1, then 2.
        # So string is: "Reg2 Reg1 Reg0".
        stride = 4
        parts = [most_frequent[i:i+stride] for i in range(0, len(most_frequent), stride)]
        # parts = [Reg2, Reg1, Reg0]
    
    # We want [Reg0, Reg1, Reg2]. So reverse parts.
    decoded = [int(p, 2) for p in parts[::-1]]
    
    # Wait: The list order expected is [4, 0, 1].
    # Reg 0 should be 4. Reg 1 should be 0. Reg 2 should be 1.
    
    print(f"Decoded Poly: {decoded}")
    
    assert decoded == expected, f"Test Failed: {decoded} != {expected}"
    print("SUCCESS: Polynomial Addition Works!")

if __name__ == "__main__":
    test_poly_addition()
