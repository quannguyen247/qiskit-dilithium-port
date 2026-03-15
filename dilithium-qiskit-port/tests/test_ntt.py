import unittest
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator
import sys
import os

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from arithmetic.ntt import QuantumNTT
from arithmetic.modular_5 import Modular5

class TestNTTArchitecture(unittest.TestCase):
    def setUp(self):
        self.simulator = AerSimulator()
        
    def test_ntt_4point_mod5(self):
        """
        Test 4-point NTT with q=5.
        Roots of unity: 
        omega = 2.
        Input vector: [1, 2, 0, 0]
        NTT Output:
        y_k = sum(x_j * w^jk)
        y_0 = 3
        y_1 = 0
        y_2 = 4
        y_3 = 2
        Expected: [3, 0, 4, 2]
        """
        N = 4
        q = 5
        omega = 2
        
        backend = Modular5()
        ntt = QuantumNTT(backend, N, q, omega)
        
        # Registers: 4 registers of 3 bits each
        # We MUST ensure the register list matches exactly what we init
        regs = []
        for i in range(N):
            regs.append(QuantumRegister(3, f"a_{i}"))
        
        aux = QuantumRegister(1, "aux")
        
        # Main Circuit
        qc = QuantumCircuit(*regs, aux)
        
        # Initialize Input: [1, 2, 0, 0]
        # Reg 0 (a_0) = 1 (001)
        qc.x(regs[0][0])
        # Reg 1 (a_1) = 2 (010)
        qc.x(regs[1][1])
        
        # Build NTT Circuit (In-Place)
        # The design in ntt.py is: build_ntt_circuit returns a QC.
        ntt_circuit = ntt.build_ntt_circuit(regs, [aux])
        
        # Compose instructions
        # qc.compose(ntt_circuit, inplace=True) 
        # Note: Using compose inplace is safer than append if register objects match
        qc.compose(ntt_circuit, inplace=True)
        
        # Measure
        cr = ClassicalRegister(N * 3, 'c')
        qc.add_register(cr)
        
        for i in range(N):
            # Measure 3 bits of reg[i] -> to specific Classical bits
            # Map reg[i][0] -> cr[i*3], etc.
            qc.measure(regs[i], cr[i*3 : (i+1)*3])
            
        # Run
        result = self.simulator.run(qc, shots=1).result()
        counts = result.get_counts()
        print(f"NTT Output Counts: {counts}") 
        
        # Parse result
        # Qiskit result is one string "bits" (MSB to LSB).
        # Our CR is c[0]..c[11].
        # String is c[11]...c[0].
        # Let's extract values for y0, y1, y2, y3.
        # y0 corresponds to regs[0] -> cr[0..2] -> bits c2 c1 c0
        
        # Let's get the string
        if isinstance(counts, dict):
            bitstring = list(counts.keys())[0].replace(" ", "")
        else:
            bitstring = counts # Should be dict
            
        # Reverse to get LSB at index 0 (so index 0 is c0)
        bitstring = bitstring[::-1]
        
        results = []
        for i in range(N):
            # Chunk for y_i
            start = i * 3
            end = (i + 1) * 3
            chunk = bitstring[start:end]
            # Convert binary string (LSB at index 0 of chunk) to int
            val = 0
            for b_idx, char in enumerate(chunk):
                if char == '1':
                    val += (1 << b_idx)
            results.append(val)
            
        # Check against Expected: [3, 0, 4, 2]
        print(f"Parsed Integers: {results}")
        self.assertEqual(results, [3, 0, 4, 2])

if __name__ == '__main__':
    unittest.main()
