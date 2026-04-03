# 🔐 Quantum Dilithium Authentication Server Guide

## 📋 Architecture

**This repository is a Python server only:**
- **Python (Server)**: ← Receives public key JSON from board
                     → Generates challenge JSON for board
                     ← Receives signature JSON from board
                     → Verifies and saves result

- **Board Client (LyCheeRVnano - Separate Hardware)**:
  - Runs independently on board hardware
  - Generates keypair locally
  - Exports public key → `publickey.json`
  - Signs challenge ← `challenge.json`
  - Exports signature → `signature.json`

Communication happens through **JSON files** with **microsecond precision timing**.

---

## 🚀 Running the Server

```bash
cd dilithium-qiskit-port
python run_test_dilithium.py
```

The server will:
1. ⏳ **Wait for** `./data/publickey.json` (from board client)
2. 📦 **Generate** `./data/challenge.json` 
3. ⏳ **Wait for** `./data/signature.json` (from board client)
4. ✅ **Verify** signature and save `./data/verification_result.json`

**Output Example:**

```
======================================================================
   QUANTUM DILITHIUM AUTHENTICATION TEST WITH TIMING
   (JSON-based protocol with LyCheeRVnano board client)
======================================================================

⏳ Stage 1: Receive Public Key (from board client)

   Waiting for JSON file: ./data/publickey.json

[2026-04-02 14:30:45.123] ⏱️  Timer started
[2026-04-02 14:30:45.124] 🔍 Reading public key JSON from: ./data/publickey.json
⏳ Waiting for board client to send: ./data/publickey.json
---

## 📝 Board Client Reference (alice_client.js)

**Location**: `alice_client.js` (runs on board hardware only)

**What it does:**
1. Generates keypair (s1, s2 secret; A, t public)
2. Exports `publickey.json` to `./data/`
3. Waits for `challenge.json` from server
4. Signs challenge → `z = y + c*s`
5. Exports `signature.json` to `./data/`

**Example output** (reference):
```
       BOARD CLIENT - QUANTUM DILITHIUM (LyCheeRVnano)

✅ [BOARD] KeyGen: Generating keypair...

  Secret s1: [3,1,4,2] (NOT exported)
  Secret s2: [1,4,2,3] (NOT exported)

  Public A[0]: [5,12,8,14]
  Public A[1]: [10,3,16,7]
  Public t: [12,15,2,9]

📦 Exported public key to: ./data/publickey.json (JSON format)
⏳ Waiting for server to generate challenge...
✅ Challenge JSON received (from server)
✅ [BOARD] Signing challenge...
📦 Signature saved to: ./data/signature.json (JSON format)
```

---

## ⏱️ Timing Metrics (Microseconds)

All timing is in **microseconds (µs)** - measured by the Python server:

### Stage 1: Receive_Public_key
- Starts timer when reading `publickey.json`
- Records elapsed time until JSON is unpacked
- Output: `Stage 1 Complete. Elapsed: 1234.56 µs`

### Stage 2: Create_challenge
- Continues from Stage 1 start time
- Generates random challenge polynomial `c`
- Packages as JSON with versioning and metadata
- Output: `Stage 2 Complete. Total elapsed: 3456.78 µs`

### Stage 3: Verification
- Reads signature JSON from file
- Unpacks JSON and verifies using public key equation
- Saves verification result as JSON
- Output: `Total Execution Time: 5234.12 µs (5.23 ms)`

---

## 📁 JSON File Exchange

```
Stage 1 (Board → Server):
  ./data/publickey.json
  {
    "version": "1.0",
    "protocol": "quantum-dilithium-auth",
    "sender": "board-client",
    "public_key": {"A": [...], "t": [...]},
    "metadata": {"N": 4, "q": 17}
  }
  
Stage 2 (Server → Board):
  ./data/challenge.json
  {
    "version": "1.0",
    "protocol": "quantum-dilithium-auth",
    "type": "challenge",
    "server": "server",
    "challenge": {"challenge_id": "...", "c": [...]}
  }
  
Stage 3 (Board → Server):
  ./data/signature.json
  {
    "version": "1.0",
    "protocol": "quantum-dilithium-auth",
    "type": "signature",
    "sender": "board-client",
    "signature": {"challenge_id": "...", "z": [...]}
  }
  
Stage 3 Result (Server → Board):
  ./data/verification_result.json
  {
    "version": "1.0",
    "protocol": "quantum-dilithium-auth",
    "type": "verification_result",
    "result": {"valid": true, "reason": "..."}
  }
```

---

## 🧪 Testing

### Automated Flow
1. Terminal 1: `python run_test_dilithium.py`
2. Terminal 2: `node alice_client.js`
3. Alice signs automatically when challenge is ready
4. Server verifies when signature is ready

### Expected Timing
```
Receive public key:    500-2000 µs
Create challenge:      1000-3000 µs
Verification:          500-2000 µs
─────────────────────────────────
Total per stage:       2-7 ms
```

---

## 🔧 Manual Step-by-Step

### Step 1: Alice Generates Public Key
```bash
node alice_client.js
```
Creates: `./data/publickey.txt`

### Step 2: Server Creates Challenge
```bash
python run_test_dilithium.py
```
Creates: `./data/challenge.txt`

### Step 3: Alice Signs
```bash
node alice_client.js
```
Creates: `./data/signature.txt`

### Step 4: Server Verifies
```bash
python run_test_dilithium.py
```
Outputs: Verification result + timing

---

## 📊 Output Format Example

**Timing Summary:**
```
⏱️  TIMING SUMMARY
======================================================================
Total elapsed time: 5234.12 µs (5.23 ms)
  start → receive_complete: 1234.56 µs
  receive_complete → challenge_created: 2345.67 µs
  challenge_created → verification_complete: 1654.89 µs
```

**Verification Result:**
```
======================================================================
📊 VERIFICATION RESULT
======================================================================
Status: ✅ VALID
Reason: Signature verified successfully

Total Execution Time: 5234.12 µs (5.23 ms)
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `node: command not found` | Install Node.js |
| `python: command not found` | Install Python |
| `FileNotFoundError: publickey.txt` | Run alice_client.js first |
| Timing shows 0 µs | Check system timer resolution |

---

**Happy quantum testing! 🚀**
