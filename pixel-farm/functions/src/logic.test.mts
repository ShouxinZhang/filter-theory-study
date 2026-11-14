// Run: node src/logic.test.mts   (Node >= 23 strips types natively)
import assert from 'node:assert/strict';
import * as L from './logic.ts';

const T0 = 1_700_000_000_000;
let s = L.newPlayer('测试', T0);
assert.equal(s.coins, L.START_COINS);
assert.equal(s.seeds.carrot, 4);

// plant, can't harvest early, can after growMs
s = L.plant(s, 0, 'carrot', T0).state;
assert.equal(s.seeds.carrot, 3);
assert.throws(() => L.harvest(s, [0], T0 + 1000), /还没成熟/);
assert.throws(() => L.plant(s, 0, 'carrot', T0), /已经种了/);
assert.throws(() => L.plant(s, 6, 'carrot', T0), /Lv2/); // level 1 has 6 plots
const h = L.harvest(s, [0], T0 + L.CROPS.carrot.growMs);
s = h.state;
assert.equal(s.inventory.carrot, 2);
assert.equal(s.xp, 2);
assert.equal(s.plots[0].cropId, null);

// economy
assert.throws(() => L.buySeed(s, 'tomato', 1, T0), /Lv2/);
assert.throws(() => L.buySeed(s, 'carrot', 1000, T0), /数量/);
assert.throws(() => L.buySeed(s, 'carrot', 1.5, T0), /数量/);
assert.throws(() => L.buySeed(s, '__proto__', 1, T0), /未知作物/);
assert.throws(() => L.buySeed(s, 'wheat', 99, T0), /金币不足/);
s = L.buySeed(s, 'wheat', 2, T0).state;
assert.equal(s.coins, L.START_COINS - 20);
const sold = L.sell(s, 'all', 'all', T0);
assert.equal(sold.result.earned, 10);
s = sold.state;
assert.throws(() => L.sell(s, 'all', 'all', T0), /空/);

// harvest all + level up
for (let i = 0; i < 6; i++) s.plots[i] = { cropId: 'wheat', plantedAt: T0 };
const ha = L.harvest(s, 'all', T0 + L.CROPS.wheat.growMs);
assert.equal(ha.result.harvested.length, 6);
assert.equal(ha.state.level, 2); // 2 + 24 xp >= 20
assert.equal(ha.state.xp, 6);
assert.equal(L.plotsForLevel(2), 7);
assert.equal(L.unlockLevelForPlot(11), 7);

// immutability
const before = JSON.stringify(s);
L.buySeed(s, 'carrot', 1, T0);
assert.equal(JSON.stringify(s), before);

console.log('logic tests passed ✔');
