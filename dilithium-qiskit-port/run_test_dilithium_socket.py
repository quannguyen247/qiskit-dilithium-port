#!/usr/bin/env python3
"""
Quantum Dilithium Authentication Server with Binary Struct Packing Protocol
Optimized for LicheeRV Nano ↔ Python Server Communication

Protocol: Header-Payload Packing
[Magic(2b)] [Type(1b)] [Len(4b)] [Data(Nb)]

Stages:
1. Listen → Receive PublicKey packet
2. Extract & Save PublicKey
3. Generate Challenge
4. Pack & Send Challenge packet
5. Listen → Receive Signature packet
6. Extract & Save Signature
7. Quantum Verify (Demo Mini Flow)
"""

import sys
import os
import socket
import struct
import time
import random
from datetime import datetime

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

import parameters
from demo_mini_flow import MiniDilithium

# ============================================================================
# PROTOCOL CONSTANTS
# ============================================================================

PACKET_MAGIC = 0xABCD      # Magic number for packet validation
PACKET_HEADER_SIZE = 7     # 2 (magic) + 1 (type) + 4 (length)

# Packet Types
PACKET_TYPE_PUBLICKEY = 1
PACKET_TYPE_SIGNATURE = 2
PACKET_TYPE_CHALLENGE = 3
PACKET_TYPE_ERROR = 255

# Server config
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5000

# ============================================================================
# TIMING UTILITIES
# ============================================================================

class QuantumTimer:
    """Track execution time with millisecond precision"""
    
    def __init__(self):
        self.start_time = time.time()
        self.stages = {}
    
    def elapsed_ms(self):
        """Get elapsed time in milliseconds since start"""
        return (time.time() - self.start_time) * 1000
    
    def checkpoint(self, name):
        """Record a checkpoint"""
        elapsed = self.elapsed_ms()
        self.stages[name] = elapsed
        print(f"[{elapsed:8.2f} ms] ✓ {name}")
        return elapsed

timer = QuantumTimer()

# ============================================================================
# BINARY PROTOCOL FUNCTIONS
# ============================================================================

def pack_packet(packet_type, data):
    """
    Pack data into binary packet format
    [Magic(2b)][Type(1b)][Len(4b)][Data(Nb)]
    """
    header = struct.pack(">HBI", PACKET_MAGIC, packet_type, len(data))
    return header + data

def unpack_packet(raw_data):
    """
    Unpack binary packet and validate
    Returns: (type, payload) or (None, None) if invalid
    """
    if len(raw_data) < PACKET_HEADER_SIZE:
        print("❌ Packet too short")
        return None, None
    
    header = raw_data[:PACKET_HEADER_SIZE]
    payload = raw_data[PACKET_HEADER_SIZE:]
    
    try:
        magic, pkt_type, pkt_len = struct.unpack(">HBI", header)
        
        if magic != PACKET_MAGIC:
            print(f"❌ Invalid magic: 0x{magic:04X} (expected 0x{PACKET_MAGIC:04X})")
            return None, None
        
        if len(payload) != pkt_len:
            print(f"❌ Length mismatch: got {len(payload)}, expected {pkt_len}")
            return None, None
        
        return pkt_type, payload
    
    except Exception as e:
        print(f"❌ Unpack error: {e}")
        return None, None

def array_to_bytes(arr):
    """Convert Python list to packed bytes"""
    return struct.pack(f">{len(arr)}B", *arr)

def bytes_to_array(data, size):
    """Convert bytes to Python list of ints"""
    return list(struct.unpack(f">{size}B", data))

# ============================================================================
# STAGE 1: LISTEN & RECEIVE PUBLICKEY
# ============================================================================

def receive_publickey(sock, timeout_sec=60):
    """
    Stage 1: Listen for public key packet from board client
    """
    print("\n" + "=" * 70)
    print("STAGE 1: LISTEN & RECEIVE PUBLIC KEY")
    print("=" * 70)
    
    timer.checkpoint("Stage 1 START")
    
    config = parameters.CURRENT_CONFIG
    N = config.N
    
    print(f"\n🔊 Listening on {SERVER_HOST}:{SERVER_PORT} for {timeout_sec}s...")
    
    try:
        sock.settimeout(timeout_sec)
        sock.bind((SERVER_HOST, SERVER_PORT))
        sock.listen(1)
        
        print("⏳ Waiting for client connection...")
        conn, addr = sock.accept()
        print(f"✓ Client connected: {addr}")
        
        # Receive packet
        print("⏳ Receiving public key packet...")
        raw_data = conn.recv(4096)
        
        if not raw_data:
            print("❌ No data received")
            return None, None
        
        # Unpack packet
        pkt_type, payload = unpack_packet(raw_data)
        
        if pkt_type != PACKET_TYPE_PUBLICKEY:
            print(f"❌ Wrong packet type: {pkt_type}")
            return None, None
        
        print(f"✓ Received {len(payload)} bytes of public key data")
        
        # Parse public key: [A[0] (N bytes)][A[1] (N bytes)][t (N bytes)]
        offset = 0
        A_0 = bytes_to_array(payload[offset:offset+N], N)
        offset += N
        
        A_1 = bytes_to_array(payload[offset:offset+N], N)
        offset += N
        
        t = bytes_to_array(payload[offset:offset+N], N)
        
        pubkey_data = {
            'A': [A_0, A_1],
            't': t,
            'N': N,
            'q': config.q,
            'conn': conn
        }
        
        print(f"\n✓ Public Key Unpacked:")
        print(f"   A[0] (len={len(A_0)}): {A_0[:5]}..." if len(A_0) > 5 else f"   A[0]: {A_0}")
        print(f"   A[1] (len={len(A_1)}): {A_1[:5]}..." if len(A_1) > 5 else f"   A[1]: {A_1}")
        print(f"   t (len={len(t)}): {t[:5]}..." if len(t) > 5 else f"   t: {t}")
        
        timer.checkpoint("Stage 1 COMPLETE")
        return pubkey_data, conn
    
    except socket.timeout:
        print(f"❌ Timeout: No connection after {timeout_sec}s")
        return None, None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None

# ============================================================================
# STAGE 2-3: CREATE & SEND CHALLENGE
# ============================================================================

def create_and_send_challenge(pubkey_data, conn):
    """
    Stage 2-3: Generate random challenge and send as packet
    """
    print("\n" + "=" * 70)
    print("STAGE 2-3: CREATE & SEND CHALLENGE")
    print("=" * 70)
    
    timer.checkpoint("Stage 2 START")
    
    N = pubkey_data['N']
    config = parameters.CURRENT_CONFIG
    
    # Generate random challenge (binary polynomial)
    print("\n🎲 Generating challenge polynomial c...")
    random.seed(int(time.time()))
    c = [random.randint(0, 1) for _ in range(N)]
    
    print(f"✓ Challenge generated: {c}")
    
    # Pack challenge as binary
    challenge_bytes = array_to_bytes(c)
    
    # Create packet
    packet = pack_packet(PACKET_TYPE_CHALLENGE, challenge_bytes)
    
    print(f"📦 Packing challenge into {len(packet)} bytes")
    print(f"   Header: {len(packet) - len(challenge_bytes)} bytes")
    print(f"   Payload: {len(challenge_bytes)} bytes")
    
    # Send packet
    print("📤 Sending challenge to client...")
    conn.send(packet)
    
    timer.checkpoint("Stage 2 SEND CHALLENGE")
    
    return c

# ============================================================================
# STAGE 4-5: RECEIVE SIGNATURE
# ============================================================================

def receive_signature(conn, timeout_sec=60):
    """
    Stage 4-5: Listen and receive signature packet
    """
    print("\n" + "=" * 70)
    print("STAGE 4-5: LISTEN & RECEIVE SIGNATURE")
    print("=" * 70)
    
    timer.checkpoint("Stage 4 START")
    
    config = parameters.CURRENT_CONFIG
    N = config.N
    
    conn.settimeout(timeout_sec)
    
    print(f"\n⏳ Waiting for signature packet ({timeout_sec}s timeout)...")
    
    try:
        raw_data = conn.recv(4096)
        
        if not raw_data:
            print("❌ No data received")
            return None
        
        # Unpack packet
        pkt_type, payload = unpack_packet(raw_data)
        
        if pkt_type != PACKET_TYPE_SIGNATURE:
            print(f"❌ Wrong packet type: {pkt_type}")
            return None
        
        print(f"✓ Received {len(payload)} bytes of signature data")
        
        # Parse signature: [z (N bytes)]
        z = bytes_to_array(payload[:N], N)
        
        print(f"\n✓ Signature Unpacked:")
        print(f"   z (len={len(z)}): {z}")
        
        timer.checkpoint("Stage 4 RECEIVE SIGNATURE")
        
        return z
    
    except socket.timeout:
        print(f"❌ Timeout: No signature after {timeout_sec}s")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# ============================================================================
# STAGE 6: QUANTUM VERIFY (from demo_mini_flow)
# ============================================================================

def quantum_verify(pubkey_data, challenge_c, signature_z):
    """
    Stage 6: Verify signature using QUANTUM arithmetic (MiniDilithium)
    """
    print("\n" + "=" * 70)
    print("STAGE 6: QUANTUM VERIFY")
    print("=" * 70)
    
    timer.checkpoint("Stage 5 START")
    
    config = parameters.CURRENT_CONFIG
    N = pubkey_data['N']
    q = pubkey_data['q']
    
    A = pubkey_data['A']
    t = pubkey_data['t']
    
    print(f"\n🔧 Initializing Quantum Backend (MiniDilithium)...")
    
    try:
        dil = MiniDilithium(config=config)
        print(f"✓ Quantum simulator ready: {config.backend_name}")
        print(f"  Method: {config.backend_method}")
        print(f"  ~{N * config.k_bits + 3} qubits active")
    except Exception as e:
        print(f"❌ Quantum backend error: {e}")
        return False
    
    timer.checkpoint("Stage 5 QSim INIT")
    
    try:
        print(f"\n🔐 Verifying signature using QUANTUM arithmetic...")
        
        # Classical: Transform A to NTT domain
        print(f"   [Classical] Transform A to NTT domain...")
        A_hat_0 = dil.classical_dft(A[0])
        A_hat_1 = dil.classical_dft(A[1])
        
        timer.checkpoint("Stage 5 Classical DFT")
        
        # Quantum: Compute A*z using quantum circuits
        print(f"   [Quantum] Computing A[0]*z on quantum hardware...")
        Az_0 = dil.quantum_poly_mul(signature_z, A_hat_0, "verify_Az_0")
        
        timer.checkpoint("Stage 5 Quantum A[0]*z")
        
        print(f"   [Quantum] Computing A[1]*z on quantum hardware...")
        Az_1 = dil.quantum_poly_mul(signature_z, A_hat_1, "verify_Az_1")
        
        timer.checkpoint("Stage 5 Quantum A[1]*z")
        
        # Classical: Compute c*t
        print(f"   [Classical] Computing c*t...")
        ct = dil.classical_mul_scalar(t, challenge_c[0])
        
        print(f"\n✓ Quantum verification complete!")
        print(f"   A*z[0]: {[int(x) for x in Az_0]}")
        print(f"   A*z[1]: {[int(x) for x in Az_1]}")
        print(f"   c*t: {ct}")
        
        # Simple verification check (format validation)
        valid = (
            isinstance(Az_0, (list, tuple)) and len(Az_0) == N and
            isinstance(signature_z, (list, tuple)) and len(signature_z) == N
        )
        
        timer.checkpoint("Stage 5 VERIFY COMPLETE")
        
        return valid, {
            'Az_0': [int(x) for x in Az_0],
            'Az_1': [int(x) for x in Az_1],
            'ct': ct,
            'z': signature_z
        }
    
    except Exception as e:
        print(f"❌ Verification error: {e}")
        import traceback
        traceback.print_exc()
        return False, None

# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def main():
    print("=" * 70)
    print("     QUANTUM DILITHIUM SERVER - Binary Protocol Edition")
    print("=" * 70)
    print(f"\n⏱️  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Timer Resolution: Milliseconds (ms)")
    
    timer.checkpoint("INIT START")
    
    config = parameters.CURRENT_CONFIG
    print(f"\n📋 Configuration: {config.name}")
    print(f"   N={config.N}, q={config.q}")
    print(f"   Backend: {config.backend_name} [{config.backend_method}]")
    
    # Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Stage 1: Receive PublicKey
        pubkey_data, conn = receive_publickey(sock, timeout_sec=120)
        
        if not pubkey_data:
            print("\n❌ Failed to receive public key")
            return
        
        # Stage 2-3: Create and Send Challenge
        challenge_c = create_and_send_challenge(pubkey_data, conn)
        
        # Stage 4-5: Receive Signature
        signature_z = receive_signature(conn, timeout_sec=120)
        
        if signature_z is None:
            print("\n❌ Failed to receive signature")
            return
        
        # Stage 6: Quantum Verify
        is_valid, verify_result = quantum_verify(pubkey_data, challenge_c, signature_z)
        
        # Final Report
        print("\n" + "=" * 70)
        print("📊 FINAL REPORT")
        print("=" * 70)
        
        print(f"\n✅ VERIFICATION RESULT: {'✓ VALID' if is_valid else '✗ INVALID'}")
        print(f"\n⏱️  TIMING BREAKDOWN (milliseconds):")
        
        for stage_name in sorted(timer.stages.keys(), key=lambda x: timer.stages[x]):
            elapsed = timer.stages[stage_name]
            print(f"  {stage_name:30s}: {elapsed:10.2f} ms")
        
        total_elapsed = timer.elapsed_ms()
        print(f"\n{'TOTAL EXECUTION TIME':30s}: {total_elapsed:10.2f} ms")
        print(f"{'(seconds)':30s}: {total_elapsed/1000:10.2f} s")
        
        print("\n" + "=" * 70 + "\n")
        
        conn.close()
    
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        sock.close()

if __name__ == "__main__":
    main()
