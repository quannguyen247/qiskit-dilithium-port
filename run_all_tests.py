import sys
import os
import subprocess

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Define files to run
files = [
    "dilithium-qiskit-port/tests/test_adders.py",
    "dilithium-qiskit-port/tests/test_mult_mod7.py",
    "dilithium-qiskit-port/tests/test_poly_add.py",
    # "dilithium-qiskit-port/tests/test_poly_mul.py", # Skipping old polynomial multiplication test
    "dilithium-qiskit-port/tests/test_ntt.py",
    "dilithium-qiskit-port/tests/test_ntt_17.py",
    "dilithium-qiskit-port/tests/test_poly_mul_17.py"
]

print("=== Running All Tests ===\n")
for f in files:
    print(f"--- Running {f} ---")
    file_path = os.path.join(os.path.dirname(__file__), f)
    # Use sys.executable to ensure we use the same Python environment
    result = subprocess.run([sys.executable, file_path], capture_output=True, text=True)
    
    # Print output
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
        
    if result.returncode != 0:
        print(f"FAILED: {f}")
    else:
        print(f"PASSED: {f}")
    print("\n" + "="*30 + "\n")
