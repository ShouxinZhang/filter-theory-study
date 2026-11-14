// End-to-end smoke test against the Firebase emulators.
// Run from repo root:  npx firebase emulators:exec --project demo-pixel-farm "node web/scripts/emulator-smoke.mjs"
import assert from 'node:assert/strict';
import { initializeApp } from 'firebase/app';
import { getAuth, connectAuthEmulator, signInAnonymously } from 'firebase/auth';
import { getFirestore, connectFirestoreEmulator, doc, getDoc, setDoc } from 'firebase/firestore';
import { getFunctions, connectFunctionsEmulator, httpsCallable } from 'firebase/functions';

const app = initializeApp({ apiKey: 'demo', projectId: 'demo-pixel-farm', authDomain: 'localhost' });
const auth = getAuth(app);
const db = getFirestore(app);
const fns = getFunctions(app, 'us-central1');
connectAuthEmulator(auth, 'http://127.0.0.1:9099', { disableWarnings: true });
connectFirestoreEmulator(db, '127.0.0.1', 8080);
connectFunctionsEmulator(fns, '127.0.0.1', 5001);
const call = (n, d) => httpsCallable(fns, n)(d).then((r) => r.data);

const { user } = await signInAnonymously(auth);
const ref = doc(db, 'players', user.uid);

assert.equal((await call('ensurePlayer', {})).created, true);
assert.equal((await call('ensurePlayer', {})).created, false);
let s = (await getDoc(ref)).data();
assert.equal(s.coins, 60);

await call('buySeed', { cropId: 'wheat', qty: 2 });
await call('plant', { plot: 0, cropId: 'carrot' });
s = (await getDoc(ref)).data();
assert.equal(s.coins, 40);
assert.equal(s.seeds.wheat, 2);
assert.equal(s.plots[0].cropId, 'carrot');

// server rejects early harvest
await assert.rejects(call('harvest', { plots: [0] }), /还没成熟/);
// server rejects bad input
await assert.rejects(call('buySeed', { cropId: 'carrot', qty: -5 }), /数量/);

// security rules: client cannot write its own save
await assert.rejects(setDoc(ref, { ...s, coins: 999999 }), /permission/i);
// and cannot read someone else's
await assert.rejects(getDoc(doc(db, 'players', 'someone-else')), /permission/i);

console.log('emulator smoke test passed ✔');
process.exit(0);
