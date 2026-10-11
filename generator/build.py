"""Build the Sturköskolan model, render previews and export it as a datapack of
/fill commands.

    python3 build.py --render            # previews into renders/
    python3 build.py --export DIR        # datapack functions into DIR
"""
import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import Model, parse_state, KEEP          # noqa: E402
from blockrules import postprocess, is_full         # noqa: E402
import surroundings as site_mod                      # noqa: E402
import modern                                        # noqa: E402
import yellow                                        # noqa: E402
from lib import door                                 # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GROUND_Y = 64          # absolute Y of the first air block above the superflat grass
BOUNDS = dict(x0=-120, x1=110, y0=-4, y1=34, z0=-150, z1=100)


def connect(m):
    """Openings that cut through the yellow building's walls (done after it)."""
    m.fill(15, 1, 0, 16, 2, 0, "air")
    m.fill(15, 0, -1, 16, 0, -1, "polished_andesite_stairs[facing=south]")


def welcome_signs(m):
    m.sign(-22, 0, -24, "oak_sign[rotation=4]", ["Välkommen till", "Sturköskolan", "& Sturkö förskola", ""],
           color="dark_blue")
    m.sign(-23, 0, 8, "oak_sign[rotation=4]", ["Sturköskolan", "Kyrkvägen 1", "", ""], color="dark_blue")


def make_model():
    t = time.time()
    m = Model(**BOUNDS)
    site_mod.ground(m)
    site_mod.roads(m)
    modern.build(m)
    yellow.build(m)
    connect(m)
    site_mod.details(m)
    welcome_signs(m)
    n = postprocess(m)
    print(f"model built in {time.time() - t:.1f}s, palette {len(m.pal)}, shaped {n} blocks", flush=True)
    return m


# --------------------------------------------------------------------- export
def boxes(m):
    """Greedy box decomposition of the model into (y1,y2,x1,x2,z1,z2,pid),
    bottom-up. Full blocks are also merged vertically."""
    a = m.a.copy()
    # block entities are placed separately with their NBT
    for (x, y, z) in m.block_entities:
        a[x - m.x0, y - m.y0, z - m.z0] = KEEP
    names = [parse_state(s)[0] for s in m.pal]
    # 'air' above ground is a no-op in a fresh superflat world
    air_ids = [i for i, n in enumerate(names) if n == "air"]
    for i in air_ids:
        sub = a[:, -m.y0:, :]
        sub[sub == i] = KEEP
    full = np.array([is_full(n, 0) for n in names])
    nx, ny, nz = a.shape
    rects_by_layer = []
    for yi in range(ny):
        L = a[:, yi, :]
        done = np.zeros(L.shape, bool)
        rects = []
        ids = np.unique(L)
        for pid in ids:
            if pid == KEEP:
                continue
            mask = (L == pid)
            xs, zs = np.nonzero(mask)
            for xi, zi in zip(xs, zs):
                if done[xi, zi]:
                    continue
                x2 = xi
                while x2 + 1 < nx and mask[x2 + 1, zi] and not done[x2 + 1, zi]:
                    x2 += 1
                z2 = zi
                while z2 + 1 < nz and mask[xi:x2 + 1, z2 + 1].all() and not done[xi:x2 + 1, z2 + 1].any():
                    z2 += 1
                    if (x2 - xi + 1) * (z2 - zi + 1) > 32000:
                        break
                done[xi:x2 + 1, zi:z2 + 1] = True
                rects.append((xi, x2, zi, z2, int(pid)))
        rects_by_layer.append(rects)
    # vertical merge for full blocks
    out = []
    open_boxes = {}
    for yi, rects in enumerate(rects_by_layer):
        new_open = {}
        for (x1, x2, z1, z2, pid) in rects:
            key = (x1, x2, z1, z2, pid)
            vol = (x2 - x1 + 1) * (z2 - z1 + 1)
            if full[pid] and key in open_boxes and vol * (yi - open_boxes[key] + 1) <= 32000:
                new_open[key] = open_boxes.pop(key)
            elif full[pid]:
                new_open[key] = yi
            else:
                out.append((yi, yi, x1, x2, z1, z2, pid))
        for key, y1 in open_boxes.items():
            x1, x2, z1, z2, pid = key
            out.append((y1, yi - 1, x1, x2, z1, z2, pid))
        open_boxes = new_open
    for key, y1 in open_boxes.items():
        x1, x2, z1, z2, pid = key
        out.append((y1, ny - 1, x1, x2, z1, z2, pid))
    out.sort(key=lambda b: (b[0], b[1]))
    return out


def commands(m):
    cmds = []
    for (y1, y2, x1, x2, z1, z2, pid) in boxes(m):
        s = "minecraft:" + m.pal[pid]
        X1, X2 = x1 + m.x0, x2 + m.x0
        Y1, Y2 = y1 + m.y0 + GROUND_Y, y2 + m.y0 + GROUND_Y
        Z1, Z2 = z1 + m.z0, z2 + m.z0
        if (X1, Y1, Z1) == (X2, Y2, Z2):
            cmds.append(f"setblock {X1} {Y1} {Z1} {s}")
        else:
            cmds.append(f"fill {X1} {Y1} {Z1} {X2} {Y2} {Z2} {s}")
    for (x, y, z), nbt in sorted(m.block_entities.items(), key=lambda kv: kv[0][1]):
        cmds.append(f"setblock {x} {y + GROUND_Y} {z} minecraft:{m.get(x, y, z)}{nbt}")
    return cmds


def export(m, out_dir, per_file=8000):
    cmds = commands(m)
    fdir = os.path.join(out_dir, "data", "sturko", "function")
    os.makedirs(fdir, exist_ok=True)
    for f in os.listdir(fdir):
        os.remove(os.path.join(fdir, f))
    n = 0
    for i in range(0, len(cmds), per_file):
        with open(os.path.join(fdir, f"part_{n:03d}.mcfunction"), "w", encoding="utf-8") as f:
            f.write("\n".join(cmds[i:i + per_file]) + "\n")
        n += 1
    with open(os.path.join(out_dir, "pack.mcmeta"), "w") as f:
        f.write('{"pack": {"description": "Sturköskolan builder", "pack_format": 94, '
                '"min_format": [94, 0], "max_format": [94, 1]}}\n')
    print(f"exported {len(cmds)} commands in {n} functions", flush=True)
    return n


# --------------------------------------------------------------------- render
def render_all(m, out):
    import render as R
    assets = R.Assets(os.environ.get("MC_ASSETS", "assets"))
    os.makedirs(out, exist_ok=True)
    jobs = [
        ("overview_sw", R.iso_view(4, 2, 5, "sw"), None),
        ("school_sw", R.iso_view(10, 5, 12, "sw"), (-40, -70, 60, 45)),
        ("school_se", R.iso_view(10, 5, 12, "se"), (-40, -70, 60, 45)),
        ("school_ne", R.iso_view(10, 5, 12, "ne"), (-40, -70, 60, 45)),
        ("school_nw", R.iso_view(10, 5, 12, "nw"), (-40, -70, 60, 45)),
        ("elev_west", R.elevation_view("west", 8), (-60, -70, 60, 45)),
        ("elev_east", R.elevation_view("east", 8), (-20, -70, 60, 45)),
        ("elev_south", R.elevation_view("south", 8), (-40, -70, 60, 60)),
        ("elev_north", R.elevation_view("north", 8), (-40, -100, 60, 45)),
    ]
    for name, view, region in jobs:
        t = time.time()
        img = R.render(m, assets, view, region=region)
        img.convert("RGB").save(os.path.join(out, name + ".png"))
        print(f"rendered {name} {img.size} in {time.time() - t:.1f}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--export", default=None)
    args = ap.parse_args()
    m = make_model()
    if args.render:
        render_all(m, os.path.join(ROOT, "renders"))
    if args.export:
        export(m, args.export)
