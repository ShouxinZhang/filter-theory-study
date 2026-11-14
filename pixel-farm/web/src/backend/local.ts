import * as L from '../../../functions/src/logic';
import type { Backend, UserInfo } from './index';

const SAVE_KEY = 'pixelfarm.save.v1';
const USER_KEY = 'pixelfarm.user.v1';

/** Offline mode: same rules, stored in localStorage. Useful for development/preview. */
export class LocalBackend implements Backend {
  readonly mode = 'local' as const;
  private user: UserInfo | null = JSON.parse(localStorage.getItem(USER_KEY) || 'null');
  private authCbs: ((u: UserInfo | null) => void)[] = [];
  private playerCbs = new Set<(s: L.PlayerState) => void>();

  onAuth(cb: (u: UserInfo | null) => void) {
    this.authCbs.push(cb);
    queueMicrotask(() => cb(this.user));
  }

  private setUser(u: UserInfo | null) {
    this.user = u;
    if (u) localStorage.setItem(USER_KEY, JSON.stringify(u));
    else localStorage.removeItem(USER_KEY);
    this.authCbs.forEach((cb) => cb(u));
  }

  async signInGuest() {
    this.setUser({ uid: 'local', name: '本地农场主', isGuest: true });
  }
  async signInGoogle() {
    throw new Error('本地模式不支持 Google 登录，请点“游客试玩”');
  }
  async linkGoogle() {
    throw new Error('本地模式不支持绑定账号');
  }
  async signOut() {
    this.setUser(null);
  }

  private load(): L.PlayerState | null {
    return JSON.parse(localStorage.getItem(SAVE_KEY) || 'null');
  }
  private save(s: L.PlayerState) {
    localStorage.setItem(SAVE_KEY, JSON.stringify(s));
    this.playerCbs.forEach((cb) => cb(s));
  }

  async start() {
    if (!this.load()) this.save(L.newPlayer(this.user?.name ?? '农场主', Date.now()));
  }

  onPlayer(cb: (s: L.PlayerState) => void) {
    this.playerCbs.add(cb);
    const s = this.load();
    if (s) cb(s);
    return () => this.playerCbs.delete(cb);
  }

  now() {
    return Date.now();
  }

  private mutate<T>(fn: (s: L.PlayerState, now: number) => L.Mutation<T>): T {
    const { state, result } = fn(this.load()!, Date.now());
    this.save(state);
    return result;
  }

  async buySeed(cropId: L.CropId, qty: number) {
    this.mutate((s, now) => L.buySeed(s, cropId, qty, now));
  }
  async plant(plot: number, cropId: L.CropId) {
    this.mutate((s, now) => L.plant(s, plot, cropId, now));
  }
  async harvest(plots: number[] | 'all') {
    return this.mutate((s, now) => L.harvest(s, plots, now));
  }
  async sell(cropId: L.CropId | 'all', qty: number | 'all') {
    return this.mutate((s, now) => L.sell(s, cropId, qty, now));
  }
}
