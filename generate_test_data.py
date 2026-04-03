#!/usr/bin/env python3
"""
Board Client Simulator: Generate Public Key + Sign Challenge
Simulates alice_client.js workflow

Workflow:
  1. KeyGen: Generate public key (A, t) + private key (s1, s2) → publickey.json
  2. Wait: for challenge.json from server
  3. Sign: Using private key + challenge → signature.json

Usage:
  python generate_test_data.py
"""

import sys
import os
import json
import random
import time
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'dilithium-qiskit-port', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'dilithium-qiskit-port'))

import parameters

def generate_random_poly(n, bound):
    """Generate random polynomial with coefficients in [0, bound)."""
    return [random.randint(0, bound-1) for _ in range(n)]

def main():
    print("=" * 70)
    print("BOARD CLIENT SIMULATOR - Quantum Dilithium Authentication")
    print("=" * 70)
    
    config = parameters.CURRENT_CONFIG
    print(f"\n📝 Configuration: {config.name}")
    print(f"   N = {config.N}, q = {config.q}")
    
    # Create data directory
    data_dir = os.path.join(os.path.dirname(__file__), 'dilithium-qiskit-port', 'data')
    os.makedirs(data_dir, exist_ok=True)
    print(f"\n📁 Data directory: {data_dir}")
    
    N = config.N
    q = config.q
    
    # =====================================================================
    # STAGE 1: KeyGen - Generate Public Key (A, t) + Private Key (s1, s2)
    # =====================================================================
    print("\n" + "=" * 70)
    print("STAGE 1: KEYGEN (Generate Keys)")
    print("=" * 70)
    
    print("\n🔑 Generating keypair...")
    random.seed(42)  # Deterministic for testing
    
    # Private key (secret)
    s1 = generate_random_poly(N, 5)  # Small coefficients
    s2 = generate_random_poly(N, 5)
    print(f"   Private key s (s1, s2): Generated (keeping secret)")
    
    # Public key (A matrix, random)
    A_0 = generate_random_poly(N, q)
    A_1 = generate_random_poly(N, q)
    t = generate_random_poly(N, q)
    
    print(f"   Public key A (A[0], A[1]): Generated")
    print(f"   Public key t: Generated")
    
    # Create publickey.json
    publickey_json = {
        "version": "1.0",
        "protocol": "quantum-dilithium-auth",
        "type": "publickey",
        "sender": "board_client",
        "timestamp": int(datetime.now().timestamp()),
        
        "public_key": {
            "A": [A_0, A_1],
            "t": t
        },
        
        "metadata": {
            "N": N,
            "q": q,
            "source": "Board Client (alice_client simulation)"
        }
    }
    
    pubkey_file = os.path.join(data_dir, 'publickey.json')
    with open(pubkey_file, 'w') as f:
        json.dump(publickey_json, f, indent=2)
    
    print(f"\n✅ Public key saved: {os.path.basename(pubkey_file)}")
    print(f"   A[0]: {A_0}")
    print(f"   A[1]: {A_1}")
    print(f"   t: {t}")
    print(f"   Private key s1, s2: (kept secret)")
    
    # =====================================================================
    # STAGE 2: Wait for Challenge from Server
    # =====================================================================
    print("\n" + "=" * 70)
    print("STAGE 2: WAIT FOR CHALLENGE (from server)")
    print("=" * 70)
    
    challenge_file = os.path.join(data_dir, 'challenge.json')
    
    print(f"\n⏳ Waiting for challenge from server...")
    print(f"   Expected file: {os.path.basename(challenge_file)}")
    print(f"   (Server should create this file after receiving publickey.json)")
    
    # Poll for challenge file
    challenge_data = None
    wait_count = 0
    max_wait = 120  # 120 seconds timeout
    
    while not challenge_data and wait_count < max_wait:
        if os.path.exists(challenge_file):
            try:
                with open(challenge_file, 'r') as f:
                    challenge_json = json.load(f)
                
                # Validate challenge structure
                if 'challenge' in challenge_json and 'c' in challenge_json['challenge']:
                    challenge_data = challenge_json
                    print(f"\n✅ Challenge received!")
                    break
            except:
                pass
        
        if wait_count % 10 == 0:
            print(f"   ⏳ Still waiting... ({wait_count}s elapsed)", end='\r')
        
        time.sleep(1)
        wait_count += 1
    
    if not challenge_data:
        print(f"\n❌ Timeout: No challenge.json received after {max_wait}s")
        print(f"   Make sure server is running and created challenge.json")
        return
    
    # Extract challenge
    c = challenge_data['challenge']['c']
    challenge_id = challenge_data['challenge'].get('challenge_id', 'unknown')
    
    print(f"   Challenge ID: {challenge_id}")
    print(f"   Challenge polynomial c: {c}")
    print(f"   ✅ Challenge received at {datetime.now().strftime('%H:%M:%S')}")
    
    # =====================================================================
    # STAGE 3: Sign - Create Signature using Private Key
    # =====================================================================
    print("\n" + "=" * 70)
    print("STAGE 3: SIGN (Create Signature)")
    print("=" * 70)
    
    print(f"\n🔐 Signing challenge with private key...")
    print(f"   Using: private key s1, s2")
    print(f"   With: challenge polynomial c")
    
    # Compute signature: z = s + c (pointwise addition mod q)
    # For simplicity: z1 = s1 + c, z2 = s2
    z1 = [(s1[i] + c[i]) % q for i in range(N)]
    z2 = [s2[i] for i in range(N)]
    
    print(f"   Computing z = s + c (mod {q})")
    print(f"   z1 = s1 + c: {z1}")
    print(f"   z2 = s2:     {z2}")
    
    # Create signature.json
    sig_json = {
        "version": "1.0",
        "protocol": "quantum-dilithium-auth",
        "type": "signature",
        "client": "board_client",
        "timestamp": int(datetime.now().timestamp()),
        
        "signature": {
            "challenge_id": challenge_id,
            "z": z1,  # Primary signature (z1)
            "message": "Signed challenge for quantum Dilithium authentication"
        }
    }
    
    sig_file = os.path.join(data_dir, 'signature.json')
    with open(sig_file, 'w') as f:
        json.dump(sig_json, f, indent=2)
    
    print(f"\n✅ Signature created: {os.path.basename(sig_file)}")
    print(f"   Challenge ID: {challenge_id}")
    print(f"   Signature z: {z1}")
    
    # =====================================================================
    # Summary
    # =====================================================================
    print("\n" + "=" * 70)
    print("✅ BOARD CLIENT WORKFLOW COMPLETE!")
    print("=" * 70)
    
    print("\n📊 FILES CREATED:")
    print(f"  1. {os.path.basename(pubkey_file)} ✅ (from KeyGen)")
    print(f"  2. {os.path.basename(sig_file)} ✅ (from Sign)")
    print(f"     └─ Requires challenge.json from server first!")
    
    print("\n📋 WORKFLOW SEQUENCE:")
    print("  Stage 1: Board generates publickey.json")
    print("  ↓")
    print("  → Server reads publickey.json")
    print("  ↓")
    print("  Stage 2: Server generates challenge.json")
    print("  ↓")
    print("  → Board reads challenge.json (WAIT for this!)")
    print("  ↓")
    print("  Stage 3: Board generates signature.json")
    print("  ↓")
    print("  → Server verifies signature using QUANTUM circuits")
    
    print("\n🔧 NEXT STEPS:")
    print(f"  Server will verify signature and output: verification_result.json")
    print()

if __name__ == "__main__":
    main()

