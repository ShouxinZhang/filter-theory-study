/**
 * Pure game rules shared by the Cloud Functions (authoritative server) and the
 * browser (local/offline mode + UI display). No Firebase imports here.
 *
 * All timestamps are epoch milliseconds. On the server they come from the
 * server clock, so clients cannot fast-forward crop growth.
 */

export type CropId = 'carrot' | 'wheat' | 'tomato' | 'corn' | 'pumpkin' | 'strawberry';

export interface CropDef {
  id: CropId;
  name: string;
  seedPrice: number;
  /** crops produced per harvest */
  yield: number;
  /** coins per crop when sold */
  sellPrice: number;
  growMs: number;
  /** xp per harvested plot */
  xp: number;
  unlockLevel: number;
}

const MIN = 60_000;

export const CROPS: Record<CropId, CropDef> = {
  carrot: { id: 'carrot', name: '胡萝卜', seedPrice: 5, yield: 2, sellPrice: 5, growMs: 1 * MIN, xp: 2, unlockLevel: 1 },
  wheat: { id: 'wheat', name: '小麦', seedPrice: 10, yield: 3, sellPrice: 6, growMs: 3 * MIN, xp: 4, unlockLevel: 1 },
  tomato: { id: 'tomato', name: '番茄', seedPrice: 25, yield: 3, sellPrice: 15, growMs: 10 * MIN, xp: 10, unlockLevel: 2 },
  corn: { id: 'corn', name: '玉米', seedPrice: 50, yield: 4, sellPrice: 22, growMs: 30 * MIN, xp: 20, unlockLevel: 3 },
  pumpkin: { id: 'pumpkin', name: '南瓜', seedPrice: 100, yield: 2, sellPrice: 110, growMs: 60 * MIN, xp: 40, unlockLevel: 5 },
  strawberry: { id: 'strawberry', name: '草莓', seedPrice: 200, yield: 5, sellPrice: 90, growMs: 120 * MIN, xp: 70, unlockLevel: 7 },
};

export const CROP_IDS = Object.keys(CROPS) as CropId[];
export const MAX_PLOTS = 12;
export const START_COINS = 60;
export const MAX_BUY = 99;

export interface Plot {
  cropId: CropId | null;
  plantedAt: number | null;
}

export type Counts = Partial<Record<CropId, number>>;

export interface PlayerState {
  name: string;
  coins: number;
  level: number;
  /** xp inside the current level (resets on level-up) */
  xp: number;
  seeds: Counts;
  inventory: Counts;
  plots: Plot[];
  createdAt: number;
  updatedAt: number;
}

export interface Mutation<T> {
  state: PlayerState;
  result: T;
}

export class GameError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'GameError';
  }
}

// ---------- derived values ----------

export function xpToNext(level: number): number {
  return 20 * level;
}

export function plotsForLevel(level: number): number {
  return Math.min(MAX_PLOTS, 5 + level);
}

export function unlockLevelForPlot(index: number): number {
  let lv = 1;
  while (plotsForLevel(lv) <= index) lv++;
  return lv;
}

export function isCropId(x: unknown): x is CropId {
  return typeof x === 'string' && Object.prototype.hasOwnProperty.call(CROPS, x);
}

export function cropProgress(plot: Plot, now: number): number {
  if (!plot.cropId || plot.plantedAt == null) return 0;
  const p = (now - plot.plantedAt) / CROPS[plot.cropId].growMs;
  return Math.max(0, Math.min(1, p));
}

export function isMature(plot: Plot, now: number): boolean {
  return !!plot.cropId && cropProgress(plot, now) >= 1;
}

export function remainingMs(plot: Plot, now: number): number {
  if (!plot.cropId || plot.plantedAt == null) return 0;
  return Math.max(0, plot.plantedAt + CROPS[plot.cropId].growMs - now);
}

export function formatDuration(ms: number): string {
  const total = Math.ceil(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n: number) => String(n).padStart(2, '0');
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

// ---------- helpers ----------

function clone(s: PlayerState): PlayerState {
  return JSON.parse(JSON.stringify(s)) as PlayerState;
}

function assertInt(x: unknown, min: number, max: number, what: string): number {
  if (typeof x !== 'number' || !Number.isInteger(x) || x < min || x > max) {
    throw new GameError('invalid-argument', `${what} 无效`);
  }
  return x;
}

function assertCrop(x: unknown): CropId {
  if (!isCropId(x)) throw new GameError('invalid-argument', '未知作物');
  return x;
}

function add(counts: Counts, id: CropId, n: number) {
  const v = (counts[id] ?? 0) + n;
  if (v > 0) counts[id] = v;
  else delete counts[id];
}

// ---------- state creation ----------

export function newPlayer(name: string, now: number): PlayerState {
  return {
    name: String(name).slice(0, 24) || '农场主',
    coins: START_COINS,
    level: 1,
    xp: 0,
    seeds: { carrot: 4 },
    inventory: {},
    plots: Array.from({ length: MAX_PLOTS }, () => ({ cropId: null, plantedAt: null })),
    createdAt: now,
    updatedAt: now,
  };
}

// ---------- mutations ----------

export function buySeed(s0: PlayerState, cropIdIn: unknown, qtyIn: unknown, now: number): Mutation<{ cost: number }> {
  const cropId = assertCrop(cropIdIn);
  const qty = assertInt(qtyIn, 1, MAX_BUY, '数量');
  const crop = CROPS[cropId];
  if (s0.level < crop.unlockLevel) throw new GameError('locked', `${crop.name} 需要 Lv${crop.unlockLevel}`);
  const cost = crop.seedPrice * qty;
  if (s0.coins < cost) throw new GameError('no-coins', '金币不足');
  const s = clone(s0);
  s.coins -= cost;
  add(s.seeds, cropId, qty);
  s.updatedAt = now;
  return { state: s, result: { cost } };
}

export function plant(s0: PlayerState, plotIn: unknown, cropIdIn: unknown, now: number): Mutation<{ plot: number }> {
  const cropId = assertCrop(cropIdIn);
  const plot = assertInt(plotIn, 0, MAX_PLOTS - 1, '地块');
  if (plot >= plotsForLevel(s0.level)) throw new GameError('locked', `该地块 Lv${unlockLevelForPlot(plot)} 解锁`);
  if (s0.plots[plot].cropId) throw new GameError('occupied', '这块地已经种了东西');
  if ((s0.seeds[cropId] ?? 0) < 1) throw new GameError('no-seeds', `没有${CROPS[cropId].name}种子了`);
  const s = clone(s0);
  add(s.seeds, cropId, -1);
  s.plots[plot] = { cropId, plantedAt: now };
  s.updatedAt = now;
  return { state: s, result: { plot } };
}

export interface HarvestResult {
  harvested: { plot: number; cropId: CropId; count: number }[];
  xpGained: number;
  levelUps: number;
}

export function harvest(s0: PlayerState, plotsIn: unknown, now: number): Mutation<HarvestResult> {
  const unlocked = plotsForLevel(s0.level);
  let targets: number[];
  if (plotsIn === 'all') {
    targets = s0.plots.map((_, i) => i).filter((i) => i < unlocked && isMature(s0.plots[i], now));
    if (targets.length === 0) throw new GameError('nothing', '没有可以收获的作物');
  } else {
    if (!Array.isArray(plotsIn) || plotsIn.length === 0 || plotsIn.length > MAX_PLOTS) {
      throw new GameError('invalid-argument', '地块无效');
    }
    targets = [...new Set(plotsIn.map((p) => assertInt(p, 0, unlocked - 1, '地块')))];
    for (const i of targets) {
      const p = s0.plots[i];
      if (!p.cropId) throw new GameError('empty', '这块地是空的');
      if (!isMature(p, now)) throw new GameError('not-ready', `${CROPS[p.cropId].name}还没成熟`);
    }
  }

  const s = clone(s0);
  const result: HarvestResult = { harvested: [], xpGained: 0, levelUps: 0 };
  for (const i of targets) {
    const crop = CROPS[s.plots[i].cropId as CropId];
    add(s.inventory, crop.id, crop.yield);
    result.harvested.push({ plot: i, cropId: crop.id, count: crop.yield });
    result.xpGained += crop.xp;
    s.plots[i] = { cropId: null, plantedAt: null };
  }
  s.xp += result.xpGained;
  while (s.xp >= xpToNext(s.level)) {
    s.xp -= xpToNext(s.level);
    s.level++;
    result.levelUps++;
  }
  s.updatedAt = now;
  return { state: s, result };
}

export function sell(s0: PlayerState, cropIdIn: unknown, qtyIn: unknown, now: number): Mutation<{ earned: number; sold: number }> {
  const s = clone(s0);
  let earned = 0;
  let sold = 0;
  if (cropIdIn === 'all') {
    for (const id of CROP_IDS) {
      const n = s.inventory[id] ?? 0;
      earned += n * CROPS[id].sellPrice;
      sold += n;
    }
    s.inventory = {};
  } else {
    const cropId = assertCrop(cropIdIn);
    const have = s.inventory[cropId] ?? 0;
    const qty = qtyIn === 'all' ? have : assertInt(qtyIn, 1, 1_000_000, '数量');
    if (qty < 1 || qty > have) throw new GameError('not-enough', '仓库里数量不足');
    add(s.inventory, cropId, -qty);
    earned = qty * CROPS[cropId].sellPrice;
    sold = qty;
  }
  if (sold === 0) throw new GameError('nothing', '仓库是空的');
  s.coins += earned;
  s.updatedAt = now;
  return { state: s, result: { earned, sold } };
}
