# 🚀 Quantum Dilithium Cryptography: QUICK START
## ⚡ Quantum-Safe Authentication with Qiskit Simulation

### Requirements
- **Python** (v3.8+): https://python.org/
- **Qiskit** (`pip install qiskit qiskit-aer`): Quantum simulation
- **Board Client** (optional): Node.js client for LyCheeRVnano board

### Test in 1 Command

**Windows:**
```bash
run_test_dilithium.bat
```

**Linux/macOS:**
```bash
bash run_test_dilithium.sh
```

Expected result:
```
✅ AUTHENTICATION WORKFLOW COMPLETE!
TOTAL EXECUTION TIME: XXXX.XX µs
```

---

## 🔐 What Happens?

```
Stage 1: Receive Public Key
  └─ Server reads publickey.json from board
  └─ Verifies public key (A, t) data
  └─ ⏱️ Measures: Receive time (µs)

Stage 2: Create Challenge  
  └─ Server generates random challenge polynomial c
  └─ Packs as JSON: challenge.json
  └─ ⏱️ Measures: Challenge generation time (µs)

Stage 3: Verify Signature (QUANTUM!)
  └─ Server reads signature.json from board
  └─ Unpacks signature polynomial z
  └─ EXECUTES QUANTUM CIRCUITS:
     ├─ QuantumNTT on Qiskit simulator
     ├─ Modular arithmetic on ~13-23 qubits
     ├─ A*z computation via quantum polynomial multiplication
     └─ Verification: Check A*z - c*t == w
  └─ ⏱️ Measures: Quantum circuit execution time (µs, from AerSimulator)
  └─ Outputs: verification_result.json + timing metrics
```
---

## 📂 Files Exchange

**Directory**: `./data/`

| Stage | File | Direction | Format | Source |
|-------|------|-----------|--------|--------|
| 1 | `publickey.json` | Board → Server | JSON | Board KeyGen |
| 2 | `challenge.json` | Server → Board | JSON | Server Challenge |
| 3 | `signature.json` | Board → Server | JSON | Board Sign |
| 3 | `verification_result.json` | Server → Board | JSON | Server Verify |

---

## ⏱️ Timing Output

**Microseconds (µs) precision:**

```
Stage 1 - Receive Public Key:
[2026-04-02 14:30:45.123] ✅ Stage 1 Complete. Elapsed: 1234.56 µs

Stage 2 - Create Challenge:
[2026-04-02 14:30:46.257] ✅ Stage 2 Complete. Total elapsed: 3456.78 µs

Stage 3 - Verification:
Total Execution Time: 5234.12 µs (5.23 ms)

📊 Timing Summary:
  start → receive_complete:     1234.56 µs
  receive_complete → challenge: 2345.67 µs
  challenge → verified:         1654.89 µs
```

---

## 📁 Generated Files

All files in `./data/` (JSON format):

| File | Created by | Contains |
|------|-----------|----------|
| `publickey.json` | Board (Node.js) | A[0], A[1], t (JSON) |
| `challenge.json` | Server (Python) | Challenge ID, c (JSON) |
| `signature.json` | Board (Node.js) | z (signature) (JSON) |
| `verification_result.json` | Server (Python) | Verification result (JSON) |

---

## 🎯 3 Main Functions (with Quantum Verification)

### 1️⃣ Receive_Public_key (Python)
```python
pubkey_data = Receive_Public_key("./data/publickey.json")
# ✅ Reads public key JSON (A matrix, t public key)
# ✅ Starts microsecond-precision timer
# Output: "✅ Stage 1 Complete. Elapsed: XXXX.XX µs"
```

### 2️⃣ Create_challenge (Python)
```python
challenge_data = Create_challenge(pubkey_data, "./data/challenge.json")
# ✅ Generates random challenge polynomial c
# ✅ Packs as JSON protocol message
# Output: "✅ Stage 2 Complete. Total elapsed: XXXX.XX µs"
```

### 3️⃣ Verification (Python) - **RUNS QUANTUM CIRCUITS**
```python
is_valid = Verification(pubkey_data, challenge_data, "./data/signature.json")
# 🔬 QUANTUM EXECUTION via MiniDilithium:
#    ├─ Initialize Qiskit AerSimulator
#    ├─ Transform A to NTT domain (classical)
#    ├─ Call quantum_poly_mul() → Executes QuantumNTT circuit
#    ├─ Compute A*z on quantum hardware (simulated)
#    ├─ Verify: A*z - c*t == w (quantum result)
#    └─ Measure circuit execution time from AerSimulator
# 
# Output: "✅ VERIFICATION SUCCESSFUL!"
#         "Quantum Backend: Aer [statevector/matrix_product_state]"
#         "Total Execution Time: XXXX.XX µs"
```

---

## 🔧 How It Works

**This repo is a Python QUANTUM SERVER only.** It expects:

1. **publickey.json** → Placed by board client (KeyGen)
2. **Server generates** → challenge.json (Challenge)
3. **signature.json** → Placed by board client (Sign)
4. **Server returns** → verification_result.json (Verify using QUANTUM)
4. **Server outputs** → verification_result.json

Just run:
```bash
python run_test_dilithium.py
```

The server will:
- ⏳ Wait for `publickey.json` from board...
- 📦 Generate `challenge.json`
- ⏳ Wait for `signature.json` from board...
- ✅ Verify and save `verification_result.json`

**Board client** (separate hardware) runs independently on LyCheeRVnano.

---

## 📊 Expected Timing

**Per Stage (typical):**
- Receive Public Key: 500-2000 µs
- Create Challenge: 1000-3000 µs  
- Verification: 500-2000 µs

**Total:** 2-7 ms

---

## 🐛 Common Issues

| Problem | Fix |
|---------|-----|
| `FileNotFoundError: publickey.json` | Ensure board client has generated and placed publickey.json in ./data/ |
| `python: command not found` | Install Python 3.8+ |
| Paths not found | Make sure running from `dilithium-qiskit-port/` folder |

---

## 📚 Learn More

- **Full Guide**: [WORKFLOW_JS_PYTHON.md](./WORKFLOW_JS_PYTHON.md)
- **Python Source**: [run_test_dilithium.py](./run_test_dilithium.py)
- **Node.js Source**: [alice_client.js](./alice_client.js)
- **Protocol Spec**: [PROTOCOL_GUIDE.md](./PROTOCOL_GUIDE.md)

---

## 🎓 Understanding the Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Alice (JS) generates keypair                         │
│    ↓                                                     │
│    Exports: publickey.txt (A, t)                       │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ 2. Server (Python) reads public key                    │
│    ⏱️  START TIMING                                    │
│    ↓                                                     │
│    Generates random challenge c                        │
│    ↓                                                     │
│    Exports: challenge.txt (ID, c)                      │
│    ⏱️  OUTPUT: Time from step 1                        │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ 3. Alice (JS) reads challenge                           │
│    ↓                                                     │
│    Signs: z = y + c*s                                  │
│    ↓                                                     │
│    Exports: signature.txt (z)                          │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ 4. Server (Python) reads signature                     │
│    ↓                                                     │
│    Verifies: A*z - c*t == w                            │
│    ↓                                                     │
│    ⏱️  OUTPUT: Total time + RESULT                    │
└─────────────────────────────────────────────────────────┘
```

---

**Ready? Run `run_test_dilithium.bat` (Windows) or `bash run_test_dilithium.sh` (Linux/macOS) now! 🚀**
