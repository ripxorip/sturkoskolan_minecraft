"""Reusable building primitives on top of Model."""
import math
import random

# ---------------------------------------------------------------- materials
YELLOW = "yellow_concrete"          # the old school's rendered facade
PLINTH = "polished_andesite"
ROOF = "acacia"                     # orange-red tile roof (acacia_planks/_stairs/_slab)
ROOF_TRIM = "mangrove"              # red painted barge boards
CREAM = "smooth_sandstone"          # cream render / panels of the modern parts
GRAY = "cyan_terracotta"            # blue-gray corrugated metal cladding
PALE = "birch_planks"                # pale yellow corrugated cladding (gym, east wing)
ORANGE = "orange_concrete"        # window frames of the modern parts
GREEN = "lime_terracotta"           # window frames of the preschool
METAL = "smooth_stone"              # light gray metal roofs
METAL_SLAB = "smooth_stone_slab"
FLAT = "gray_concrete"              # flat roofing felt
INTERIOR = "white_concrete"
GLASS = "glass_pane"


def P(base, kind):
    """Material name helper: P('acacia','stairs') -> acacia_stairs; planks for wood."""
    wood = {"oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry",
            "crimson", "warped", "pale_oak", "bamboo"}
    if kind == "full":
        return base + "_planks" if base in wood else base
    if base == "smooth_stone" and kind == "stairs":
        return "stone_stairs"
    special = {("bricks", "stairs"): "brick_stairs", ("bricks", "slab"): "brick_slab",
               ("stone_bricks", "stairs"): "stone_brick_stairs", ("stone_bricks", "slab"): "stone_brick_slab",
               ("end_stone_bricks", "slab"): "end_stone_brick_slab",
               ("end_stone_bricks", "stairs"): "end_stone_brick_stairs",
               ("deepslate_tiles", "stairs"): "deepslate_tile_stairs",
               ("deepslate_tiles", "slab"): "deepslate_tile_slab"}
    if (base, kind) in special:
        return special[(base, kind)]
    return f"{base}_{kind}"


# ---------------------------------------------------------------- wall planes
def wset(m, axis, plane, u, y, state):
    """Set a block on a wall plane. axis='x': wall at x=plane, u runs along z.
    axis='z': wall at z=plane, u runs along x."""
    if axis == "x":
        m.set(plane, y, u, state)
    else:
        m.set(u, y, plane, state)


def wfill(m, axis, plane, u1, u2, y1, y2, state):
    if axis == "x":
        m.fill(plane, y1, u1, plane, y2, u2, state)
    else:
        m.fill(u1, y1, plane, u2, y2, plane, state)


def window(m, axis, plane, u1, u2, y1, y2, glass=GLASS, frame=None, mullions=(), transoms=()):
    """Window with outer rectangle u1..u2, y1..y2. With a frame, the outer ring
    is frame material and glass fills the inside."""
    u1, u2 = sorted((u1, u2))
    if frame:
        wfill(m, axis, plane, u1, u2, y1, y2, frame)
        wfill(m, axis, plane, u1 + 1, u2 - 1, y1 + 1, y2 - 1, glass)
        for u in mullions:
            wfill(m, axis, plane, u, u, y1 + 1, y2 - 1, frame)
        for y in transoms:
            wfill(m, axis, plane, u1 + 1, u2 - 1, y, y, frame)
    else:
        wfill(m, axis, plane, u1, u2, y1, y2, glass)


def porthole(m, axis, plane, uc, yc, ring="stripped_oak_wood", center="orange_stained_glass", big=False):
    """Round window. 3x3 (plus-shaped ring) or 4x4 octagon when big=True
    (uc,yc = lower-left of the 2x2 centre)."""
    if not big:
        for du, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            wset(m, axis, plane, uc + du, yc + dy, ring)
        wset(m, axis, plane, uc, yc, center)
    else:
        for du in range(-1, 3):
            for dy in range(-1, 3):
                corner = du in (-1, 2) and dy in (-1, 2)
                if corner:
                    continue
                inner = du in (0, 1) and dy in (0, 1)
                wset(m, axis, plane, uc + du, yc + dy, center if inner else ring)


def door(m, x, y, z, facing, kind="oak_door", hinge="left"):
    m.set(x, y, z, f"{kind}[facing={facing},half=lower,hinge={hinge},open=false]")
    m.set(x, y + 1, z, f"{kind}[facing={facing},half=upper,hinge={hinge},open=false]")


def double_door(m, axis, plane, u, y, facing, kind="oak_door"):
    """Two doors side by side at u and u+1 (hinges outward)."""
    if axis == "x":
        door(m, plane, y, u, facing, kind, "left" if facing == "east" else "right")
        door(m, plane, y, u + 1, facing, kind, "right" if facing == "east" else "left")
    else:
        door(m, u, y, plane, facing, kind, "right" if facing == "north" else "left")
        door(m, u + 1, y, plane, facing, kind, "left" if facing == "north" else "right")


def opening(m, axis, plane, u1, u2, y1, y2):
    wfill(m, axis, plane, u1, u2, y1, y2, "air")


# ---------------------------------------------------------------- roofs
def quant(h):
    return math.floor(h * 2 + 0.5) / 2.0


def place_column(m, x, z, top, bottom, full, slab):
    """Roof column whose top surface is at `top` (multiple of .5), filled down to
    `bottom` (block y). Uses a bottom slab for half tops."""
    if top % 1:
        m.set(x, int(math.floor(top)), z, f"{slab}[type=bottom]")
        hi = int(math.floor(top)) - 1
    else:
        hi = int(top) - 1
    if hi >= bottom:
        m.fill(x, bottom, z, x, hi, z, full)


def mono_roof(m, x1, x2, z1, z2, y_low, y_high, low_side="north", full=METAL, slab=METAL_SLAB,
              wall=None, wall_top=4, overhang=1, high_wall=True):
    """Mono-pitch roof over x1..x2, z1..z2. y_low / y_high are the roof *top
    surface* heights at the low and high side (quantised to half blocks). Side
    walls (x1, x2) and the high end wall are raised to meet the roof."""
    zs = list(range(z1, z2 + 1))
    if low_side == "south":
        zs = zs[::-1]
    n = max(len(zs) - 1, 1)
    tops = [quant(y_low + (y_high - y_low) * i / n) for i in range(len(zs))]
    for i, z in enumerate(zs):
        t = tops[i]
        tb = int(math.ceil(t)) - 1
        bottom = tb if i == 0 else min(tb, int(math.floor(tops[i - 1])))
        for x in range(x1, x2 + 1):
            place_column(m, x, z, t, bottom, full, slab)
        for x in range(x1 - overhang, x1):
            place_column(m, x, z, t, tb, full, slab)
        for x in range(x2 + 1, x2 + overhang + 1):
            place_column(m, x, z, t, tb, full, slab)
        if wall:
            for x in (x1, x2):
                if bottom - 1 > wall_top:
                    m.fill(x, wall_top + 1, z, x, bottom - 1, z, wall)
            if high_wall and i == len(zs) - 1 and bottom - 1 > wall_top:
                m.fill(x1, wall_top + 1, z, x2, bottom - 1, z, wall)
    if overhang:
        zl = zs[0] - 1 if low_side == "north" else zs[0] + 1
        t = tops[0] - 0.5
        for x in range(x1 - overhang, x2 + overhang + 1):
            place_column(m, x, zl, t, int(math.ceil(t)) - 1, full, slab)
    return tops


def flat_roof(m, x1, x2, z1, z2, y, mat=FLAT, fascia=None, overhang=0, parapet=None):
    m.fill(x1, y, z1, x2, y, z2, mat)
    if fascia:
        for x in range(x1 - overhang, x2 + overhang + 1):
            for z in (z1 - overhang, z2 + overhang):
                m.set(x, y, z, fascia)
        for z in range(z1 - overhang, z2 + overhang + 1):
            for x in (x1 - overhang, x2 + overhang):
                m.set(x, y, z, fascia)
    if parapet:
        m.walls(x1, z1, x2, z2, y + 1, y + 1, parapet)


# ---------------------------------------------------------------- interiors
def lanterns(m, x1, x2, z1, z2, y, step=5, hanging=True):
    """Lanterns hanging under a ceiling (block at y+1) on a grid."""
    xs = range(x1 + (x2 - x1) % step // 2 + 1, x2, step) if x2 - x1 > 2 else [(x1 + x2) // 2]
    zs = range(z1 + (z2 - z1) % step // 2 + 1, z2, step) if z2 - z1 > 2 else [(z1 + z2) // 2]
    for x in xs:
        for z in zs:
            m.set(x, y, z, f"lantern[hanging={'true' if hanging else 'false'}]")


def ceiling_lights(m, x1, x2, z1, z2, y, step=4, block="sea_lantern"):
    for x in range(x1 + 1, x2, step):
        for z in range(z1 + 1, z2, step):
            m.set(x, y, z, block)


def desks(m, x1, x2, z1, z2, y, facing="north", wood="spruce", chair="oak"):
    """Rows of school desks (top slab) with stair chairs. `facing` = direction the
    pupils look (towards the board)."""
    back = {"north": "south", "south": "north", "east": "west", "west": "east"}[facing]
    if facing in ("north", "south"):
        rows = range(z1, z2 + 1, 3) if facing == "north" else range(z2, z1 - 1, -3)
        dz = 1 if facing == "north" else -1
        for zr in rows:
            if (zr + dz) > max(z1, z2) or (zr + dz) < min(z1, z2):
                continue
            for x in range(x1, x2 + 1):
                if (x - x1) % 3 == 2:
                    continue
                m.set(x, y, zr, f"{wood}_slab[type=top]")
                m.set(x, y, zr + dz, f"{chair}_stairs[facing={back}]")
    else:
        rows = range(x1, x2 + 1, 3) if facing == "west" else range(x2, x1 - 1, -3)
        dx = 1 if facing == "west" else -1
        for xr in rows:
            if (xr + dx) > max(x1, x2) or (xr + dx) < min(x1, x2):
                continue
            for z in range(z1, z2 + 1):
                if (z - z1) % 3 == 2:
                    continue
                m.set(xr, y, z, f"{wood}_slab[type=top]")
                m.set(xr + dx, y, z, f"{chair}_stairs[facing={back}]")


def table_with_chairs(m, x, y, z, length=3, axis="x", top="birch_slab[type=top]", chair="birch_stairs"):
    """Long table along axis with chairs on both sides."""
    for i in range(length):
        if axis == "x":
            m.set(x + i, y, z, top)
            m.set(x + i, y, z - 1, f"{chair}[facing=north]")
            m.set(x + i, y, z + 1, f"{chair}[facing=south]")
        else:
            m.set(x, y, z + i, top)
            m.set(x - 1, y, z + i, f"{chair}[facing=west]")
            m.set(x + 1, y, z + i, f"{chair}[facing=east]")


# ---------------------------------------------------------------- nature
def tree(m, x, z, kind="oak", height=6, radius=3, seed=0, y0=0, trunk2=False):
    rnd = random.Random(seed * 7919 + x * 31 + z)
    log = f"{kind}_log[axis=y]"
    leaves = f"{kind}_leaves[persistent=true]"
    tw = 2 if trunk2 else 1
    for y in range(y0, y0 + height):
        for dx in range(tw):
            for dz in range(tw):
                m.set(x + dx, y, z + dz, log)
    if kind == "spruce":
        top = y0 + height + 1
        for y in range(y0 + 2, top + 1):
            r = max(0, int((top - y) * radius / (top - y0 - 2) + 0.5))
            if (top - y) % 2 == 1:
                r = max(r - 1, 0)
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if dx * dx + dz * dz <= r * r + 1 and m.get(x + dx, y, z + dz) in ("<keep>", "air"):
                        m.set(x + dx, y, z + dz, leaves)
        m.set(x, top + 1, z, leaves)
        return
    cy = y0 + height
    cx, cz = x + (tw - 1) / 2, z + (tw - 1) / 2
    blobs = [(cx, cy, cz, radius)]
    for _ in range(3 + radius // 2):
        a = rnd.uniform(0, 2 * math.pi)
        d = rnd.uniform(0.4, 0.8) * radius
        blobs.append((cx + math.cos(a) * d, cy + rnd.uniform(-1.5, 1.0), cz + math.sin(a) * d,
                      radius * rnd.uniform(0.55, 0.8)))
    R = int(radius * 1.8) + 2
    for dx in range(-R, R + 1):
        for dz in range(-R, R + 1):
            for dy in range(-R, R + 1):
                px, py, pz = int(cx + dx), cy + dy, int(cz + dz)
                if py < y0 + 2:
                    continue
                inside = False
                for bx, by, bz, br in blobs:
                    if ((px - bx) ** 2 + ((py - by) * 1.35) ** 2 + (pz - bz) ** 2) <= br * br:
                        inside = True
                        break
                if inside and rnd.random() > 0.06 and m.get(px, py, pz) in ("<keep>", "air"):
                    m.set(px, py, pz, leaves)
    # a few branches
    for _ in range(radius // 2):
        a = rnd.uniform(0, 2 * math.pi)
        for t in range(1, max(2, radius - 1)):
            bx, bz = int(round(cx + math.cos(a) * t)), int(round(cz + math.sin(a) * t))
            by = cy - 1 + t // 2
            axis = "x" if abs(math.cos(a)) > abs(math.sin(a)) else "z"
            m.set(bx, by, bz, f"{kind}_log[axis={axis}]")


def bush(m, x, z, r=1, kind="oak", seed=0):
    rnd = random.Random(seed + x * 17 + z * 13)
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            for dy in range(0, r + 1):
                if dx * dx + dz * dz + dy * dy * 2 <= r * r + 1 and rnd.random() > 0.15:
                    if m.get(x + dx, dy, z + dz) in ("<keep>", "air"):
                        m.set(x + dx, dy, z + dz, f"{kind}_leaves[persistent=true]")
