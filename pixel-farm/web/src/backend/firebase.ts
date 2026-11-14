import { initializeApp } from 'firebase/app';
import {
  getAuth, onAuthStateChanged, signInAnonymously, signInWithPopup, linkWithPopup, GoogleAuthProvider,
  signOut, connectAuthEmulator, type User,
} from 'firebase/auth';
import { getFirestore, doc, onSnapshot, connectFirestoreEmulator } from 'firebase/firestore';
import { getFunctions, httpsCallable, connectFunctionsEmulator } from 'firebase/functions';
import type { CropId, HarvestResult, PlayerState } from '../../../functions/src/logic';
import type { Backend, UserInfo } from './index';

const env = import.meta.env;
const useEmulator = env.VITE_USE_EMULATOR === 'true';
const projectId = env.VITE_FIREBASE_PROJECT_ID || 'demo-pixel-farm';

const app = initializeApp({
  apiKey: env.VITE_FIREBASE_API_KEY || 'demo-api-key',
  authDomain: env.VITE_FIREBASE_AUTH_DOMAIN || `${projectId}.firebaseapp.com`,
  projectId,
  appId: env.VITE_FIREBASE_APP_ID,
});
const auth = getAuth(app);
const db = getFirestore(app);
const fns = getFunctions(app, 'us-central1');

if (useEmulator) {
  const host = env.VITE_EMULATOR_HOST || 'localhost';
  connectAuthEmulator(auth, `http://${host}:9099`, { disableWarnings: true });
  connectFirestoreEmulator(db, host, 8080);
  connectFunctionsEmulator(fns, host, 5001);
}

function toUser(u: User): UserInfo {
  return { uid: u.uid, name: u.displayName || `游客${u.uid.slice(0, 4)}`, isGuest: u.isAnonymous };
}

export class FirebaseBackend implements Backend {
  readonly mode = 'firebase' as const;
  private offset = 0;

  onAuth(cb: (u: UserInfo | null) => void) {
    onAuthStateChanged(auth, (u) => cb(u ? toUser(u) : null));
  }

  async signInGoogle() {
    await signInWithPopup(auth, new GoogleAuthProvider());
  }
  async signInGuest() {
    await signInAnonymously(auth);
  }
  async linkGoogle() {
    if (!auth.currentUser) return;
    try {
      await linkWithPopup(auth.currentUser, new GoogleAuthProvider());
      await auth.currentUser.getIdToken(true); // refresh token so the server sees the new name
      await this.call('ensurePlayer', {});
    } catch (e: any) {
      if (e?.code === 'auth/credential-already-in-use') throw new Error('这个 Google 账号已经有存档了');
      throw e;
    }
  }
  async signOut() {
    await signOut(auth);
  }

  private async call<T>(name: string, data: unknown): Promise<T> {
    try {
      const res = await httpsCallable(fns, name)(data);
      const d = res.data as T & { serverNow?: number };
      if (typeof d?.serverNow === 'number') this.offset = d.serverNow - Date.now();
      return d;
    } catch (e: any) {
      throw new Error(e?.message || '网络错误');
    }
  }

  async start() {
    await this.call('ensurePlayer', {});
  }

  onPlayer(cb: (s: PlayerState) => void) {
    const uid = auth.currentUser!.uid;
    return onSnapshot(doc(db, 'players', uid), (snap) => {
      if (snap.exists()) cb(snap.data() as PlayerState);
    });
  }

  now() {
    return Date.now() + this.offset;
  }

  async buySeed(cropId: CropId, qty: number) {
    await this.call('buySeed', { cropId, qty });
  }
  async plant(plot: number, cropId: CropId) {
    await this.call('plant', { plot, cropId });
  }
  harvest(plots: number[] | 'all') {
    return this.call<HarvestResult>('harvest', { plots });
  }
  sell(cropId: CropId | 'all', qty: number | 'all') {
    return this.call<{ earned: number; sold: number }>('sell', { cropId, qty });
  }
}
