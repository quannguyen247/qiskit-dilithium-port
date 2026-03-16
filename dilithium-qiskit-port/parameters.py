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
        # Increasing N increases qubit usage linearly: Qubits ~ k * N + C 
        
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
        # 'statevector': Exact, fast for small N (N<=2), consumes RAM exponentially.
        # 'matrix_product_state': Better for larger N (N>=4), manages entanglement efficiently.
        self.backend_method = 'matrix_product_state' 
        
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
        
        # =================================================================
        # [USER CONFIG]: SIMULATOR QUBIT SETTINGS
        # =================================================================
        # 1 = AUTO (Automatically use the minimal required qubits, e.g. 13 or 23)
        # 0 = CUSTOM (Force a fixed total qubit count for load-testing)
        self.use_auto_qubits = 0
        
        # [CUSTOMIZE HERE]: Target total qubit count when use_auto_qubits = 0
        # Example: set to 30 to force simulation with 30 qubits
        self.custom_qubit_count = 10
        # =================================================================
        
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

    @classmethod
    def Standard_Dilithium2(cls):
        """
        STANDARD DILITHIUM-2 (Reference Configuration - DO NOT RUN)
        N=256, q=8380417, ~6,000 Qubits.
        Impossible to simulate on classical hardware.
        """
        cfg = cls("Standard Dilithium-2")
        cfg.N = 256
        cfg.q = 8380417
        cfg.omega = 1753 
        cfg.psi = 0 # Not calculated
        cfg.k_bits = 23 # 23 bits per coeff
        cfg.matrix_K = 4
        cfg.matrix_L = 4
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
# To switch configuration, commented/uncomment the lines below:

# OPTION 1: TOY DILITHIUM (Fast, Recommended for Simulator)
CURRENT_CONFIG = DilithiumConfig.Micro()

# OPTION 2: MINI DILITHIUM (Slow, only for powerful machines)
# CURRENT_CONFIG = DilithiumConfig.Mini()

# OPTION 3: STANDARD DILITHIUM (Reference Only - DO NOT RUN)
# CURRENT_CONFIG = DilithiumConfig.Standard_Dilithium2()


def get_cpu_info():
    """
    Robust CPU Info Retrieval (Cross-Platform).
    """
    try:
        # 1. Windows Registry (Most reliable for commercial name)
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            model = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            return model.strip()
    except Exception:
        pass
        
    try:
        # 2. Linux / macOS (sysctl or /proc/cpuinfo)
        if platform.system() == "Linux":
             with open("/proc/cpuinfo", "r") as f:
                 for line in f:
                     if "model name" in line:
                         return line.split(":")[1].strip()
        elif platform.system() == "Darwin":
            return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
    except Exception:
        pass
        
    # 3. Fallback
    return platform.processor() or "Unknown Processor"