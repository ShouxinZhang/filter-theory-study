import { setGlobalOptions } from 'firebase-functions/v2';
import { onCall, HttpsError, CallableRequest } from 'firebase-functions/v2/https';
import { initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import * as L from './logic';

// Keep costs bounded: small max instance count, one region.
setGlobalOptions({ region: 'us-central1', maxInstances: 5, memory: '256MiB' });

initializeApp();
const db = getFirestore();

function requireUid(req: CallableRequest): string {
  if (!req.auth) throw new HttpsError('unauthenticated', '请先登录');
  return req.auth.uid;
}

function displayName(req: CallableRequest): string {
  const tokenName = req.auth?.token?.name;
  return typeof tokenName === 'string' && tokenName ? tokenName : `游客${req.auth!.uid.slice(0, 4)}`;
}

/** Run a pure game mutation inside a Firestore transaction using the server clock. */
async function mutate<T>(uid: string, fn: (s: L.PlayerState, now: number) => L.Mutation<T>) {
  return db.runTransaction(async (tx) => {
    const ref = db.doc(`players/${uid}`);
    const snap = await tx.get(ref);
    if (!snap.exists) throw new HttpsError('failed-precondition', '存档不存在，请刷新页面');
    const now = Date.now();
    try {
      const { state, result } = fn(snap.data() as L.PlayerState, now);
      tx.set(ref, state);
      return { ...result, serverNow: now };
    } catch (e) {
      if (e instanceof L.GameError) throw new HttpsError('failed-precondition', e.message, { code: e.code });
      throw e;
    }
  });
}

export const ensurePlayer = onCall(async (req) => {
  const uid = requireUid(req);
  const name = displayName(req);
  const isGuest = req.auth?.token?.firebase?.sign_in_provider === 'anonymous';
  return db.runTransaction(async (tx) => {
    const ref = db.doc(`players/${uid}`);
    const snap = await tx.get(ref);
    const now = Date.now();
    if (!snap.exists) {
      tx.set(ref, L.newPlayer(name, now));
      return { created: true, serverNow: now };
    }
    // Guest linked a Google account: adopt the real name.
    if (!isGuest && snap.get('name') !== name) tx.update(ref, { name, updatedAt: now });
    return { created: false, serverNow: now };
  });
});

export const buySeed = onCall((req) =>
  mutate(requireUid(req), (s, now) => L.buySeed(s, req.data?.cropId, req.data?.qty, now)),
);

export const plant = onCall((req) =>
  mutate(requireUid(req), (s, now) => L.plant(s, req.data?.plot, req.data?.cropId, now)),
);

export const harvest = onCall((req) =>
  mutate(requireUid(req), (s, now) => L.harvest(s, req.data?.plots, now)),
);

export const sell = onCall((req) =>
  mutate(requireUid(req), (s, now) => L.sell(s, req.data?.cropId, req.data?.qty, now)),
);
