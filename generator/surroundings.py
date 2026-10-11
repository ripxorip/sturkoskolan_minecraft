"""Everything around the school: ground, roads (from OpenStreetMap), yards,
fences, playground, Sturkö Kvarn (the windmill), the café, a few houses, trees."""
import json
import math
import os
import random

import numpy as np

from lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
ASPHALT = "gray_concrete_powder"
YARD = "light_gray_concrete_powder"
SIDEWALK = "smooth_stone"

# OSM projection: local metres around the school, rotated 4.4 degrees so the
# building is axis aligned, scaled 1.2 blocks per metre.
LAT0, LON0, ROT, SCALE = 56.11215, 15.68115, math.radians(4.4), 1.2


def project(lat, lon):
    x = (lon - LON0) * 111320 * math.cos(math.radians(LAT0))
    y = (lat - LAT0) * 110574
    xr = x * math.cos(ROT) - y * math.sin(ROT)
    yr = x * math.sin(ROT) + y * math.cos(ROT)
    return SCALE * xr, -SCALE * yr


def load_osm():
    with open(os.path.join(HERE, "..", "data", "osm_area.json")) as f:
        d = json.load(f)
    ways = []
    for e in d["elements"]:
        if e["type"] == "way" and "geometry" in e:
            ways.append((e.get("tags", {}), [project(g["lat"], g["lon"]) for g in e["geometry"]]))
    return ways


# ------------------------------------------------------------------ rasterising
def grid(m):
    X, Z = np.meshgrid(np.arange(m.x0, m.x1), np.arange(m.z0, m.z1), indexing="ij")
    return X.astype(float), Z.astype(float)


def polyline_dist(X, Z, pts):
    """Distance to a polyline and arc-length parameter of the nearest point."""
    best = np.full(X.shape, np.inf)
    s_best = np.zeros(X.shape)
    s0 = 0.0
    for (ax, az), (bx, bz) in zip(pts[:-1], pts[1:]):
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        if L2 == 0:
            continue
        t = np.clip(((X - ax) * dx + (Z - az) * dz) / L2, 0, 1)
        px, pz = ax + t * dx, az + t * dz
        d = np.hypot(X - px, Z - pz)
        mask = d < best
        best[mask] = d[mask]
        s_best[mask] = s0 + t[mask] * math.sqrt(L2)
        s0 += math.sqrt(L2)
    return best, s_best


def polygon_mask(X, Z, poly):
    """Even-odd point-in-polygon on the grid."""
    inside = np.zeros(X.shape, bool)
    n = len(poly)
    for i in range(n):
        (x1, z1), (x2, z2) = poly[i], poly[(i + 1) % n]
        cond = ((z1 > Z) != (z2 > Z))
        xint = (x2 - x1) * (Z - z1) / ((z2 - z1) + 1e-12) + x1
        inside ^= cond & (X < xint)
    return inside


def apply_mask(m, mask, y, state):
    xs, zs = np.nonzero(mask)
    for xi, zi in zip(xs, zs):
        m.set(int(xi + m.x0), y, int(zi + m.z0), state)


def line4(x1, z1, x2, z2):
    """4-connected line (so iron bars / fences connect along diagonals)."""
    x1, z1, x2, z2 = int(round(x1)), int(round(z1)), int(round(x2)), int(round(z2))
    pts = [(x1, z1)]
    x, z = x1, z1
    dx, dz = abs(x2 - x1), abs(z2 - z1)
    sx, sz = (1 if x2 > x1 else -1), (1 if z2 > z1 else -1)
    err = dx - dz
    while (x, z) != (x2, z2):
        e2 = 2 * err
        if e2 > -dz and (abs(e2 + dz) <= abs(e2 - dx) or e2 >= dx):
            err -= dz; x += sx
        else:
            err += dx; z += sz
        pts.append((x, z))
    return pts


def fence_line(m, pts, h=2, state="iron_bars", skip=()):
    for (ax, az), (bx, bz) in zip(pts[:-1], pts[1:]):
        for x, z in line4(ax, az, bx, bz):
            if (x, z) in skip:
                continue
            if m.get(x, 0, z) in ("<keep>", "air"):
                m.fill(x, 0, z, x, h - 1, z, state)


# ------------------------------------------------------------------ ground & roads
SCHOOL_AREA = [(63.4, -68.3), (30.5, -74.1), (18.5, -100.9), (-0.9, -86.0), (-27.7, -70.5),
               (-33.2, -66.4), (-36.5, -61.4), (-39.0, -55.0), (-52.2, -50.1), (-50.3, -44.1),
               (-43.9, -23.7), (-30.9, 2.9), (-12.7, 38.2), (9.3, 78.7), (15.4, 74.9),
               (41.4, 68.8), (38.6, 60.4), (37.6, 54.4), (37.3, 48.3), (39.7, 35.0),
               (57.9, -53.8), (60.9, -60.9)]


def kyrk_x(z):
    """x of Kyrkvägen's centre line along the school (piecewise linear)."""
    pts = [(-56.9, -65.1), (-52.2, -50.1), (-50.3, -44.1), (-43.9, -23.7), (-30.9, 2.9),
           (-12.7, 38.2), (9.3, 78.7)]
    pts = sorted(pts, key=lambda p: p[1])
    for (x1, z1), (x2, z2) in zip(pts[:-1], pts[1:]):
        if z1 <= z <= z2:
            return x1 + (x2 - x1) * (z - z1) / (z2 - z1)
    return pts[0][0] if z < pts[0][1] else pts[-1][0]


def makes_x(z):
    pts = [(39.7, 35.0), (57.9, -53.8), (60.9, -60.9), (63.4, -68.3), (65.8, -78.7), (65.1, -94.9)]
    pts = sorted(pts, key=lambda p: p[1])
    for (x1, z1), (x2, z2) in zip(pts[:-1], pts[1:]):
        if z1 <= z <= z2:
            return x1 + (x2 - x1) * (z - z1) / (z2 - z1)
    return pts[0][0] if z < pts[0][1] else pts[-1][0]


def ground(m):
    X, Z = grid(m)
    rnd = np.random.default_rng(7)
    noise = rnd.random(X.shape)
    school = polygon_mask(X, Z, SCHOOL_AREA)
    # north playground: sandy ground with grass edges
    play = school & (Z < -57) & (Z > -90)
    sandy = play & (Z > -76) & (X > -30) & (X < 40)
    apply_mask(m, sandy & (noise < 0.55), -1, "coarse_dirt")
    apply_mask(m, sandy & (noise >= 0.55) & (noise < 0.8), -1, "packed_mud")
    # west asphalt: entrance plaza, parking and drive
    west = polygon_mask(X, Z, [(-60, -63), (-12, -63), (-12, -3), (-36, -3), (-44, -24), (-50, -44), (-55, -56)])
    apply_mask(m, west, -1, YARD)
    # east service yard along Makes väg
    east = polygon_mask(X, Z, [(42, -58), (59, -58), (50.5, -6), (42, -6)])
    apply_mask(m, east, -1, YARD)
    # gravel area south of the yellow building
    south = polygon_mask(X, Z, [(13, 31), (36, 31), (36, 40), (13, 40)])
    apply_mask(m, south & (noise < 0.85), -1, "gravel")
    apply_mask(m, south & (noise >= 0.85), -1, "coarse_dirt")
    # paths in the yard east of the yellow building
    for x, z in line4(28, 26, 35, 33) + line4(29, 27, 36, 34):
        m.set(x, -1, z, "gravel")
    for z in range(-5, 30):
        m.set(28, -1, z, "gravel")


def roads(m):
    X, Z = grid(m)
    ways = load_osm()
    layers = []  # (priority, mask, state)
    for tags, pts in ways:
        hw = tags.get("highway")
        if not hw:
            continue
        name = tags.get("name", "")
        width = {"tertiary": 3.6, "residential": 2.8, "service": 2.2, "unclassified": 2.8,
                 "path": 1.6}.get(hw)
        if width is None:
            continue
        d, s = polyline_dist(X, Z, pts)
        mask = d <= width
        state = ASPHALT
        if hw == "service" and name == "Makes väg":
            state = "gravel"
        if hw == "path":
            state = "gray_concrete_powder"
        layers.append((1 if hw == "path" else 2, mask, state))
        if hw == "tertiary":
            # sidewalk-ish verge kerb and a dashed centre line
            dash = (d < 0.5) & ((s // 3) % 2 == 0)
            layers.append((3, dash, "white_concrete"))
            layers.append((0, (d > width) & (d <= width + 0.8), "stone"))
    for prio in (0, 1, 2, 3):
        for p, mask, state in layers:
            if p == prio:
                apply_mask(m, mask, -1, state)


# ------------------------------------------------------------------ playground etc.
def picnic_table(m, x, z, axis="x"):
    for i in range(3):
        if axis == "x":
            m.set(x + i, 0, z, "spruce_slab[type=top]")
            m.set(x + i, 0, z - 1, "spruce_slab[type=bottom]")
            m.set(x + i, 0, z + 1, "spruce_slab[type=bottom]")
        else:
            m.set(x, 0, z + i, "spruce_slab[type=top]")
            m.set(x - 1, 0, z + i, "spruce_slab[type=bottom]")
            m.set(x + 1, 0, z + i, "spruce_slab[type=bottom]")


def play_tower(m, x, z):
    """Wooden play tower with a blue roof, a ladder and a red slide (going south)."""
    for dx in (0, 3):
        for dz in (0, 3):
            m.fill(x + dx, 0, z + dz, x + dx, 5, z + dz, "spruce_fence")
    m.fill(x, 2, z, x + 3, 2, z + 3, "spruce_slab[type=top]")
    for dx in (1, 2):
        m.set(x + dx, 3, z, "spruce_fence"); m.set(x, 3, z + dx, "spruce_fence"); m.set(x + 3, 3, z + dx, "spruce_fence")
    m.fill(x, 6, z, x + 3, 6, z + 3, "blue_concrete")
    m.fill(x + 1, 7, z, x + 2, 7, z + 3, "blue_concrete")
    m.fill(x + 1, 0, z, x + 1, 2, z, "spruce_planks")
    m.fill(x + 1, 0, z - 1, x + 1, 2, z - 1, "ladder[facing=north]")
    # slide down to the south
    for i in range(3):
        m.set(x + 1, 2 - i, z + 4 + i, "mangrove_stairs[facing=north]")
        m.set(x + 2, 2 - i, z + 4 + i, "mangrove_stairs[facing=north]")
    m.fill(x + 1, 0, z + 7, x + 2, 0, z + 7, "mangrove_slab[type=bottom]")


def swings(m, x, z):
    """Swing set along x (x .. x+6)."""
    for dx in (0, 6):
        m.fill(x + dx, 0, z - 1, x + dx, 3, z - 1, "spruce_fence")
        m.fill(x + dx, 0, z + 1, x + dx, 3, z + 1, "spruce_fence")
    m.fill(x, 4, z - 1, x + 6, 4, z + 1, "air")
    m.fill(x, 4, z, x + 6, 4, z, "stripped_spruce_log[axis=x]")
    for dx in (2, 4):
        m.fill(x + dx, 2, z, x + dx, 3, z, "iron_chain[axis=y]")
        m.set(x + dx, 1, z, "spruce_slab[type=top]")


def trampoline(m, x, z):
    """In-ground trampoline: real bouncy slime blocks!"""
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            if abs(dx) == 2 and abs(dz) == 2:
                continue
            ring = abs(dx) == 2 or abs(dz) == 2
            m.set(x + dx, -1, z + dz, "black_concrete" if ring else "slime_block")


def sandbox(m, x1, z1, x2, z2):
    m.fill(x1, -1, z1, x2, -1, z2, "sand")
    m.walls(x1, z1, x2, z2, 0, 0, "spruce_slab[type=bottom]")
    m.fill(x1, -2, z1, x2, -2, z2, "dirt")


def playhouse(m, x, z, color="mangrove_planks"):
    m.fill(x, -1, z, x + 3, -1, z + 3, "spruce_planks")
    m.walls(x, z, x + 3, z + 3, 0, 2, color)
    m.fill(x, 0, z, x, 2, z, "white_concrete"); m.fill(x + 3, 0, z, x + 3, 2, z, "white_concrete")
    m.fill(x, 0, z + 3, x, 2, z + 3, "white_concrete"); m.fill(x + 3, 0, z + 3, x + 3, 2, z + 3, "white_concrete")
    door(m, x + 1, 0, z + 3, "south", "spruce_door")
    m.set(x + 2, 1, z + 3, "glass_pane")
    m.set(x, 1, z + 1, "glass_pane"); m.set(x + 3, 1, z + 1, "glass_pane")
    for i, y in enumerate((3, 4)):
        m.fill(x - 1 + i, y, z - 1, x - 1 + i, y, z + 4, "dark_oak_stairs[facing=east]")
        m.fill(x + 4 - i, y, z - 1, x + 4 - i, y, z + 4, "dark_oak_stairs[facing=west]")
    m.fill(x + 1, 4, z, x + 2, 4, z + 3, color)
    m.fill(x + 1, 5, z - 1, x + 2, 5, z + 4, "dark_oak_slab[type=bottom]")
    m.fill(x + 1, 3, z, x + 2, 3, z, color); m.fill(x + 1, 3, z + 3, x + 2, 3, z + 3, color)


def lamp_post(m, x, z, h=7, dx=0, dz=0):
    m.set(x, 0, z, "andesite_wall")
    m.fill(x, 1, z, x, h, z, "iron_bars")
    m.set(x + dx, h + 1, z + dz, "polished_andesite_slab[type=bottom]")
    m.set(x, h + 1, z, "polished_andesite_slab[type=bottom]")
    m.set(x + dx, h, z + dz, "lantern[hanging=true]") if (dx or dz) else m.set(x, h + 2, z, "lantern")


def octagon(r):
    pts = set()
    R = int(math.ceil(r))
    for dx in range(-R, R + 1):
        for dz in range(-R, R + 1):
            if abs(dx) <= r and abs(dz) <= r and abs(dx) + abs(dz) <= r * 1.42:
                pts.add((dx, dz))
    return pts


def windmill(m, cx=40, cz=-88):
    """Sturkö Kvarn: tarred smock mill on a stone base, with a stage and sails
    facing the school (south)."""
    for y in range(-1, 2):
        for dx, dz in octagon(5.5):
            m.set(cx + dx, y, cz + dz, "stone_bricks" if (dx + dz + y) % 3 else "cobblestone")
    for dx, dz in octagon(4.5):
        m.set(cx + dx, 1, cz + dz, "spruce_planks")
    top = 15
    for y in range(2, top):
        r = 4.5 - (y - 2) * 1.6 / (top - 2)
        outer, inner = octagon(r), octagon(r - 1)
        for dx, dz in outer - inner:
            m.set(cx + dx, y, cz + dz, "dark_oak_planks")
        if y in (7, 11):
            for dx, dz in inner:
                m.set(cx + dx, y, cz + dz, "spruce_planks")
    for y in range(3, top - 1):  # ladder up through the floors
        m.set(cx, y, cz - 2, "ladder[facing=south]")
        if y in (7, 11):
            m.set(cx, y, cz - 2, "ladder[facing=south]")
    m.fill(cx, 7, cz - 1, cx, 7, cz - 1, "spruce_planks")
    m.fill(cx, 3, cz - 3, cx, top - 1, cz - 3, "dark_oak_planks")
    # cap
    for i, y in enumerate(range(top, top + 4)):
        for dx, dz in octagon(3.6 - i):
            m.set(cx + dx, y, cz + dz, "dark_oak_planks" if i < 3 else "dark_oak_slab[type=bottom]")
    # door and windows
    door(m, cx, 2, cz + 4, "south", "spruce_door")
    m.set(cx, 1, cz + 5, "stone_brick_stairs[facing=north]")
    for y, (dx, dz) in ((5, (-4, 0)), (5, (4, 0)), (9, (0, 3)), (12, (-3, 0))):
        m.set(cx + dx, y, cz + dz, "glass_pane")
    # stage (gallery) around the mill at y=6
    ring = octagon(6.5) - octagon(4.6)
    for dx, dz in ring:
        m.set(cx + dx, 6, cz + dz, "spruce_slab[type=top]")
    for dx, dz in octagon(6.5) - octagon(5.6):
        m.set(cx + dx, 7, cz + dz, "spruce_fence")
    for dx, dz in ((-6, 0), (6, 0), (0, -6), (0, 6), (-4, -4), (4, 4), (-4, 4), (4, -4)):
        m.fill(cx + dx, 0, cz + dz, cx + dx, 5, cz + dz, "spruce_fence")
    # windshaft + sails in the vertical plane south of the cap
    hz, hy = cz + 4, top + 1
    m.fill(cx, hy, cz + 2, cx, hy, hz, "spruce_log[axis=z]")
    L = 11
    for i in range(1, L + 1):
        m.set(cx, hy + i, hz, "stripped_spruce_log[axis=y]")
        m.set(cx, hy - i, hz, "stripped_spruce_log[axis=y]")
        m.set(cx + i, hy, hz, "stripped_spruce_log[axis=x]")
        m.set(cx - i, hy, hz, "stripped_spruce_log[axis=x]")
        if i >= 3:
            for o in (1, 2):
                m.set(cx + o, hy + i, hz, "spruce_fence")
                m.set(cx - o, hy - i, hz, "spruce_fence")
                m.set(cx + i, hy - o, hz, "spruce_fence")
                m.set(cx - i, hy + o, hz, "spruce_fence")
    m.set(cx, hy, hz + 1, "spruce_log[axis=z]")


def house(m, x1, z1, x2, z2, wall, trim="white_concrete", roof="deepslate_tiles", ridge="x",
          door_side="south", chimney=True, storeys=1):
    """Simple Swedish house with a 45 degree gable roof."""
    h = 3 if storeys == 1 else 6
    m.fill(x1, -1, z1, x2, -1, z2, "spruce_planks")
    m.walls(x1, z1, x2, z2, 0, h, wall)
    for (x, z) in ((x1, z1), (x1, z2), (x2, z1), (x2, z2)):
        m.fill(x, 0, z, x, h, z, trim)
    m.walls(x1, z1, x2, z2, -1, -1, "cobblestone")
    stairs, slab = P(roof, "stairs"), P(roof, "slab")
    if ridge == "x":
        width = z2 - z1 + 2
        for i in range((width + 1) // 2):
            y = h + 1 + i
            za, zb = z1 - 1 + i, z2 + 1 - i
            if za > zb:
                break
            if za == zb:
                m.fill(x1 - 1, y, za, x2 + 1, y, za, slab + "[type=bottom]")
                break
            m.fill(x1 - 1, y, za, x2 + 1, y, za, stairs + "[facing=south]")
            m.fill(x1 - 1, y, zb, x2 + 1, y, zb, stairs + "[facing=north]")
            for x in (x1, x2):
                if za + 1 <= zb - 1:
                    m.fill(x, y, za + 1, x, y, zb - 1, wall)
        if chimney:
            m.fill(x1 + 2, h, (z1 + z2) // 2, x1 + 2, h + width // 2 + 2, (z1 + z2) // 2, "bricks")
    else:
        width = x2 - x1 + 2
        for i in range((width + 1) // 2):
            y = h + 1 + i
            xa, xb = x1 - 1 + i, x2 + 1 - i
            if xa > xb:
                break
            if xa == xb:
                m.fill(xa, y, z1 - 1, xa, y, z2 + 1, slab + "[type=bottom]")
                break
            m.fill(xa, y, z1 - 1, xa, y, z2 + 1, stairs + "[facing=east]")
            m.fill(xb, y, z1 - 1, xb, y, z2 + 1, stairs + "[facing=west]")
            for z in (z1, z2):
                if xa + 1 <= xb - 1:
                    m.fill(xa + 1, y, z, xb - 1, y, z, wall)
        if chimney:
            m.fill((x1 + x2) // 2, h, z1 + 2, (x1 + x2) // 2, h + width // 2 + 2, z1 + 2, "bricks")
    # windows with white frames
    for x in range(x1 + 2, x2 - 1, 3):
        for z in (z1, z2):
            for yy in ((1,) if storeys == 1 else (1, 4)):
                m.fill(x, yy, z, x, yy + 1, z, "glass_pane")
    for z in range(z1 + 2, z2 - 1, 3):
        for x in (x1, x2):
            for yy in ((1,) if storeys == 1 else (1, 4)):
                m.fill(x, yy, z, x, yy + 1, z, "glass_pane")
    # door
    if door_side == "south":
        door(m, (x1 + x2) // 2, 0, z2, "south", "spruce_door")
    elif door_side == "north":
        door(m, (x1 + x2) // 2, 0, z1, "north", "spruce_door")
    elif door_side == "west":
        door(m, x1, 0, (z1 + z2) // 2, "west", "spruce_door")
    else:
        door(m, x2, 0, (z1 + z2) // 2, "east", "spruce_door")
    m.fill(x1 + 1, h, z1 + 1, x2 - 1, h, z2 - 1, "spruce_planks")
    lanterns(m, x1, x2, z1, z2, h - 1, step=4)


def cafe(m):
    """Sturkö Kvarn och Pizzeria, the red café next to the mill."""
    x1, z1, x2, z2 = 47, -81, 59, -73
    house(m, x1, z1, x2, z2, "red_terracotta", roof="deepslate_tiles", ridge="x", door_side="south")
    m.fill(x1 + 1, -1, z1 + 1, x2 - 1, -1, z2 - 1, "spruce_planks")
    m.fill(x1 + 1, 0, z1 + 1, x1 + 3, 1, z1 + 2, "bricks")      # pizza oven
    m.set(x1 + 2, 0, z1 + 3, "furnace[facing=south]")
    m.fill(x1 + 5, 0, z1 + 2, x2 - 2, 0, z1 + 2, "spruce_slab[type=top]")
    for xx in (x1 + 3, x1 + 7):
        table_with_chairs(m, xx, 0, z1 + 5, length=2, top="spruce_slab[type=top]", chair="spruce_stairs")
    m.sign((x1 + x2) // 2 + 2, 2, z2 + 1, "oak_wall_sign[facing=south]", ["Sturkö Kvarn", "och", "Pizzeria", ""],
           color="dark_red")
    # outdoor tables with parasols
    for xx, col in ((x1 + 1, "red"), (x1 + 6, "white"), (x1 + 11, "red")):
        zz = z2 + 4
        m.set(xx, 0, zz, "spruce_slab[type=top]")
        m.set(xx - 1, 0, zz, "spruce_stairs[facing=west]"); m.set(xx + 1, 0, zz, "spruce_stairs[facing=east]")
        m.fill(xx, 1, zz, xx, 2, zz, "spruce_fence")
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                m.set(xx + dx, 3, zz + dz, f"{col}_wool")
    m.fill(x1 - 1, -1, z2 + 1, x2 + 1, -1, z2 + 7, "gravel")


def bus_stop(m):
    x1, z1 = 10, -100
    m.fill(x1, -1, z1, x1 + 4, -1, z1 + 2, "smooth_stone")
    m.fill(x1, 0, z1 + 2, x1 + 4, 2, z1 + 2, "glass_pane")
    m.fill(x1, 0, z1, x1, 2, z1 + 1, "glass_pane")
    m.fill(x1 + 4, 0, z1, x1 + 4, 2, z1 + 1, "glass_pane")
    m.fill(x1, 3, z1, x1 + 4, 3, z1 + 2, "smooth_stone_slab[type=bottom]")
    m.fill(x1 + 1, 0, z1 + 1, x1 + 3, 0, z1 + 1, "spruce_slab[type=bottom]")
    m.fill(x1 + 6, 0, z1, x1 + 6, 2, z1, "iron_bars")
    m.set(x1 + 6, 3, z1, "yellow_concrete")
    m.sign(x1 + 6, 3, z1 - 1, "oak_wall_sign[facing=north]", ["Busshållplats", "Kvarnen", "", ""])


def caravan(m, x, z):
    m.fill(x, 0, z, x + 5, 2, z + 2, "white_concrete")
    m.fill(x, 3, z, x + 5, 3, z + 2, "smooth_quartz_slab[type=bottom]")
    m.fill(x + 1, 1, z, x + 2, 1, z, "glass_pane"); m.fill(x + 4, 1, z + 2, x + 4, 1, z + 2, "glass_pane")
    m.set(x + 1, 0, z + 2, "black_concrete"); m.set(x + 4, 0, z, "black_concrete")
    door(m, x + 3, 0, z, "north", "birch_door")
    m.set(x - 1, 0, z + 1, "iron_bars")


def container(m, x, z, length=6, color="cyan_terracotta"):
    m.fill(x, 0, z, x + length - 1, 2, z + 2, color)
    m.fill(x + length - 1, 0, z, x + length - 1, 2, z + 2, "iron_block")


def boulder(m, x, z, rx=3.5, ry=2.2, rz=2.2, seed=3):
    rnd = random.Random(seed)
    for dx in range(-5, 6):
        for dz in range(-4, 5):
            for dy in range(-1, 4):
                if (dx / rx) ** 2 + (dy / ry) ** 2 + (dz / rz) ** 2 <= 1.0 + rnd.uniform(-0.15, 0.1):
                    m.set(x + dx, dy, z + dz, rnd.choice(["diorite", "andesite", "stone", "diorite", "tuff"]))


def granite_wall(m, z1=-4, z2=42):
    rnd = random.Random(11)
    prev = None
    for z in range(z1, z2 + 1):
        xr = kyrk_x(z)
        xw = int(round(xr + 7.4))
        for x in range(int(round(xr + 4.4)), xw):
            if m.get(x, -1, z) == "<keep>" or "concrete_powder" in m.get(x, -1, z):
                m.set(x, -1, z, SIDEWALK)
        xs = [xw] if prev is None else list(range(min(prev, xw), max(prev, xw) + 1))
        for x in xs:
            m.set(x, 0, z, rnd.choice(["stone_bricks", "polished_andesite", "andesite", "stone_bricks"]))
            m.set(x, 1, z, "stone_brick_slab[type=bottom]")
        prev = xw


def details(m):
    rnd = random.Random(5)
    # ---------------- fences ("chain link")
    north = [(-36.5, -61.4), (-33.2, -66.4), (-27.7, -70.5), (-0.9, -86.0), (18.5, -100.9),
             (30.5, -74.1), (63.4, -68.3), (60.9, -60.9)]
    off = []
    for (x, z) in north:   # pull the fence a little inside the school area
        off.append((x + (0 if x > 50 else 0), z + 2.5 if z < -60 else z))
    fence_line(m, off)
    fence_line(m, [(60.9, -58.5), (42, -58.5)])
    fence_line(m, [(-36.5, -59), (-36.5, -62)])
    fence_line(m, [(-36.5, -59), (-17, -59), (-17, -57)])
    gate = {(-23, z) for z in range(-48, -45)}
    fence_line(m, [(-23, -58), (-23, -34)], skip=gate)
    fence_line(m, [(-23, -34), (-17, -34)])
    fence_line(m, [(-23, -22), (-17, -22)])
    fence_line(m, [(-23, -22), (-23, -4), (-17, -4)], skip={(-23, z) for z in range(-14, -11)})
    m.sign(-24, 0, -15, "oak_sign[rotation=4]", ["Mopedåkning", "förbjuden", "", ""], color="gold")
    # yard east of the yellow building, with the "Skolområde" gate
    fx = 37
    fence_line(m, [(fx, -5), (fx, 31), (31, 31)], skip={(fx, z) for z in range(8, 11)})
    m.sign(fx + 1, 0, 11, "oak_sign[rotation=12]", ["Skolområde", "", "", ""])
    # ball court south-west of the yellow building
    cx1, cz1, cx2, cz2 = -5, 22, 10, 38
    m.fill(cx1, -1, cz1, cx2, -1, cz2, ASPHALT)
    for x in range(cx1 + 1, cx2):
        m.set(x, -1, (cz1 + cz2) // 2, "white_concrete")
    fence_line(m, [(cx1, cz1), (cx2, cz1), (cx2, cz2), (cx1, cz2), (cx1, cz1)], h=3,
               skip={(cx1, z) for z in range(29, 32)})
    for gz, back in ((cz1 + 1, cz1 + 1), (cz2 - 1, cz2 - 1)):
        m.fill(1, 0, gz, 4, 1, gz, "iron_bars")
        m.fill(1, 2, gz, 4, 2, gz, "white_concrete")
    playhouse(m, 12, 33, "mangrove_planks")
    # ---------------- granite wall + sidewalk along Kyrkvägen
    granite_wall(m)
    # ---------------- playground (north yard)
    play_tower(m, 4, -72)
    swings(m, -12, -68)
    trampoline(m, -2, -64)
    sandbox(m, 14, -71, 20, -66)
    playhouse(m, 26, -66, "mangrove_planks")
    playhouse(m, -22, -66, "mangrove_planks")
    for x, z in ((-8, -60), (-2, -60), (22, -60)):
        picnic_table(m, x, z)
    for z in (-44, -38):
        picnic_table(m, -21, z, axis="z")
    picnic_table(m, -21, -20, axis="z"); picnic_table(m, -21, -12, axis="z")
    for i in range(8):                                  # bike rack
        m.set(-28, 0, -54 + i, "iron_bars")
    # in-yard colourful hop-scotch on the asphalt by the entrance (photo 7)
    for i, c in enumerate(["red", "yellow", "lime", "light_blue", "magenta", "orange"]):
        m.set(-20, -1, -41 + i, f"{c}_concrete")
    # ---------------- stuff south of the yellow building (photo 1)
    container(m, 15, 33, 6, "cyan_terracotta")
    caravan(m, 23, 33)
    m.fill(13, 0, 32, 13, 1, 39, "spruce_fence")
    boulder(m, 32, 18)
    # red shed in the SE yard
    house(m, 30, 23, 35, 28, "red_terracotta", roof="dark_oak", ridge="z", door_side="west", chimney=False)
    # ---------------- windmill + café + bus stop
    windmill(m)
    cafe(m)
    bus_stop(m)
    # ---------------- houses around
    house(m, -44, -99, -33, -92, "red_terracotta", ridge="x", door_side="south")
    house(m, -16, -118, -7, -109, "yellow_terracotta", ridge="x", door_side="south")
    house(m, 73, -102, 82, -93, "white_concrete", ridge="z", door_side="west")
    house(m, 44, 37, 52, 48, "white_concrete", roof="deepslate_tiles", ridge="z", door_side="west", storeys=2)
    house(m, -52, 24, -42, 32, "red_terracotta", ridge="x", door_side="north")
    # ---------------- lamp posts
    for z in range(-56, 40, 16):
        xl = int(round(kyrk_x(z) + 5.0))
        if m.get(xl, 0, z) in ("<keep>", "air"):
            lamp_post(m, xl, z, dx=-1)
    for z in range(-50, -5, 15):
        lamp_post(m, 45, z, dx=1)
    lamp_post(m, -27, -30, dx=1)
    # ---------------- trees
    trees = [(24, 46, "oak", 8, 7, True), (-4, -80, "oak", 7, 5, False), (17, -84, "oak", 7, 5, False),
             (-24, -76, "birch", 7, 3, False), (-32, -70, "oak", 6, 4, False),
             (26, -96, "oak", 7, 5, False), (52, -96, "oak", 6, 4, False), (30, -84, "birch", 7, 3, False),
             (64, -40, "oak", 7, 5, False), (66, -10, "oak", 6, 5, False), (58, 20, "oak", 7, 5, False),
             (48, 28, "birch", 7, 3, False), (34, 3, "oak", 6, 4, False), (34, 28, "birch", 6, 3, False),
             (-20, 12, "birch", 7, 3, False), (-17, 2, "birch", 6, 3, False), (-16, 28, "oak", 6, 4, False),
             (-46, 15, "oak", 7, 5, False), (-60, -30, "oak", 7, 5, False), (-62, -5, "spruce", 9, 4, False),
             (-50, -80, "oak", 6, 4, False), (-28, -112, "oak", 6, 4, False), (0, -122, "birch", 7, 3, False),
             (86, -80, "spruce", 10, 4, False), (78, -60, "oak", 7, 5, False), (70, 40, "oak", 7, 5, False),
             (20, 62, "oak", 6, 4, False), (-30, 50, "oak", 7, 5, False), (55, 60, "birch", 7, 3, False),
             (-70, -90, "spruce", 9, 4, False), (40, -110, "oak", 6, 4, False), (90, -120, "oak", 7, 5, False)]
    for i, (x, z, kind, h, r, big) in enumerate(trees):
        if m.get(x, 0, z) in ("<keep>", "air") and "concrete" not in m.get(x, -1, z):
            m.set(x, -1, z, "dirt")
            tree(m, x, z, kind, h, r, seed=i, trunk2=big)
    for x, z in ((-19, 6), (-18, 16), (-14, 20), (-13, -1), (-25, -26), (-25, -33), (38, -58)):
        bush(m, x, z, 1, seed=x * z)
    # flowers on the lawns
    for _ in range(260):
        x, z = rnd.randint(m.x0, m.x1 - 1), rnd.randint(m.z0, m.z1 - 1)
        if m.get(x, -1, z) == "<keep>" and m.get(x, 0, z) == "<keep>":
            m.set(x, 0, z, rnd.choice(["short_grass", "short_grass", "short_grass", "dandelion", "poppy",
                                       "cornflower", "oxeye_daisy"]))
