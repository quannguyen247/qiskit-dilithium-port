# Small parameters for proof-of-concept quantum circuit implementation
# Fits within typical 20-30 qubit range for small operations

# Q = 7 (Requires 3 qubits per coefficient)
# N = 4 (Polynomial degree)
# Total qubits per polynomial = 4 * 3 = 12 qubits
# Binary addition of two polynomials = 24 qubits + ancilla ~ 28-30 qubits

Q_PARAM = 7 
N_PARAM = 4
K_PARAM = 2  # Matrix dimensions (2x2)
L_PARAM = 2
