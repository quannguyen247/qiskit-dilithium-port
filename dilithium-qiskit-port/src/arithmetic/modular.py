# Module 2: Modular Arithmetic Primitives for Dilithium
# Implements a + b mod q efficiently on quantum circuits, fully reversible with no resets.

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

class ModularArithmetic:
    """
    Implements modular arithmetic operations |a> -> |a mod q>
    Reversible implementation without qc.reset().
    """

    @staticmethod
    def add_mod7(qc, reg_a, reg_b, reg_aux):
        """
        Computes |a>|b> -> |a>|(a+b)%7>
        Preconditions:
            reg_a (3 bits): 0 <= a < 7
            reg_b (4 bits): 0 <= b < 7 (MSB b[3] must be 0)
            reg_aux (3 bits): |000>
        Postconditions:
            reg_b holds (a+b)%7 in bits 0-2. Bit 3 is 0.
            reg_aux is restored to |000>.
        """
        # --- Step 1: Plain Addition reg_b = reg_a + reg_b ---
        # Use simple ripple adder.
        # Uses aux[0] for C0, aux[1] for C1.
        
        # Bit 0
        qc.ccx(reg_a[0], reg_b[0], reg_aux[0]) # C0
        qc.cx(reg_a[0], reg_b[0])              # Sum0
        
        # Bit 1
        qc.ccx(reg_a[1], reg_b[1], reg_aux[1]) # Gen1
        qc.cx(reg_a[1], reg_b[1])              # Prop1
        qc.ccx(reg_aux[0], reg_b[1], reg_aux[1]) # Carry1 (using Prop1)
        qc.cx(reg_aux[0], reg_b[1])              # Sum1 = Prop1 ^ C0
        
        # Bit 2 (Output C2 into b[3])
        qc.ccx(reg_a[2], reg_b[2], reg_b[3])   # Gen2 -> b[3]
        qc.cx(reg_a[2], reg_b[2])              # Prop2
        qc.ccx(reg_aux[1], reg_b[2], reg_b[3]) # Carry2 -> b[3]
        qc.cx(reg_aux[1], reg_b[2])            # Sum2
        
        # Uncompute Carries from Step 1 (aux[1], aux[0])
        # Uncompute aux[1] (C1)
        qc.cx(reg_aux[0], reg_b[1])              # Restore Prop1 in b[1]
        qc.ccx(reg_aux[0], reg_b[1], reg_aux[1]) # Uncompute Carry1 (P & C0)
        # Note: Prop1 = a1 ^ b_old1. Gen1 = a1 & b_old1.
        # We need to uncompute Gen1.
        # We assume typical Adder uncompute pattern.
        # But wait, Gen1 = a1 & b_old1.
        # b[1] currently holds Prop1 (after restoring b[1]).
        # Prop1 ^ a1 -> b_old1.
        qc.cx(reg_a[1], reg_b[1])              # b[1] -> b_old1
        qc.ccx(reg_a[1], reg_b[1], reg_aux[1]) # Uncompute Gen1
        qc.cx(reg_a[1], reg_b[1])              # Back to Prop1
        qc.cx(reg_aux[0], reg_b[1])            # Back to Sum1

        # Uncompute aux[0] (C0)
        # Same logic for Bit 0
        qc.cx(reg_a[0], reg_b[0])              # Restore b_old[0]
        qc.ccx(reg_a[0], reg_b[0], reg_aux[0]) # Uncompute C0
        qc.cx(reg_a[0], reg_b[0])              # Back to Sum0
        
        # aux is now |000>. reg_b holds (A+B).
        
        # --- Step 2: Compute Flag (b >= 7) ---
        # b >= 7 <=> b[3]==1 OR (b[2]==1 & b[1]==1 & b[0]==1)
        # Store (b[2]&b[1]&b[0]) in aux[0]
        qc.ccx(reg_b[0], reg_b[1], reg_aux[0]) # b0 & b1 -> aux[0]
        qc.ccx(reg_b[2], reg_aux[0], reg_aux[2]) # b0 & b1 & b2 -> aux[2]
        
        # Flag = b[3] OR aux[2]. Store in aux[1].
        qc.x(reg_b[3])
        qc.x(reg_aux[2])
        qc.ccx(reg_b[3], reg_aux[2], reg_aux[1]) # NOR -> aux[1]
        qc.x(reg_aux[1]) # OR -> Flag
        qc.x(reg_aux[2]) # Restore
        qc.x(reg_b[3])   # Restore
        
        # Uncompute aux[2] and aux[0]
        qc.ccx(reg_b[2], reg_aux[0], reg_aux[2])
        qc.ccx(reg_b[0], reg_b[1], reg_aux[0])
        
        # Now aux[1] has Flag. aux[0], aux[2] are 0.
        
        # --- Step 3: Conditional Subtract 7 (Add 9 = 1001) controlled by aux[1] ---
        ctrl = reg_aux[1]
        
        # Bit 0: b[0] += 1 (controlled)
        # C0 = b[0] & ctrl -> aux[0]
        qc.ccx(reg_b[0], ctrl, reg_aux[0])
        qc.cx(ctrl, reg_b[0]) # Sum0
        
        # Bit 1: b[1] += 0 + C0
        # C1 = b[1] & C0 -> aux[2]
        qc.ccx(reg_b[1], reg_aux[0], reg_aux[2])
        qc.cx(reg_aux[0], reg_b[1]) # Sum1
        
        # Bit 2: b[2] += 0 + C1
        # Need C2. Reuse aux[0]. But must uncompute C0 first?
        # No, because C1 depends on C0.
        # We are trapped if we don't have enough ancilla?
        # No, we can trickle uncompute.
        # But we need C2 for Bit 3 logic.
        # Wait, Step 3 logic:
        # We need C2 to add to Bit 3.
        # Can we compute C2 without erasing C0?
        # We have aux[0] (C0) and aux[2] (C1).
        # We need another qubit for C2?
        # Or overwrite C0? If we overwrite C0, we can never uncompute C1.
        # Unless we can RECOMPUTE C0 from b[0] and ctrl.
        # Yes, C0 = (b[0] ^ ctrl) & ctrl? No.
        # b[0]_new = b[0]_old ^ ctrl.
        # b[0]_old = b[0]_new ^ ctrl.
        # C0 = b[0]_old & ctrl.
        # So yes, we can recompute C0 whenever needed.
        
        # So overwrite aux[0] with C2.
        # Uncompute C0 logic (Clear aux[0]):
        # C0 is currently in aux[0]. We need to clear it to use aux[0] for C2.
        # But C1 needs C0 value? No, C1 is already computed in aux[2].
        # Does C1 need C0 to stay active? No. The value is latched in aux[2].
        # Does UNCOMPUTING C1 later need C0? Yes.
        # So we can clear C0 now, use aux[0] for C2, then uncompute C2, then RECOMPUTE C0 to uncompute C1?
        # Yes!
        
        # Clear C0 (using b[0], ctrl)
        # Logic: C0 = b[0]_old & ctrl.
        # Restore b[0]_old
        qc.cx(ctrl, reg_b[0]) 
        qc.ccx(reg_b[0], ctrl, reg_aux[0]) # Uncompute C0
        qc.cx(ctrl, reg_b[0]) # Restore b[0]_new
        
        # Now aux[0] is free. Use for C2.
        # C2 = b[2] & C1 -> aux[0]
        qc.ccx(reg_b[2], reg_aux[2], reg_aux[0])
        qc.cx(reg_aux[2], reg_b[2]) # Sum2
        
        # Bit 3: b[3] += 1 + C2
        qc.cx(ctrl, reg_b[3]) # Add 1
        qc.cx(reg_aux[0], reg_b[3]) # Add C2
        
        # Uncompute C2 (in aux[0])
        qc.cx(reg_aux[2], reg_b[2]) # Restore b[2] (Sum2 ^ C1 -> b[2]_old)
        qc.ccx(reg_b[2], reg_aux[2], reg_aux[0]) # Uncompute C2
        qc.cx(reg_aux[2], reg_b[2]) # Restore Sum2
        
        # Uncompute C1 (in aux[2]). Needs C0 (in aux[0], currently 0).
        # Recompute C0 into aux[0].
        qc.cx(ctrl, reg_b[0]) # b[0]_old
        qc.ccx(reg_b[0], ctrl, reg_aux[0]) # Recompute C0
        qc.cx(ctrl, reg_b[0]) # b[0]_new
        
        # Uncompute C1
        qc.cx(reg_aux[0], reg_b[1]) # Restore b[1] (Sum1 ^ C0)
        qc.ccx(reg_b[1], reg_aux[0], reg_aux[2]) # Uncompute C1
        qc.cx(reg_aux[0], reg_b[1]) # Restore Sum1
        
        # Uncompute C0
        qc.cx(ctrl, reg_b[0])
        qc.ccx(reg_b[0], ctrl, reg_aux[0])
        qc.cx(ctrl, reg_b[0])
        
        # Now b is updated (mod 7). Bit 3 should be 0.
        # Flag is still in aux[1].
        
        # --- Step 4: Uncompute Flag ---
        # Flag (aux[1]) logic: Flag <=> (b_new < a).
        # We compute borrow sequence of (b - a).
        # br[0] -> aux[0]
        # br[1] -> aux[2]
        # br[2] -> updates aux[1] (XOR)
        
        # Bit 0 Borrow: br[0] = !b[0] & a[0]
        qc.x(reg_b[0])
        qc.ccx(reg_b[0], reg_a[0], reg_aux[0]) 
        qc.x(reg_b[0])
        
        # Bit 1 Borrow: br[1] = maj(!b[1], a[1], br[0])
        # Ripple Borrow Logic used in Step 1 but dual.
        # P = !b[1] ^ a[1].
        # Gen = !b[1] & a[1].
        # br[1] = Gen | (P & br[0]).
        # Compute P into a[1] temporarily? No, standard logic.
        qc.x(reg_b[1])
        qc.ccx(reg_b[1], reg_a[1], reg_aux[2]) # Gen -> aux[2]
        qc.cx(reg_b[1], reg_a[1]) # P -> a[1]
        qc.ccx(reg_a[1], reg_aux[0], reg_aux[2]) # OR (P & br[0]) -> aux[2]
        qc.cx(reg_b[1], reg_a[1]) # Restore a[1]
        qc.x(reg_b[1])
        
        # Bit 2 Borrow: br[2] = maj(!b[2], a[2], br[1])
        # We want to XOR br[2] into aux[1] (Flag).
        # If Logic is correct, aux[1] will become 0.
        qc.x(reg_b[2])
        qc.ccx(reg_b[2], reg_a[2], reg_aux[1]) # Gen -> XOR Flag
        qc.cx(reg_b[2], reg_a[2]) # P
        qc.ccx(reg_a[2], reg_aux[2], reg_aux[1]) # Prop&Cin -> XOR Flag
        qc.cx(reg_b[2], reg_a[2]) # Restore a[2]
        qc.x(reg_b[2])
        
        # Uncompute br[1] (aux[2])
        # Need P again?
        qc.x(reg_b[1])
        qc.cx(reg_b[1], reg_a[1]) # P
        qc.ccx(reg_a[1], reg_aux[0], reg_aux[2]) # Uncompute Prop&Cin
        qc.cx(reg_b[1], reg_a[1]) # Restore a[1]
        qc.ccx(reg_b[1], reg_a[1], reg_aux[2]) # Uncompute Gen
        qc.x(reg_b[1])
        
        # Uncompute br[0] (aux[0])
        qc.x(reg_b[0])
        qc.ccx(reg_b[0], reg_a[0], reg_aux[0])
        qc.x(reg_b[0])
        
        # Done. aux is fully clean.

