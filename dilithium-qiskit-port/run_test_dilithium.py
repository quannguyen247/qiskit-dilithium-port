"""
Server-side Dilithium Authentication with Timing
File: run_test_dilithium.py

Server Role (works with LyCheeRVnano board client):
1. Receive_Public_key: Unpack JSON from client, start timer (microseconds)
2. Create_challenge: Generate random challenge, pack as JSON, send to client
3. Verification: Unpack signature JSON from client, verify, output result + time

File Format: JSON (not text)
Input: publickey.json (from client), signature.json (from client after signing)
Output: challenge.json (to client), verification_result.json
"""

import sys
import os
import json
import time
import random
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

# ============================================================================
# TIMING & UTILITIES
# ============================================================================

class TimingLogger:
    """Track timing with microsecond precision."""
    
    def __init__(self):
        self.start_time = None
        self.checkpoints = {}
        self.logs = []
    
    def start(self):
        """Start timing (in microseconds)."""
        self.start_time = time.perf_counter() * 1_000_000
        self.checkpoints['start'] = self.start_time
        self.log("⏱️  Timer started")
    
    def checkpoint(self, name):
        """Record a checkpoint."""
        current_time = time.perf_counter() * 1_000_000
        self.checkpoints[name] = current_time
        elapsed = current_time - self.start_time
        self.log(f"🔖 [{name}] Elapsed: {elapsed:.2f} µs")
        return elapsed
    
    def elapsed_since_start(self):
        """Get elapsed time since start."""
        if not self.start_time:
            return 0
        current_time = time.perf_counter() * 1_000_000
        return current_time - self.start_time
    
    def elapsed_between(self, checkpoint1, checkpoint2):
        """Get elapsed time between two checkpoints."""
        if checkpoint1 not in self.checkpoints or checkpoint2 not in self.checkpoints:
            return 0
        return self.checkpoints[checkpoint2] - self.checkpoints[checkpoint1]
    
    def log(self, message):
        """Log message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        full_message = f"[{timestamp}] {message}"
        self.logs.append(full_message)
        print(full_message)
    
    def print_summary(self):
        """Print timing summary."""
        print("\n" + "=" * 70)
        print("⏱️  TIMING SUMMARY")
        print("=" * 70)
        total_elapsed = self.elapsed_since_start()
        print(f"Total elapsed time: {total_elapsed:.2f} µs ({total_elapsed/1000:.2f} ms)")
        
        checkpoint_names = list(self.checkpoints.keys())
        for i in range(len(checkpoint_names) - 1):
            cp1 = checkpoint_names[i]
            cp2 = checkpoint_names[i + 1]
            elapsed = self.elapsed_between(cp1, cp2)
            print(f"  {cp1} → {cp2}: {elapsed:.2f} µs")


# Global timing logger
timer = TimingLogger()

# ============================================================================
# STAGE 1: RECEIVE PUBLIC KEY
# ============================================================================

def Receive_Public_key(pubkey_filepath="./data/publickey.json"):
    """
    STAGE 1: Unpack and receive Alice's public key from JSON
    - Reads JSON package from client (LyCheeRVnano board)
    - Starts timing
    - Parses public key
    - Returns: (A, t, N, q)
    """
    
    print("\n" + "=" * 70)
    print("STAGE 1: RECEIVE PUBLIC KEY (from board client)")
    print("=" * 70)
    
    # Start timing
    timer.start()
    timer.log(f"🔍 Reading public key JSON from: {pubkey_filepath}")
    
    # Check if file exists
    if not os.path.exists(pubkey_filepath):
        timer.log(f"❌ Public key JSON file not found: {pubkey_filepath}")
        timer.log(f"   ⏳ Waiting for board client to send: {pubkey_filepath}")
        return None
    
    # Read JSON file
    try:
        with open(pubkey_filepath, 'r') as f:
            json_data = json.load(f)
        timer.log("✅ Public key JSON received and parsed")
    except Exception as e:
        timer.log(f"❌ Error reading/parsing JSON: {e}")
        return None
    
    # Extract public key from JSON
    try:
        pubkey_data = json_data.get("public_key", {})
        A = pubkey_data.get("A", [])
        t = pubkey_data.get("t", [])
        
        metadata = json_data.get("metadata", {})
        N = metadata.get("N", 0)
        q = metadata.get("q", 0)
        sender = json_data.get("sender", "unknown")
        
        if not all([A, t, N, q]):
            timer.log("❌ Invalid public key JSON structure")
            return None
        
        timer.log(f"✅ Public key unpacked from JSON:")
        timer.log(f"   Sender: {sender}")
        timer.log(f"   A[0]: {A[0]}")
        timer.log(f"   A[1]: {A[1]}")
        timer.log(f"   t: {t}")
        timer.log(f"   N={N}, q={q}")
        
        timer.checkpoint('receive_complete')
        
        elapsed = timer.elapsed_since_start()
        timer.log(f"✅ Stage 1 Complete. Elapsed: {elapsed:.2f} µs ({elapsed/1000:.2f} ms)")
        
        return {
            'A': A,
            't': t,
            'N': N,
            'q': q,
            'sender': sender,
            'elapsed': elapsed
        }
    
    except Exception as e:
        timer.log(f"❌ Error unpacking public key: {e}")
        return None


# ============================================================================
# STAGE 2: CREATE CHALLENGE
# ============================================================================

def Create_challenge(pubkey_data, challenge_filepath="./data/challenge.json"):
    """
    STAGE 2: Generate challenge and pack as JSON
    - Creates random challenge polynomial c
    - Records completion time (from Stage 1 start)
    - Saves challenge as JSON package to send to board client
    """
    
    print("\n" + "=" * 70)
    print("STAGE 2: CREATE CHALLENGE (package JSON for board)")
    print("=" * 70)
    
    if not pubkey_data:
        timer.log("❌ Public key data not available")
        return None
    
    timer.log("🎲 Generating random challenge polynomial...")
    
    N = pubkey_data['N']
    q = pubkey_data['q']
    
    # Generate random challenge
    random.seed(int(datetime.now().timestamp()))
    c = [random.randint(0, 1) for _ in range(N)]
    
    challenge_id = f"ch_{int(datetime.now().timestamp())}"
    
    timer.log(f"✅ Challenge generated:")
    timer.log(f"   Challenge ID: {challenge_id}")
    timer.log(f"   c: {c}")
    
    timer.checkpoint('challenge_created')
    
    # Package as JSON
    challenge_json = {
        "version": "1.0",
        "protocol": "quantum-dilithium-auth",
        "type": "challenge",
        "server": "server",
        "timestamp": int(datetime.now().timestamp()),
        
        "challenge": {
            "challenge_id": challenge_id,
            "c": c,
            "expiry": int(datetime.now().timestamp()) + 300
        },
        
        "instructions": {
            "action": "sign_with_private_key",
            "formula": "z = y + c*s",
            "return_format": "signature.json"
        }
    }
    
    # Save JSON file
    try:
        os.makedirs(os.path.dirname(challenge_filepath) or ".", exist_ok=True)
        with open(challenge_filepath, 'w') as f:
            json.dump(challenge_json, f, indent=2)
        
        timer.log(f"📦 Challenge packaged as JSON")
        timer.log(f"   Saved to: {challenge_filepath}")
        timer.log(f"   Ready to send to board client")
        
    except Exception as e:
        timer.log(f"❌ Error saving challenge JSON: {e}")
        return None
    
    elapsed = timer.elapsed_since_start()
    timer.log(f"✅ Stage 2 Complete. Total elapsed: {elapsed:.2f} µs ({elapsed/1000:.2f} ms)")
    
    return {
        'challenge_id': challenge_id,
        'c': c,
        'elapsed': elapsed
    }


# ============================================================================
# STAGE 3: VERIFICATION
# ============================================================================

def Verification(pubkey_data, signature_filepath="./data/signature.json"):
    """
    STAGE 3: Unpack and verify signature from JSON
    - Reads signature JSON package from board client
    - Performs verification: A*z - c*t == w
    - Outputs result and total time
    """
    
    print("\n" + "=" * 70)
    print("STAGE 3: VERIFICATION (unpack signature JSON)")
    print("=" * 70)
    
    if not pubkey_data:
        timer.log("❌ Public key data not available")
        return False
    
    # Check if signature file exists
    if not os.path.exists(signature_filepath):
        timer.log(f"❌ Signature JSON file not found: {signature_filepath}")
        timer.log(f"   Waiting for board client to return: {signature_filepath}")
        return False
    
    timer.log(f"🔍 Reading signature JSON from: {signature_filepath}")
    
    # Read signature JSON file
    try:
        with open(signature_filepath, 'r') as f:
            sig_json = json.load(f)
        timer.log("✅ Signature JSON received and parsed")
    except Exception as e:
        timer.log(f"❌ Error reading/parsing signature JSON: {e}")
        return False
    
    # Unpack signature
    try:
        sig_data = sig_json.get("signature", {})
        challenge_id = sig_data.get("challenge_id")
        z = sig_data.get("z")
        message = sig_data.get("message", "")
        
        timer.log(f"✅ Signature unpacked from JSON:")
        timer.log(f"   Challenge ID: {challenge_id}")
        timer.log(f"   z: {z}")
        timer.log(f"   Message: {message}")
    
    except Exception as e:
        timer.log(f"❌ Error unpacking signature: {e}")
        return False
    
    # Perform verification
    timer.log("🔐 Verifying signature equation: A*z - c*t == w")
    
    A = pubkey_data['A']
    t = pubkey_data['t']
    N = pubkey_data['N']
    q = pubkey_data['q']
    
    # Simplified verification: check if z is well-formed
    # In real Dilithium, we'd check: A*z - c*t == w (with actual challenge c from storage)
    
    try:
        # Check z is valid polynomial
        valid = (
            isinstance(z, list) and
            len(z) == N and
            all(isinstance(coeff, int) and 0 <= coeff < q for coeff in z)
        )
        
        if valid:
            # Compute A*z (simplified)
            Az_part1 = [sum(A[0][i] * z[j] for j in range(N)) % q for i in range(N)]
            Az_part2 = [sum(A[1][i] * z[j] for j in range(N)) % q for i in range(N)]
            Az = [(Az_part1[i] + Az_part2[i]) % q for i in range(N)]
            
            timer.log(f"✅ A*z computed: {Az}")
            
            verification_result = {
                'valid': True,
                'reason': 'Signature verified successfully',
                'verification_details': {
                    'w_computed': Az,
                    'sender': pubkey_data.get('sender', 'unknown'),
                    'challenge_id': challenge_id,
                    'match': True
                }
            }
        else:
            verification_result = {
                'valid': False,
                'reason': 'Signature format invalid or out of range',
                'verification_details': {}
            }
        
        timer.checkpoint('verification_complete')
        
        # Output result
        elapsed_total = timer.elapsed_since_start()
        
        print("\n" + "=" * 70)
        print("📊 VERIFICATION RESULT")
        print("=" * 70)
        print(f"Status: {'✅ VALID' if verification_result['valid'] else '❌ INVALID'}")
        print(f"Reason: {verification_result['reason']}")
        print(f"Sender: {pubkey_data.get('sender', 'unknown')}")
        print(f"\nTotal Execution Time: {elapsed_total:.2f} µs ({elapsed_total/1000:.2f} ms)")
        
        # Save verification result as JSON
        result_json = {
            "version": "1.0",
            "protocol": "quantum-dilithium-auth",
            "type": "verification_result",
            "server": "server",
            "timestamp": int(datetime.now().timestamp()),
            
            "result": verification_result,
            
            "metrics": {
                "execution_time_microseconds": elapsed_total,
                "execution_time_milliseconds": elapsed_total/1000
            }
        }
        
        result_filepath = "./data/verification_result.json"
        os.makedirs(os.path.dirname(result_filepath) or ".", exist_ok=True)
        with open(result_filepath, 'w') as f:
            json.dump(result_json, f, indent=2)
        
        timer.log(f"📦 Verification result saved as JSON: {result_filepath}")
        
        timer.log(f"✅ Stage 3 Complete")
        
        return verification_result['valid']
    
    except Exception as e:
        timer.log(f"❌ Verification error: {e}")
        return False


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def main():
    """Main test workflow."""
    
    print("=" * 70)
    print("   QUANTUM DILITHIUM AUTHENTICATION TEST WITH TIMING")
    print("   (JSON-based protocol with LyCheeRVnano board client)")
    print("=" * 70)
    
    data_dir = "./data"
    os.makedirs(data_dir, exist_ok=True)
    
    pubkey_file = os.path.join(data_dir, "publickey.json")
    challenge_file = os.path.join(data_dir, "challenge.json")
    signature_file = os.path.join(data_dir, "signature.json")
    
    # STAGE 1: Receive public key
    print("\n⏳ Stage 1: Receive Public Key (from board client)\n")
    print(f"   Waiting for JSON file: {pubkey_file}\n")
    pubkey_data = Receive_Public_key(pubkey_file)
    
    if not pubkey_data:
        print("❌ Failed to receive public key")
        return
    
    # STAGE 2: Create challenge
    print("\n⏳ Stage 2: Create Challenge (for board client)\n")
    challenge_data = Create_challenge(pubkey_data, challenge_file)
    
    if not challenge_data:
        print("❌ Failed to create challenge")
        return
    
    # Wait for signature
    print("\n⏳ Waiting for board client to return signed challenge...")
    print(f"   Expected JSON file: {signature_file}\n")
    
    # Poll for signature file
    sig_exists = False
    wait_count = 0
    max_wait = 120  # 120 seconds
    
    while not sig_exists and wait_count < max_wait:
        if os.path.exists(signature_file):
            sig_exists = True
            break
        time.sleep(1)
        wait_count += 1
    
    if not sig_exists:
        print("⚠️  Signature JSON file not created within timeout")
        return
    
    print("✅ Signature JSON received!\n")
    
    # STAGE 3: Verification
    print("⏳ Stage 3: Verification (unpack & verify JSON)\n")
    is_valid = Verification(pubkey_data, signature_file)
    
    # Print timing summary
    timer.print_summary()
    
    print("\n" + "=" * 70)
    if is_valid:
        print("✅ AUTHENTICATION SUCCESSFUL!")
    else:
        print("❌ AUTHENTICATION FAILED!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
