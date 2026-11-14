import Phaser from 'phaser';
import {
  CROPS, MAX_PLOTS, plotsForLevel, unlockLevelForPlot, cropProgress, remainingMs, formatDuration,
  type PlayerState,
} from '../../functions/src/logic';
import { buildTextures } from './sprites';

export interface FarmBridge {
  getState(): PlayerState | null;
  now(): number;
  isPending(i: number): boolean;
  onPlotClick(i: number): void;
}

export const W = 480;
export const H = 320;
const SCALE = 3;
const PLOT = 16 * SCALE;
const GAP = 14;
const COLS = 4;
const ROWS = MAX_PLOTS / COLS;
const FIELD_W = COLS * PLOT + (COLS - 1) * GAP;
const FIELD_H = ROWS * PLOT + (ROWS - 1) * GAP;
const FX = Math.round((W - FIELD_W) / 2);
const FY = 96;
const FONT = '"DotGothic16", "PingFang SC", "Microsoft YaHei", monospace';

interface PlotView {
  x: number;
  y: number;
  soil: Phaser.GameObjects.Image;
  crop: Phaser.GameObjects.Image;
  lock: Phaser.GameObjects.Image;
  bar: Phaser.GameObjects.Graphics;
  hl: Phaser.GameObjects.Graphics;
}

export class FarmScene extends Phaser.Scene {
  private views: PlotView[] = [];
  private hovered = -1;
  private tip!: Phaser.GameObjects.Text;
  private bridge: FarmBridge;

  constructor(bridge: FarmBridge) {
    super('farm');
    this.bridge = bridge;
  }

  create() {
    buildTextures(this);

    // grass background
    for (let y = 0; y < H / 32; y++) {
      for (let x = 0; x < W / 32; x++) {
        this.add.image(x * 32, y * 32, `grass${(x * 7 + y * 13) % 6}`).setOrigin(0).setScale(2);
      }
    }

    const g = this.add.graphics();
    // dirt path from the top
    g.fillStyle(0xc9a26b).fillRect(W / 2 - 16, 0, 32, FY - 18);
    g.fillStyle(0xb38b55).fillRect(W / 2 - 16, 0, 2, FY - 18).fillRect(W / 2 + 14, 0, 2, FY - 18);
    // field bed
    g.fillStyle(0x5a3519).fillRect(FX - 14, FY - 14, FIELD_W + 28, FIELD_H + 28);
    g.fillStyle(0x744a24).fillRect(FX - 12, FY - 12, FIELD_W + 24, FIELD_H + 24);
    this.drawFence(g, FX - 24, FY - 26, FIELD_W + 48, FIELD_H + 50);

    // trees
    for (const [x, y] of [[18, 30], [400, 22], [14, 230], [418, 228], [70, 4], [360, 250]]) {
      this.add.image(x, y, 'tree').setOrigin(0).setScale(SCALE);
    }

    // sign
    const sign = this.add.graphics();
    sign.fillStyle(0x5a3519).fillRect(W / 2 + 26, 18, 4, 30).fillRect(W / 2 + 84, 18, 4, 30);
    sign.fillStyle(0x8f5d32).fillRect(W / 2 + 22, 12, 70, 22);
    sign.fillStyle(0xb5824d).fillRect(W / 2 + 24, 14, 66, 18);
    this.add.text(W / 2 + 57, 23, '我的农场', { fontFamily: FONT, fontSize: '11px', color: '#3b2412' })
      .setOrigin(0.5).setResolution(4);

    for (let i = 0; i < MAX_PLOTS; i++) {
      const x = FX + (i % COLS) * (PLOT + GAP);
      const y = FY + Math.floor(i / COLS) * (PLOT + GAP);
      const soil = this.add.image(x, y, 'soil').setOrigin(0).setScale(SCALE);
      const crop = this.add.image(x, y, 'sprout').setOrigin(0).setScale(SCALE).setVisible(false);
      const lock = this.add.image(x, y, 'lock').setOrigin(0).setScale(SCALE).setVisible(false);
      const bar = this.add.graphics();
      const hl = this.add.graphics();
      hl.lineStyle(2, 0xfff6d0, 1).strokeRect(x - 2, y - 2, PLOT + 4, PLOT + 4).setVisible(false);
      const zone = this.add.zone(x, y, PLOT, PLOT).setOrigin(0).setInteractive({ useHandCursor: true });
      zone.on('pointerdown', () => this.bridge.onPlotClick(i));
      zone.on('pointerover', () => (this.hovered = i));
      zone.on('pointerout', () => this.hovered === i && (this.hovered = -1));
      this.views.push({ x, y, soil, crop, lock, bar, hl });
    }

    this.tip = this.add
      .text(0, 0, '', {
        fontFamily: FONT, fontSize: '10px', color: '#fff6d0', backgroundColor: '#2b1d14', padding: { x: 4, y: 2 },
      })
      .setOrigin(0.5, 1).setResolution(4).setDepth(20).setVisible(false);
  }

  private drawFence(g: Phaser.GameObjects.Graphics, x: number, y: number, w: number, h: number) {
    const rail = (x1: number, y1: number, len: number, horiz: boolean) => {
      g.fillStyle(0x6b4423);
      if (horiz) g.fillRect(x1, y1 + 3, len, 3).fillRect(x1, y1 + 9, len, 3);
      else g.fillRect(x1 + 2, y1, 3, len);
    };
    const gateL = W / 2 - 20;
    const gateR = W / 2 + 20;
    rail(x, y, gateL - x, true);
    rail(gateR, y, x + w - gateR, true);
    rail(x, y + h, w, true);
    rail(x, y, h, false);
    rail(x + w - 6, y, h, false);
    g.fillStyle(0x8f5d32);
    for (let px = x; px <= x + w - 6; px += 18) {
      if (px > gateL - 6 && px < gateR) continue;
      g.fillRect(px, y - 2, 6, 16);
      g.fillRect(px, y + h - 2, 6, 16);
    }
    for (let py = y; py <= y + h; py += 18) {
      g.fillRect(x, py, 6, 14);
      g.fillRect(x + w - 6, py, 6, 14);
    }
  }

  update(time: number) {
    const s = this.bridge.getState();
    if (!s) return;
    const now = this.bridge.now();
    const unlocked = plotsForLevel(s.level);

    this.views.forEach((v, i) => {
      const plot = s.plots[i];
      const locked = i >= unlocked;
      v.lock.setVisible(locked);
      v.soil.setAlpha(locked ? 0.45 : 1);
      v.bar.clear();
      v.hl.setVisible(this.hovered === i && !locked);
      const pending = this.bridge.isPending(i);

      if (!locked && plot.cropId) {
        const prog = cropProgress(plot, now);
        const tex = prog >= 1 ? `crop_${plot.cropId}` : prog >= 0.5 ? 'growing' : 'sprout';
        v.crop.setTexture(tex).setVisible(true).setAlpha(pending ? 0.5 : 1);
        if (prog < 1) {
          v.crop.y = v.y;
          v.bar.fillStyle(0x2b1d14).fillRect(v.x, v.y + PLOT + 3, PLOT, 5);
          v.bar.fillStyle(0x9be15d).fillRect(v.x + 1, v.y + PLOT + 4, Math.round((PLOT - 2) * prog), 3);
        } else {
          v.crop.y = v.y + (Math.sin(time / 220 + i) > 0 ? -1 : 0) * 2;
          if (Math.floor(time / 400 + i) % 3 === 0) {
            v.bar.fillStyle(0xfff6d0).fillRect(v.x + 6 + ((i * 13) % 30), v.y + 4 + ((i * 7) % 14), 3, 3);
          }
        }
      } else {
        v.crop.setVisible(false);
      }
    });

    if (this.hovered >= 0) {
      const v = this.views[this.hovered];
      const plot = s.plots[this.hovered];
      let label: string;
      if (this.hovered >= unlocked) label = `Lv${unlockLevelForPlot(this.hovered)} 解锁`;
      else if (!plot.cropId) label = '空地 · 点击播种';
      else if (cropProgress(plot, now) >= 1) label = `${CROPS[plot.cropId].name} 可收获!`;
      else label = `${CROPS[plot.cropId].name} ${formatDuration(remainingMs(plot, now))}`;
      this.tip.setText(label).setPosition(v.x + PLOT / 2, v.y - 4).setVisible(true);
    } else {
      this.tip.setVisible(false);
    }
  }

  floatText(i: number, msg: string, color = '#fff6d0') {
    const v = this.views[i];
    if (!v) return;
    const t = this.add
      .text(v.x + PLOT / 2, v.y + 8, msg, {
        fontFamily: FONT, fontSize: '11px', color, stroke: '#2b1d14', strokeThickness: 3,
      })
      .setOrigin(0.5).setResolution(4).setDepth(30);
    this.tweens.add({ targets: t, y: v.y - 22, alpha: 0, duration: 1100, ease: 'Cubic.easeOut', onComplete: () => t.destroy() });
  }
}
