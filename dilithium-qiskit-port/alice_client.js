/**
 * Alice Client - Node.js
 * 
 * Workflow:
 * 1. Generate keypair (offchain simulation)
 * 2. Export public key to publickey.json (JSON format)
 * 3. Read challenge from challenge.json (JSON format)
 * 4. Sign challenge
 * 5. Send signature to signature.json (JSON format)
 */

const fs = require('fs');
const path = require('path');

// Ensure data directory exists
const DATA_DIR = './data';
if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
}

const pubkeyFile = path.join(DATA_DIR, 'publickey.json');
const challengeFile = path.join(DATA_DIR, 'challenge.json');
const signatureFile = path.join(DATA_DIR, 'signature.json');

/**
 * Step 1: Generate Keypair and Export Public Key
 * 
 * Simulates Board's KeyGen:
 * - Creates secret keys (s1, s2)
 * - Creates public keys (A, t)
 * - Exports only public keys as JSON
 */
function generateAndExportPublicKey() {
    console.log('\n✅ [BOARD] KeyGen: Generating keypair...\n');
    
    // Generate random polynomial
    function randomPoly(n, bound) {
        return Array.from({ length: n }, () => Math.floor(Math.random() * bound));
    }
    
    const N = 4;  // Mini config (N=4)
    const q = 17; // Modulus
    
    // Secret keys (NOT exported)
    const s1 = randomPoly(N, 5);
    const s2 = randomPoly(N, 5);
    console.log(`  Secret s1: ${JSON.stringify(s1)} (NOT exported)`);
    console.log(`  Secret s2: ${JSON.stringify(s2)} (NOT exported)\n`);
    
    // Public keys
    const A = [randomPoly(N, q), randomPoly(N, q)];
    const t = randomPoly(N, q);
    
    console.log(`  Public A[0]: ${JSON.stringify(A[0])}`);
    console.log(`  Public A[1]: ${JSON.stringify(A[1])}`);
    console.log(`  Public t: ${JSON.stringify(t)}\n`);
    
    // Prepare export data as JSON
    const publicKeyJSON = {
        version: "1.0",
        protocol: "quantum-dilithium-auth",
        type: "public_key",
        sender: "board-client",
        timestamp: Math.floor(Date.now() / 1000),
        public_key: {
            A: A,
            t: t
        },
        metadata: {
            N: N,
            q: q,
            algorithm: "dilithium-mini"
        }
    };
    
    // Save as JSON file
    fs.writeFileSync(pubkeyFile, JSON.stringify(publicKeyJSON, null, 2));
    console.log(`� Exported public key to: ${pubkeyFile} (JSON format)\n`);
    
    // Store secret keys in memory (for later signing)
    return { s1, s2, N, q };
}

/**
 * Step 2: Read Challenge from JSON
 */
function readChallenge() {
    console.log('\n✅ [BOARD] Reading challenge from server...\n');
    
    if (!fs.existsSync(challengeFile)) {
        console.log(`⚠️  Challenge JSON file not found: ${challengeFile}`);
        console.log('   (Server needs to create challenge first)\n');
        return null;
    }
    
    try {
        const jsonContent = fs.readFileSync(challengeFile, 'utf8');
        const challengeJSON = JSON.parse(jsonContent);
        
        console.log(`📦 Challenge JSON received`);
        
        // Extract challenge data
        const challengeData = challengeJSON.challenge || {};
        const challengeId = challengeData.challenge_id;
        const c = challengeData.c;
        
        if (!challengeId || !c) {
            console.log('❌ Failed to extract challenge data from JSON\n');
            return null;
        }
        
        console.log(`   Challenge ID: ${challengeId}`);
        console.log(`   c: ${JSON.stringify(c)}\n`);
        
        return { challengeId, c };
    } catch (error) {
        console.log(`❌ Error reading/parsing challenge JSON: ${error}\n`);
        return null;
    }
}

/**
 * Step 3: Sign Challenge and Export Signature as JSON
 */
function signChallengeAndExport(secretKeys, challenge) {
    console.log('\n✅ [BOARD] Signing challenge...\n');
    
    if (!secretKeys || !challenge) {
        console.log('❌ Missing secret keys or challenge\n');
        return false;
    }
    
    const { s1, s2, N, q } = secretKeys;
    const { challengeId, c } = challenge;
    
    // Generate ephemeral y (simulation)
    function randomPoly(n, bound) {
        return Array.from({ length: n }, () => Math.floor(Math.random() * bound));
    }
    
    const y1 = randomPoly(N, 3);
    const y2 = randomPoly(N, 3);
    
    console.log(`  y1: ${JSON.stringify(y1)}`);
    console.log(`  y2: ${JSON.stringify(y2)}\n`);
    
    // Compute z = y + c*s (modulo q)
    function polyAdd(p1, p2, mod) {
        return p1.map((v, i) => (v + p2[i]) % mod);
    }
    
    const cs1 = s1.map(v => (c[0] * v) % q);
    const cs2 = s2.map(v => (c[0] * v) % q);
    
    const z1 = polyAdd(y1, cs1, q);
    const z2 = polyAdd(y2, cs2, q);
    const z = polyAdd(z1, z2, q);
    
    console.log(`  Signature z: ${JSON.stringify(z)}\n`);
    
    // Prepare signature as JSON
    const signatureJSON = {
        version: "1.0",
        protocol: "quantum-dilithium-auth",
        type: "signature",
        sender: "board-client",
        timestamp: Math.floor(Date.now() / 1000),
        signature: {
            challenge_id: challengeId,
            z: z,
            message: "Authenticate to quantum network"
        }
    };
    
    // Save as JSON file
    fs.writeFileSync(signatureFile, JSON.stringify(signatureJSON, null, 2));
    console.log(`📦 Signature saved to: ${signatureFile} (JSON format)\n`);
    
    return true;
}

/**
 * Main Workflow
 */
async function main() {
    console.log('═'.repeat(70));
    console.log('       BOARD CLIENT - QUANTUM DILITHIUM (LyCheeRVnano)');
    console.log('═'.repeat(70));
    
    // Phase 1: Generate and export public key
    const secretKeys = generateAndExportPublicKey();
    
    // Wait for user to run Python server
    console.log('⏳ Waiting for server to generate challenge...');
    console.log('   (Run: python run_test_dilithium.py)\n');
    
    // Check if challenge exists (polling)
    let challengeReady = false;
    let attempts = 0;
    const maxAttempts = 60; // 60 seconds
    
    while (!challengeReady && attempts < maxAttempts) {
        if (fs.existsSync(challengeFile)) {
            challengeReady = true;
            break;
        }
        await new Promise(resolve => setTimeout(resolve, 1000));
        attempts++;
    }
    
    if (!challengeReady) {
        console.log('❌ Challenge JSON file not received within timeout\n');
        return;
    }
    
    console.log('✅ Challenge JSON received!\n');
    
    // Phase 2: Read challenge
    const challenge = readChallenge();
    
    if (!challenge) {
        return;
    }
    
    // Phase 3: Sign and export
    const signed = signChallengeAndExport(secretKeys, challenge);
    
    if (signed) {
        console.log('═'.repeat(70));
        console.log('✅ BOARD CLIENT WORKFLOW COMPLETE');
        console.log('═'.repeat(70));
        console.log('\n⏳ Waiting for server to verify...');
        console.log('   (Check server output for verification result)\n');
    }
}

// Run main
main().catch(console.error);
