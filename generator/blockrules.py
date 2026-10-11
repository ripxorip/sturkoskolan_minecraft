"""Post-processing that mimics Minecraft's neighbour-dependent block shapes.

Blocks placed by /fill and /setblock only get their shapes updated when a
*neighbour* changes, so the last-placed pane/fence/stair in a row would look
wrong. We compute the final states here, from the complete model.
"""
import numpy as np
from model import parse_state, make_state

NONFULL_SUFFIX = ("_stairs", "_slab", "_pane", "_fence", "_fence_gate", "_wall", "_door",
                  "_trapdoor", "_carpet", "_sign", "_button", "_pressure_plate", "_bed",
                  "_torch", "_banner", "_rod", "_candle", "_sapling", "_tulip", "_head",
                  "_skull", "_coral", "_fan", "_rail", "_hanging_sign", "_lantern",
                  "_leaves", "_chain")
NONFULL_NAMES = {"air", "lantern", "soul_lantern", "torch", "chain", "iron_chain", "iron_bars", "ladder",
                 "flower_pot", "daylight_detector", "short_grass", "tall_grass", "fern",
                 "poppy", "dandelion", "cornflower", "oxeye_daisy", "azure_bluet", "allium",
                 "lily_of_the_valley", "blue_orchid", "rose_bush", "lilac", "peony",
                 "sweet_berry_bush", "bell", "cauldron", "hopper", "anvil", "campfire",
                 "lightning_rod", "end_rod", "scaffolding", "snow", "water", "lava", "cake",
                 "bamboo", "vine", "large_fern", "dead_bush", "glass", "tinted_glass",
                 "brewing_stand", "grindstone", "lectern", "enchanting_table", "stonecutter",
                 "heavy_weighted_pressure_plate", "light_weighted_pressure_plate", "bush",
                 "pink_petals", "leaf_litter", "firefly_bush", "short_dry_grass", "tall_dry_grass"}

PANE_LIKE = lambda n: n.endswith("_pane") or n == "iron_bars"
FENCE = lambda n: n.endswith("_fence")
GATE = lambda n: n.endswith("_fence_gate")
STAIRS = lambda n: n.endswith("_stairs")


def is_wall(n):
    return n.endswith("_wall") and not any(n.endswith(s) for s in (
        "_wall_sign", "_wall_torch", "_wall_banner", "_wall_hanging_sign", "_wall_head",
        "_wall_skull", "_wall_fan"))


def is_full(n, y):
    if n == "<keep>":
        return y < 0  # untouched terrain: solid below ground, air above
    if n in NONFULL_NAMES or n.endswith("stained_glass"):
        return False
    if n.endswith("_wall") and is_wall(n):
        return False
    return not any(n.endswith(s) for s in NONFULL_SUFFIX)


DIRS = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
CW = {"north": "east", "east": "south", "south": "west", "west": "north"}
CCW = {v: k for k, v in CW.items()}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
AXIS = {"north": "z", "south": "z", "east": "x", "west": "x"}


def gate_connects(props, d):
    # A fence gate connects to fences/walls on the sides perpendicular to its facing.
    return AXIS[props.get("facing", "north")] != AXIS[d]


def postprocess(m):
    pal_names = [parse_state(s)[0] for s in m.pal]
    pal_props = [parse_state(s)[1] for s in m.pal]

    def info(x, y, z):
        if not m.inside(x, y, z):
            return ("<keep>", {})
        i = m.a[x - m.x0, y - m.y0, z - m.z0]
        return pal_names[i], pal_props[i]

    targets = [i for i, n in enumerate(pal_names)
               if PANE_LIKE(n) or FENCE(n) or is_wall(n) or STAIRS(n)]
    mask = np.isin(m.a, targets)
    xs, ys, zs = np.nonzero(mask)
    updates = []
    for xi, yi, zi in zip(xs, ys, zs):
        x, y, z = xi + m.x0, yi + m.y0, zi + m.z0
        n, p = info(x, y, z)
        p = dict(p)
        if PANE_LIKE(n):
            for d, (dx, dz) in DIRS.items():
                nn, npp = info(x + dx, y, z + dz)
                c = PANE_LIKE(nn) or is_wall(nn) or (is_full(nn, y) and not nn.endswith("_leaves"))
                p[d] = "true" if c else "false"
        elif FENCE(n):
            nether = n == "nether_brick_fence"
            for d, (dx, dz) in DIRS.items():
                nn, npp = info(x + dx, y, z + dz)
                c = (FENCE(nn) and ((nn == "nether_brick_fence") == nether)) \
                    or (GATE(nn) and gate_connects(npp, d)) \
                    or (is_full(nn, y) and not nn.endswith("_leaves"))
                p[d] = "true" if c else "false"
        elif is_wall(n):
            conn = {}
            for d, (dx, dz) in DIRS.items():
                nn, npp = info(x + dx, y, z + dz)
                c = is_wall(nn) or PANE_LIKE(nn) or (GATE(nn) and gate_connects(npp, d)) \
                    or (is_full(nn, y) and not nn.endswith("_leaves"))
                conn[d] = c
                p[d] = "low" if c else "none"
            straight = (conn["north"] and conn["south"] and not conn["east"] and not conn["west"]) or \
                       (conn["east"] and conn["west"] and not conn["north"] and not conn["south"])
            above, _ = info(x, y + 1, z)
            p["up"] = "false" if straight and above in ("<keep>", "air") else "true"
        elif STAIRS(n):
            f = p.get("facing", "north"); half = p.get("half", "bottom")
            shape = "straight"
            dx, dz = DIRS[f]
            bn, bp = info(x + dx, y, z + dz)  # block behind (in facing direction)

            def can_take(face):
                ddx, ddz = DIRS[face]
                nn, npp = info(x + ddx, y, z + ddz)
                return not STAIRS(nn) or npp.get("facing", "north") != f or npp.get("half", "bottom") != half

            done = False
            if STAIRS(bn) and bp.get("half", "bottom") == half:
                f2 = bp.get("facing", "north")
                if AXIS[f2] != AXIS[f] and can_take(OPP[f2]):
                    shape = "outer_left" if f2 == CCW[f] else "outer_right"
                    done = True
            if not done:
                fn, fp = info(x - dx, y, z - dz)  # block in front
                if STAIRS(fn) and fp.get("half", "bottom") == half:
                    f3 = fp.get("facing", "north")
                    if AXIS[f3] != AXIS[f] and can_take(f3):
                        shape = "inner_left" if f3 == CCW[f] else "inner_right"
            p["shape"] = shape
            p.setdefault("half", "bottom")
        updates.append((x, y, z, make_state(n, p)))
    for x, y, z, s in updates:
        m.set(x, y, z, s)
    return len(updates)
