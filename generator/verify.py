"""Compare random cells of the model with the live server world over RCON."""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from build import make_model, GROUND_Y
from rcon import Rcon

m = make_model()
r = Rcon()
xs, ys, zs = m.nonkeep()
idx = list(range(len(xs)))
random.Random(1).shuffle(idx)
n = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
bad = []
checked = 0
for i in idx[:n]:
    x, y, z = int(xs[i]), int(ys[i]), int(zs[i])
    s = m.get(x, y, z)
    res = r.cmd(f"execute if block {x} {y + GROUND_Y} {z} minecraft:{s}")
    checked += 1
    if "passed" not in res:
        bad.append((x, y, z, s, res[:80]))
for (x, y, z) in m.block_entities:
    res = r.cmd(f"data get block {x} {y + GROUND_Y} {z} front_text.messages[1]")
    checked += 1
    if "following" not in res:
        bad.append((x, y, z, "sign", res[:80]))
print(f"checked {checked}, mismatches {len(bad)}")
for b in bad[:30]:
    print(b)
