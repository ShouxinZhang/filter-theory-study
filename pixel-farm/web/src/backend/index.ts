import type { CropId, HarvestResult, PlayerState } from '../../../functions/src/logic';

export interface UserInfo {
  uid: string;
  name: string;
  isGuest: boolean;
}

export interface Backend {
  readonly mode: 'local' | 'firebase';
  onAuth(cb: (user: UserInfo | null) => void): void;
  signInGoogle(): Promise<void>;
  signInGuest(): Promise<void>;
  linkGoogle(): Promise<void>;
  signOut(): Promise<void>;
  /** Create the save if needed. Call after sign-in. */
  start(): Promise<void>;
  onPlayer(cb: (s: PlayerState) => void): () => void;
  /** Best estimate of the authoritative (server) clock. */
  now(): number;
  buySeed(cropId: CropId, qty: number): Promise<void>;
  plant(plot: number, cropId: CropId): Promise<void>;
  harvest(plots: number[] | 'all'): Promise<HarvestResult>;
  sell(cropId: CropId | 'all', qty: number | 'all'): Promise<{ earned: number; sold: number }>;
}

export async function createBackend(): Promise<Backend> {
  const env = import.meta.env;
  const hasFirebase = !!env.VITE_FIREBASE_API_KEY || env.VITE_USE_EMULATOR === 'true';
  if (env.VITE_BACKEND === 'local' || !hasFirebase) {
    const { LocalBackend } = await import('./local');
    return new LocalBackend();
  }
  const { FirebaseBackend } = await import('./firebase');
  return new FirebaseBackend();
}
