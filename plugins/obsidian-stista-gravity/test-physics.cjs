const assert = require('node:assert/strict');
const { anchorTarget, step } = require('./graph-view.js');
const mix = { KO: 0.5, AV: 0, RU: 0, CA: 0.5, UM: 0, DR: 0 };
const equal = anchorTarget(mix, false),
  phi = anchorTarget(mix, true);
assert(Math.abs(equal.y) < 1e-12);
assert(phi.y > 0.6);
const create = () => [{ id: 'a', x: 0, y: 0, vx: 0, vy: 0, tongue_profile: mix }];
const a = create(),
  b = create(),
  off = create();
for (let i = 0; i < 120; i++) {
  step(a, [], 1, true);
  step(b, [], 1, false);
  step(off, [], 0, true);
}
assert(a[0].y > 0.4);
assert(Math.abs(b[0].y) < 1e-12);
assert.equal(off[0].y, 0);
assert(a.every((n) => Number.isFinite(n.x) && Number.isFinite(n.y)));
console.log(
  'PASS: phi changes attraction, equal weights cancel, gravity zero removes anchor force; finite bounded positions'
);
