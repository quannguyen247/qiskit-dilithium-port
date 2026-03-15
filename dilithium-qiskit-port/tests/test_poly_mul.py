from qiskit import transpile
from qiskit_aer import AerSimulator
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.polynomials.quantum_poly import QuantumPolynomial

def test_poly_mul():
    print("=== Testing Quantum Polynomial Multiplication ===")
    
    # 1. Setup Polynomials
    # Small N=2 for speed first time? No, let's try N=2 if class allows.
    # QuantumPoly defaults N=4. Let's make N=2 for test safety on simulator.
    # Input A: [1, 2]
    # Input B: [3, 1]
    # Modulo X^2 + 1 mod 7
    # Prod = (1 + 2x)*(3 + x) = 3 + x + 6x + 2x^2 = 3 + 7x + 2(-1) = 3 + 0 - 2 = 1
    # Result = [1, 0] ?
    # Wait: 1*3 = 3
    # x coeff: 1*1 + 2*3 = 1 + 6 = 7 = 0.
    # x^2 coeff: 2*1 = 2 -> becomes -2 (negacyclic wrapping of x^2 -> -1)
    # So const term = 3 - 2 = 1.
    # Coeffs: [1, 0]
    
    N_TEST = 2
    poly_a = QuantumPolynomial("A", num_coeffs=N_TEST, coeff_bits=3)
    poly_b = QuantumPolynomial("B", num_coeffs=N_TEST, coeff_bits=3)
    
    val_a = [1, 2]
    val_b = [3, 1]
    expected = [1, 0]
    
    print(f"N={N_TEST}")
    print(f"A: {val_a}")
    print(f"B: {val_b}")
    print(f"Expected: {expected}")
    
    # 2. Build Circuit
    qc = QuantumPolynomial.build_multiplication_circuit(poly_a, poly_b, val_a=val_a, val_b=val_b)
    
    # 3. Simulate
    # Use matrix_product_state for potentially manageable overhead with high qubit count if entanglement is low
    sim = AerSimulator(method='matrix_product_state') 
    # Must disable coupling map check because Aer default backend has limited qubits?
    # No, AerSimulator without backend arg should support max qubits.
    # The error suggests 'coupling_map' limit of 30.
    # We can pass coupling_map=None explicitly.
    # Note: Removed 'sim' from transpile arguments to avoid UserWarning about conflicting options.
    qc_transpiled = transpile(qc, coupling_map=None, basis_gates=['u', 'cx', 'ccx', 'measure', 'reset', 'x', 'h', 'swap'])
    result = sim.run(qc_transpiled, shots=10).result().get_counts()
    
    most_frequent = max(result, key=result.get)
    print(f"Raw: {most_frequent}")
    
    # Parse Result
    # Output registers added: c_0 (3 bits), c_1 (3 bits).
    # Last added is leftmost in string usually, but let's check order.
    # We added c_0 then c_1.
    # Qiskit print order is reversed logic of addition usually if classic regs.
    # String: "c_1 c_0"
    
    parts = most_frequent.split()
    if len(parts) == 1:
        # If no spaces, slice.
        # String length = N * 3 = 6.
        # "c1 c0"
        bits_c1 = most_frequent[0:3]
        bits_c0 = most_frequent[3:6]
        val_0 = int(bits_c0, 2)
        val_1 = int(bits_c1, 2)
        decoded = [val_0, val_1]
    else:
        # With spaces
        # "c1_bits c0_bits"
        decoded = [int(p, 2) for p in parts[::-1]]
        
    print(f"Decoded: {decoded}")
    assert decoded == expected, f"Expected {expected}, got {decoded}"
    print("SUCCESS")

if __name__ == "__main__":
    test_poly_mul()
