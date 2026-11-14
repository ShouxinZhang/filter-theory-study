import Phaser from 'phaser';
import './style.css';
import {
  CROPS, CROP_IDS, xpToNext, plotsForLevel, unlockLevelForPlot, cropProgress, remainingMs, formatDuration,
  type CropId, type PlayerState,
} from '../../functions/src/logic';
import { createBackend, type Backend, type UserInfo } from './backend';
import { FarmScene, W, H } from './FarmScene';
import { cropIcon, coinIcon } from './sprites';

type Tool = 'harvest' | CropId;
type ModalKind = 'shop' | 'barn' | null;

const $ = <T extends HTMLElement = HTMLElement>(sel: string) => document.querySelector(sel) as T;
const esc = (s: string) => s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

let backend: Backend;
let user: UserInfo | null = null;
let state: PlayerState | null = null;
let tool: Tool = 'harvest';
let modal: ModalKind = null;
let unsubPlayer: (() => void) | null = null;
let game: Phaser.Game | null = null;
const pending = new Set<number>();

const scene = new FarmScene({
  getState: () => state,
  now: () => backend.now(),
  isPending: (i) => pending.has(i),
  onPlotClick,
});

// ---------- feedback ----------
function toast(msg: string, kind: 'info' | 'error' | 'good' = 'info') {
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => el.classList.add('out'), 2200);
  setTimeout(() => el.remove(), 2600);
}

async function run<T>(fn: () => Promise<T>): Promise<T | undefined> {
  try {
    return await fn();
  } catch (e: any) {
    toast(e?.message || String(e), 'error');
    return undefined;
  }
}

// ---------- gameplay ----------
async function onPlotClick(i: number) {
  if (!state || pending.has(i)) return;
  const now = backend.now();
  if (i >= plotsForLevel(state.level)) return toast(`这块地 Lv${unlockLevelForPlot(i)} 解锁`);
  const plot = state.plots[i];

  if (!plot.cropId) {
    if (tool === 'harvest') return toast('先在下方选一种种子，再点空地播种');
    const crop = CROPS[tool];
    if ((state.seeds[tool] ?? 0) < 1) {
      toast(`没有${crop.name}种子了，去商店买点吧`);
      return openModal('shop');
    }
    pending.add(i);
    const ok = await run(() => backend.plant(i, tool as CropId));
    pending.delete(i);
    if (ok !== undefined) scene.floatText(i, `种下${crop.name}`, '#9be15d');
    return;
  }

  if (cropProgress(plot, now) < 1) {
    return toast(`${CROPS[plot.cropId].name}还需 ${formatDuration(remainingMs(plot, now))}`);
  }

  pending.add(i);
  const res = await run(() => backend.harvest([i]));
  pending.delete(i);
  if (res) showHarvest(res);
}

function showHarvest(res: Awaited<ReturnType<Backend['harvest']>>) {
  for (const h of res.harvested) scene.floatText(h.plot, `+${h.count} ${CROPS[h.cropId].name}`);
}

async function harvestAll() {
  const res = await run(() => backend.harvest('all'));
  if (res) {
    showHarvest(res);
    toast(`收获了 ${res.harvested.length} 块地，+${res.xpGained} 经验`, 'good');
  }
}

// ---------- rendering ----------
function renderHud() {
  if (!state || !user) return;
  const need = xpToNext(state.level);
  $('#hud-name').textContent = state.name;
  $('#hud-level').textContent = `Lv${state.level}`;
  $('#hud-xp-fill').style.width = `${Math.min(100, (state.xp / need) * 100)}%`;
  $('#hud-xp-text').textContent = `${state.xp}/${need}`;
  $('#hud-coins').textContent = String(state.coins);
  $('#btn-link').hidden = !(user.isGuest && backend.mode === 'firebase');
}

function renderToolbar() {
  if (!state) return;
  const s = state;
  const seedsHtml = CROP_IDS.filter((id) => s.level >= CROPS[id].unlockLevel)
    .map((id) => {
      const n = s.seeds[id] ?? 0;
      return `<button class="tool ${tool === id ? 'active' : ''} ${n ? '' : 'empty'}" data-tool="${id}" title="${CROPS[id].name}种子">
        <img src="${cropIcon(id)}" alt=""><span class="badge">${n}</span></button>`;
    })
    .join('');
  $('#tools').innerHTML = `
    <button class="tool ${tool === 'harvest' ? 'active' : ''}" data-tool="harvest" title="收获">✋</button>
    <span class="sep"></span>${seedsHtml}`;
  const now = backend.now();
  const ready = s.plots.some((p, i) => i < plotsForLevel(s.level) && p.cropId && cropProgress(p, now) >= 1);
  $<HTMLButtonElement>('#btn-harvest-all').classList.toggle('glow', ready);
}

function openModal(kind: ModalKind) {
  modal = kind;
  $('#modal').hidden = !kind;
  renderModal();
}

function renderModal() {
  if (!modal || !state) return;
  const s = state;
  const title = $('#modal-title');
  const body = $('#modal-body');
  const coin = `<img class="coin" src="${coinIcon()}" alt="金币">`;

  if (modal === 'shop') {
    title.textContent = '种子商店';
    body.innerHTML = CROP_IDS.map((id) => {
      const c = CROPS[id];
      const locked = s.level < c.unlockLevel;
      const buy = (q: number) =>
        `<button class="btn small" data-buy="${id}" data-qty="${q}" ${locked || s.coins < c.seedPrice * q ? 'disabled' : ''}>买${q}</button>`;
      return `<div class="row ${locked ? 'locked' : ''}">
        <img class="icon" src="${cropIcon(id)}" alt="">
        <div class="info">
          <b>${c.name}</b> <span class="muted">已有 ${s.seeds[id] ?? 0}</span><br>
          <small>${c.seedPrice}${coin} · ${formatDuration(c.growMs)} 成熟 · 收 ${c.yield}个×${c.sellPrice}${coin} · +${c.xp}经验</small>
        </div>
        <div class="actions">${locked ? `<span class="muted">Lv${c.unlockLevel} 解锁</span>` : buy(1) + buy(5) + buy(10)}</div>
      </div>`;
    }).join('');
  } else {
    title.textContent = '仓库';
    const items = CROP_IDS.filter((id) => (s.inventory[id] ?? 0) > 0);
    const total = items.reduce((sum, id) => sum + (s.inventory[id] ?? 0) * CROPS[id].sellPrice, 0);
    body.innerHTML = items.length
      ? items.map((id) => {
          const n = s.inventory[id]!;
          return `<div class="row">
            <img class="icon" src="${cropIcon(id)}" alt="">
            <div class="info"><b>${CROPS[id].name}</b> ×${n}<br><small>单价 ${CROPS[id].sellPrice}${coin}</small></div>
            <div class="actions">
              <button class="btn small" data-sell="${id}" data-qty="1">卖1</button>
              <button class="btn small" data-sell="${id}" data-qty="all">全卖 (${n * CROPS[id].sellPrice})</button>
            </div></div>`;
        }).join('') + `<div class="row total"><button class="btn" data-sell="all" data-qty="all">全部卖出 · ${total}${coin}</button></div>`
      : '<p class="muted center">仓库空空的，快去收获吧！</p>';
  }
}

function onState(s: PlayerState) {
  const prevLevel = state?.level;
  state = s;
  if (prevLevel && s.level > prevLevel) toast(`升级啦！Lv${s.level}，解锁了新地块/作物`, 'good');
  renderHud();
  renderToolbar();
  renderModal();
}

// ---------- screens ----------
async function onAuth(u: UserInfo | null) {
  user = u;
  unsubPlayer?.();
  unsubPlayer = null;
  state = null;
  $('#login').hidden = !!u;
  $('#game').hidden = !u;
  if (!u) return;

  const ok = await run(() => backend.start());
  if (ok === undefined && backend.mode === 'firebase') return;
  unsubPlayer = backend.onPlayer(onState);
  if (!game) {
    game = new Phaser.Game({
      type: Phaser.AUTO,
      parent: 'stage',
      width: W,
      height: H,
      pixelArt: true,
      backgroundColor: '#5fae3c',
      scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
      scene,
    });
  }
}

function bindUi() {
  $('#btn-google').onclick = () => run(() => backend.signInGoogle());
  $('#btn-guest').onclick = () => run(() => backend.signInGuest());
  $('#btn-logout').onclick = () => run(() => backend.signOut());
  $('#btn-link').onclick = async () => {
    const r = await run(() => backend.linkGoogle());
    if (r !== undefined) toast('已绑定 Google 账号，存档已保存', 'good');
  };
  $('#btn-shop').onclick = () => openModal('shop');
  $('#btn-barn').onclick = () => openModal('barn');
  $('#btn-harvest-all').onclick = harvestAll;
  $('#modal-close').onclick = () => openModal(null);
  $('#modal').onclick = (e) => e.target === $('#modal') && openModal(null);

  $('#tools').onclick = (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLElement>('[data-tool]');
    if (!btn || !state) return;
    const t = btn.dataset.tool as Tool;
    if (t !== 'harvest' && !(state.seeds[t] ?? 0)) {
      toast(`没有${CROPS[t].name}种子，去商店买吧`);
      return openModal('shop');
    }
    tool = t;
    renderToolbar();
  };

  $('#modal-body').onclick = async (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>('button');
    if (!btn || btn.disabled) return;
    btn.disabled = true;
    if (btn.dataset.buy) {
      const id = btn.dataset.buy as CropId;
      const qty = Number(btn.dataset.qty);
      const r = await run(() => backend.buySeed(id, qty));
      if (r !== undefined) {
        toast(`买了 ${qty} 个${CROPS[id].name}种子`, 'good');
        tool = id;
        renderToolbar();
      }
    } else if (btn.dataset.sell) {
      const id = btn.dataset.sell as CropId | 'all';
      const qty = btn.dataset.qty === 'all' ? 'all' : Number(btn.dataset.qty);
      const r = await run(() => backend.sell(id, qty));
      if (r) toast(`卖出 ${r.sold} 个，+${r.earned} 金币`, 'good');
    }
    btn.disabled = false;
  };

  // refresh "harvest all" glow as crops ripen
  setInterval(renderToolbar, 1000);
}

async function main() {
  $('#coin-icon').setAttribute('src', coinIcon());
  backend = await createBackend();
  $('#mode-note').textContent =
    backend.mode === 'local' ? '本地模式：存档保存在当前浏览器' : '云端存档 · 换设备也能继续玩';
  if (backend.mode === 'local') $('#btn-google').hidden = true;
  bindUi();
  backend.onAuth(onAuth);
}

main();
