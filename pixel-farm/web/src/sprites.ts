import type Phaser from 'phaser';
import type { CropId } from '../../functions/src/logic';

/** Hand-drawn 16x16 pixel art. Each char maps to a palette colour; '.' = transparent. */
export const PALETTE: Record<string, string> = {
  k: '#2b1d14', // outline
  g: '#2f6b2f', // dark green
  G: '#4caf50', // green
  L: '#9be15d', // light green
  o: '#c4561a', // dark orange
  O: '#ff8c2a', // orange
  r: '#a3222b', // dark red
  R: '#e83b3b', // red
  y: '#c99a1e', // dark yellow
  Y: '#f7d84a', // yellow
  W: '#fff3b0', // pale highlight
  p: '#c2541b', // pumpkin dark
  P: '#f5902c', // pumpkin
  s: '#e0303f', // strawberry
  w: '#fff6d0', // seeds / sparkle
  b: '#6b4423', // brown
  B: '#8f5d32', // light brown
  m: '#9aa3ad', // metal
  M: '#d6dde4', // metal light
};

const SPRITES: Record<string, string[]> = {
  sprout: [
    '.......L........',
    '.....LgG.L......',
    '......gGgL......',
    '.......g........',
    '.......b........',
  ],
  growing: [
    '.......G........',
    '.....G.GL.G.....',
    '.....GgGgLG.....',
    '......gGgG......',
    '...L...gG...L...',
    '...gG..gG..Gg...',
    '....gGgGgGgG....',
    '......gGgG......',
    '.......gg.......',
    '................',
  ],
  crop_carrot: [
    '.....g...g......',
    '....gLg.gLg.....',
    '.....gGgGg..g...',
    '...g..gGg..gLg..',
    '..gLg..gG.gGg...',
    '...gGg.gGgGg....',
    '....gGgGgGg.....',
    '......gGg.......',
    '.....oOOOo......',
    '.....oOWOo......',
    '......oOo.......',
    '......oo........',
    '................',
  ],
  crop_wheat: [
    '....Y...Y...Y...',
    '...YWY.YWY.YWY..',
    '...yYy.yYy.yYy..',
    '...YyY.YyY.YyY..',
    '...yYy.yYy.yYy..',
    '....y...y...y...',
    '....g...G...g...',
    '...Gg..gG..gG...',
    '....gG.gG.Gg....',
    '.....gGgGgG.....',
    '......gGgG......',
    '.......gg.......',
    '................',
  ],
  crop_tomato: [
    '.......G.G......',
    '......gGgGg.....',
    '....RR.gG.......',
    '...RWRRgGgRR....',
    '...RRRr.gGRWRR..',
    '....rr.gGgRRRR..',
    '......gGg..rr...',
    '...gG.gG.Gg.....',
    '..RRgGgGgG......',
    '..RWR.gGg.......',
    '...r..gG........',
    '.....gGgG.......',
    '......gg........',
    '................',
  ],
  crop_corn: [
    '.......gL.......',
    '......YYYg......',
    '.....gYWYG......',
    '.....gYyYG......',
    '....GgYYYGg.....',
    '...Gg.YyY.gG....',
    '..G...yYy...G...',
    '......gYg.......',
    '.....gGgGg......',
    '....gG.g.Gg.....',
    '...G...g...G....',
    '.......g........',
    '......gg........',
    '................',
  ],
  crop_pumpkin: [
    '.......b........',
    '......bg.G......',
    '.....Gg.GgL.....',
    '...pPPpPPpPPp...',
    '..pPWpPPPpPPPp..',
    '..PPPpPPPpPPPP..',
    '..PPPpPPPpPPPP..',
    '..pPPpPPPpPPPp..',
    '...pPPpPPpPPp...',
    '....ppppppppp...',
    '................',
  ],
  crop_strawberry: [
    '......G..G......',
    '....gGgGgGgG....',
    '...GgsGg.gGsG...',
    '...g.ss.g.ssg...',
    '..sssw..gsswss..',
    '..swss.g.sswss..',
    '..ssss..gGsss...',
    '...ss..gGg.s....',
    '....GgGgGgG.....',
    '.....gGgGg......',
    '......gg........',
    '................',
  ],
  tree: [
    '.....gGGg.......',
    '...gGGLGGGg.....',
    '..gGLLGGGGGg....',
    '..GGLGGGGGGg....',
    '.gGGGGGGGgGGg...',
    '.gGGGGGGGGGgg...',
    '..gGGGGGGGgg....',
    '...ggGGGggg.....',
    '.....gbbg.......',
    '......bb........',
    '......bb........',
    '.....bbbb.......',
  ],
  lock: [
    '................',
    '................',
    '................',
    '......mmmm......',
    '.....m....m.....',
    '.....m....m.....',
    '....yYYYYYYy....',
    '....YYYkkYYY....',
    '....YYYkkYYY....',
    '....YYYYkYYY....',
    '....yYYYYYYy....',
    '.....yyyyyy.....',
    '................',
    '................',
  ],
};

const COIN = [
  '..yyyy..',
  '.yYYYYy.',
  'yYYWYYYy',
  'yYWYYYYy',
  'yYYYYYYy',
  'yYYYYYYy',
  '.yYYYYy.',
  '..yyyy..',
];

function canvas(w: number, h: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return [c, c.getContext('2d')!];
}

export function drawRows(rows: string[], w = 16, h = 16): HTMLCanvasElement {
  const [c, ctx] = canvas(w, h);
  const padTop = Math.max(0, h - rows.length); // bottom-align (plants sit on the soil)
  rows.slice(0, h).forEach((row, y) => {
    for (let x = 0; x < Math.min(row.length, w); x++) {
      const col = PALETTE[row[x]];
      if (col) {
        ctx.fillStyle = col;
        ctx.fillRect(x, y + padTop, 1, 1);
      }
    }
  });
  return c;
}

function rng(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function grassTile(seed: number): HTMLCanvasElement {
  const [c, ctx] = canvas(16, 16);
  const r = rng(seed);
  ctx.fillStyle = '#5fae3c';
  ctx.fillRect(0, 0, 16, 16);
  for (let i = 0; i < 22; i++) {
    ctx.fillStyle = r() < 0.6 ? '#4e9a30' : '#79c94f';
    ctx.fillRect(Math.floor(r() * 16), Math.floor(r() * 16), 1, r() < 0.3 ? 2 : 1);
  }
  if (seed % 5 === 0) {
    // tiny flower
    const x = 3 + Math.floor(r() * 10);
    const y = 3 + Math.floor(r() * 10);
    ctx.fillStyle = r() < 0.5 ? '#fff6d0' : '#ff9ecb';
    ctx.fillRect(x - 1, y, 3, 1);
    ctx.fillRect(x, y - 1, 1, 3);
    ctx.fillStyle = '#f7d84a';
    ctx.fillRect(x, y, 1, 1);
  }
  return c;
}

function soilTile(): HTMLCanvasElement {
  const [c, ctx] = canvas(16, 16);
  const r = rng(42);
  ctx.fillStyle = '#5a3519';
  ctx.fillRect(0, 0, 16, 16);
  ctx.fillStyle = '#8a5a2e';
  ctx.fillRect(1, 1, 14, 14);
  for (const y of [3, 7, 11]) {
    ctx.fillStyle = '#6b4220';
    ctx.fillRect(2, y + 1, 12, 1);
    ctx.fillStyle = '#a06c3a';
    for (let x = 2; x < 14; x++) if (r() < 0.5) ctx.fillRect(x, y, 1, 1);
  }
  return c;
}

/** Register all generated textures with a Phaser scene. */
export function buildTextures(scene: Phaser.Scene) {
  const add = (key: string, c: HTMLCanvasElement) => {
    if (!scene.textures.exists(key)) scene.textures.addCanvas(key, c);
  };
  for (let i = 0; i < 6; i++) add(`grass${i}`, grassTile(i + 1));
  add('soil', soilTile());
  for (const [key, rows] of Object.entries(SPRITES)) add(key, drawRows(rows));
}

// ---------- icons for the HTML UI ----------
const iconCache = new Map<string, string>();
function icon(key: string, make: () => HTMLCanvasElement): string {
  if (!iconCache.has(key)) iconCache.set(key, make().toDataURL());
  return iconCache.get(key)!;
}
export const cropIcon = (id: CropId) => icon(id, () => drawRows(SPRITES[`crop_${id}`]));
export const coinIcon = () => icon('coin', () => drawRows(COIN, 8, 8));
