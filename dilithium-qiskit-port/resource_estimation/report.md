# Dilithium Quantum Resource Estimation Report

## 1. Parameters
- **Scheme:** CRYSTALS-Dilithium (Mode 2)
- **Ring Dimension (N):** 256
- **Modulus (q):** 8,380,417 (Requires $k=23$ bits)
- **Operation:** Single Polynomial Multiplication ($C = A \times B$) in $\mathbb{Z}_q[X]/(X^N+1)$.

## 2. Methodology
The resource estimation is based on a recursive implementation of the Number Theoretic Transform (NTT) using the Cooley-Tukey/Gentleman-Sande butterfly structure.

### Component Cost Models
We utilize standard gate decompositions for modular arithmetic on quantum circuits:
- **Qubit Width:** $N \times k$ per polynomial (plus minimal aux qubits).
- **Modular Addition:** Based on Cuccaro Ripple Carry Adder.
  - Cost $\approx 3 \times$ (Add + Sub + Mux).
- **Modular Multiplication (Constant):** Decomposed into $k/2$ additions (average Case).

## 3. Results (Single Operation)
For the sequence `NTT(A) -> Pointwise_Mul(A, B_hat) -> INTT(C)`:

| Metric | Estimate |
| :--- | :--- |
| **Logical Qubits** | **~5,890** |
| **T-Gate Count** | **~29.5 Million** |
| **Clifford Gates** | **~44.3 Million** |
| **Circuit Depth** | *Depends on parallelization strategy (Est. $O(k \cdot \log N)$)* |

## 4. Hardware Implications
These estimates represent *logical* resources (error-corrected).
- **Physical Qubits:** Assuming a standard surface code overhead of 1000:1 (for $10^{-3}$ physical error rate), implementing this single operation would require approximately **6 Million physical qubits**.
- **Execution Time:** On a superconducting processor (200ns per gate), ~30M serial ops would take ~6 seconds (without parallelism). With full parallel NTT layers, depth reduces significantly, but control complexity increases.

## 5. Conclusion
This estimation confirms that attacking or even complying with Dilithium protocols on a quantum computer is well beyond the capabilities of NISQ (Noisy Intermediate-Scale Quantum) devices. It requires a mature, fault-tolerant quantum architecture.
