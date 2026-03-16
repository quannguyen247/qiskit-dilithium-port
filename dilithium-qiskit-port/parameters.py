import numpy as np
import platform
import subprocess
import qiskit

class DilithiumConfig:
    """
    Configuration for Quantum Dilithium Simulation (Proof of Concept).
    
    This class holds all parameters that affect the simulation:
    - N: Ring Dimension (degree of polynomial)
    - q: Modulus
    - omega: N-th root of unity in Z_q (Cyclic)
    - psi: 2N-th root of unity (Negacyclic)
    - matrix_L/K: Dilithium Matrix dimensions
    - backend_name: Simulator to use ('aer_simulator', 'statevector_simulator', etc.)
    - qubits_per_coeff: Number of qubits to represent integers mod q.
    """
    
    def __init__(self, name="Default"):
        self.name = name
        
        # --- Mathematical Parameters ---
        # N: The number of coefficients in our polynomial. 
        # Example: N=2 means polynomials look like a + bx.
        # This parameter directly impacts simulation speed (exponentially).
        self.N = 2  
        
        # q: The modulus for coefficients. All math is done modulo q.
        # We use q=17 because it fits in 5 qubits and supports standard NTT.
        self.q = 17 
        
        # omega: The N-th root of unity in Z_q. 
        # Required for the Number Theoretic Transform (NTT), similar to FFT.
        # Must satisfy: omega^N = 1 mod q.
        self.omega = 16 
        
        # psi: The 2N-th root of unity. 
        # Used for the Negacyclic NTT, which handles X^N + 1 polynomial multiplication.
        # Must satisfy: psi^N = -1 mod q.
        self.psi = 4 
        
        # k_bits: Number of qubits needed to store one coefficient.
        # Calculated as ceil(log2(q)). For q=17 (10001 in binary), we need 5 bits.
        self.k_bits = 5  
        
        # --- Simulator Configuration ---
        # backend_name: Which Qiskit simulator backend to use.
        # 'aer_simulator' is the most robust general-purpose simulator.
        self.backend_name = 'aer_simulator'
        
        # backend_method: The simulation technique.
        # 'statevector' computes the exact quantum state vector (2^n complex numbers).
        # This is very fast for small N (N<=4) but memory intensive for large N.
        self.backend_method = 'statevector' 
        
        # shots: Number of times to run the circuit if not using statevector mode.
        # More shots = better statistical accuracy but slower execution.
        self.shots = 1024 
        
        # --- Protocol Parameters ---
        # matrix_K: The height of the matrix A in the public key.
        # Increasing K makes the lattice problem harder (more security).
        self.matrix_K = 2 
        
        # matrix_L: The width of the matrix A in the public key.
        # Increasing L also increases security and signature size.
        self.matrix_L = 2
        
    def estimate_qubits(self):
        """Estimate active qubits for one polynomial convolution op"""
        # We need qubits for:
        # 1. Input Polynomial A (N * k_bits)
        # 2. Input/Output Polynomial B (Classical side, but mapped to qubits)
        # 3. Auxiliary qubits for the adder circuits (~3 extra)
        return self.N * self.k_bits + 3

    @classmethod
    def Micro(cls):
        """
        Micro-Dilithium (N=2, q=17) Configuration.
        Suitable for fast verification on a standard laptop.
        Uses approximately 13 Qubits per operation.
        """
        cfg = cls("Micro (N=2)")
        
        # Set minimal polynomial degree for speed
        cfg.N = 2
        
        # Standard modulus
        cfg.q = 17
        
        # Corresponding root of unity: 16^2 = 256 = 1 mod 17
        cfg.omega = 16 
        
        # Corresponding negacyclic root: 4^2 = 16 = -1 mod 17
        cfg.psi = 4    
        
        # Bits required for q=17
        cfg.k_bits = 5
        return cfg

    @classmethod
    def Mini(cls):
        """
        Mini-Dilithium (N=4, q=17) Configuration.
        WARNING: Slower simulation (>20 Qubits).
        Only run this if you have a powerful machine or time to wait.
        """
        cfg = cls("Mini (N=4)")
        
        # Increase polynomial degree
        cfg.N = 4
        
        # Standard modulus
        cfg.q = 17
        
        # Root of unity changes with N: 4^4 = 256 = 1 mod 17
        cfg.omega = 4  
        
        # Negacyclic root changes with N: 2^4 = 16 = -1 mod 17
        cfg.psi = 2    
        
        # Bits required remains the same
        cfg.k_bits = 5
        return cfg

    def __str__(self):
        # Format a readable string description of the current config
        return (f"Configuration: {self.name}\n"
                f"  - N={self.N}, q={self.q}\n"
                f"  - Bits/Coeff: {self.k_bits}\n"
                f"  - Roots: omega={self.omega}, psi={self.psi}\n"
                f"  - Simulator: {self.backend_name} ({self.backend_method})")


# --- GLOBAL CONFIGURATION INSTANCE ---
# This variable controls the settings for the entire project.
# To switch to N=4 mode, change .Micro() to .Mini() below.
CURRENT_CONFIG = DilithiumConfig.Micro()


def get_cpu_info():
    """
    Robust CPU Info Retrieval (Cross-Platform).
    Attempts to get the CPU model name using OS-specific commands.
    """
    try:
        # Check if running on Windows
        if platform.system() == "Windows":
            # Execute wmic command to get CPU name
            cmd = "wmic cpu get name"
            # Suppress stderr (e.g., if wmic is missing or permission denied)
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)
            # Parse output lines
            lines = output.decode().strip().split('\n')
            if len(lines) > 1:
                return lines[1].strip()
    except Exception:
        pass # Fail gracefully if command fails
        
    # Fallback to standard python platform info
    return platform.processor() or "Unknown Processor"
