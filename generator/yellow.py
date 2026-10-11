"""The old yellow school building (gula skolan): two storeys + attic under a red
tiled gambrel roof ("brutet tak"), spiral fire escapes on the east side."""
from lib import *

X0, X1, Z0, Z1 = 13, 27, 0, 29          # outer walls
CX = 20                                 # ridge line
E = 10                                  # eave level (first roof block row)

# gambrel profile: d = distance in from the wall line -> list of (dy, kind)
PROFILE = {
    -1: [(0, "stair")],
    0: [(0, "full"), (1, "full"), (2, "stair")],
    1: [(2, "full"), (3, "full"), (4, "stair")],
    2: [(4, "full")],
    3: [(5, "slab")],
    4: [(5, "full")],
    5: [(6, "slab")],
    6: [(6, "full")],
    7: [(7, "slab")],
}


def shell_bottom(d):
    return E + PROFILE[d][0][0]


def roof(m):
    for x in range(X0 - 1, X1 + 2):
        dw, de = x - X0, X1 - x
        d = min(dw, de)
        facing = "east" if dw < de else "west"
        for z in range(Z0 - 1, Z1 + 2):
            gable_edge = z in (Z0 - 1, Z1 + 1)
            mat = ROOF_TRIM if gable_edge else ROOF
            for dy, kind in PROFILE[d]:
                y = E + dy
                if kind == "full":
                    s = P(mat, "full")
                elif kind == "slab":
                    s = P(mat, "slab") + "[type=bottom]"
                else:
                    s = P(mat, "stairs") + f"[facing={facing},half=bottom]"
                m.set(x, y, z, s)
    # gable walls under the roof
    for z in (Z0, Z1):
        for x in range(X0, X1 + 1):
            d = min(x - X0, X1 - x)
            top = shell_bottom(d) - 1
            if top >= E:
                m.fill(x, E, z, x, top, z, YELLOW)
    # chimneys (west slope, near the ridge)
    for zc in (11, 18):
        m.fill(17, 11, zc, 18, 19, zc + 1, "bricks")
        m.fill(17, 20, zc, 18, 20, zc + 1, "brick_slab[type=bottom]")
    # roof windows on the west slope
    for z in (9, 14):
        m.set(17, 15, z, "glass")
    # antenna on the south gable
    m.fill(CX, 18, Z1, CX, 21, Z1, "iron_bars")
    m.set(CX, 22, Z1, "waxed_lightning_rod")


def spiral(m, cx, cz, top_s, exit_idx_at_6, mirror=False):
    """Spiral fire escape around (cx,cz): 8 steps per turn, each 0.5 high.
    Steps are numbered i=1..; surface height s_i = 0.5*i."""
    ring = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
    if mirror:
        ring = [(dx, -dz) for dx, dz in ring]
    n = int(top_s * 2)
    for i in range(1, n + 1):
        s = 0.5 * i
        idx = (exit_idx_at_6 + (12 - i)) % 8
        dx, dz = ring[idx]
        x, z = cx + dx, cz + dz
        if s % 1:
            m.set(x, int(s - 0.5), z, "polished_andesite_slab[type=bottom]")
        else:
            m.set(x, int(s) - 1, z, "polished_andesite_slab[type=top]")
    m.fill(cx, 0, cz, cx, int(top_s) + 1, cz, "iron_bars")


def build(m):
    # ---------------- foundation, floors
    m.fill(X0, -1, Z0, X1, 0, Z1, PLINTH)
    m.fill(X0 + 1, 0, Z0 + 1, X1 - 1, 0, Z1 - 1, "oak_planks")
    # ---------------- walls
    m.walls(X0, Z0, X1, Z1, 1, 9, YELLOW)
    m.fill(X1, 1, Z0, X1, 4, Z1, GRAY)                       # east ground floor: corrugated cladding
    m.fill(X0, 1, 20, X0, 4, Z1, GRAY)                       # west ground floor, south part
    m.fill(X0 + 1, 5, Z0 + 1, X1 - 1, 5, Z1 - 1, "oak_planks")  # upper floor
    m.fill(X0 + 1, E, Z0 + 1, X1 - 1, E, Z1 - 1, "oak_planks")  # attic floor
    # canopy between the floors on the east side
    m.fill(X1 + 1, 5, 4, X1 + 1, 5, 25, "polished_deepslate_slab[type=bottom]")

    # ---------------- windows, upper floor (y 6..8)
    for z1 in (3, 8, 13, 18, 24):                            # west
        window(m, "x", X0, z1, z1 + 1, 6, 8)
    m.fill(X0, 6, 27, X0, 8, 28, GLASS)                      # glazed corner (SW)
    for z1 in (5, 8, 11, 17, 20, 23):                        # east
        window(m, "x", X1, z1, z1 + 1, 6, 8)
    window(m, "x", X1, 14, 15, 8, 8)                         # small window
    window(m, "z", Z1, 15, 16, 6, 8)                         # south gable
    window(m, "z", Z1, 22, 23, 6, 8)
    # ---------------- ground floor windows
    window(m, "x", X1, 21, 25, 1, 4, frame=ORANGE, mullions=(23,))          # east, small
    window(m, "x", X1, 5, 13, 1, 4, frame=ORANGE, mullions=(7, 9, 11))      # east, big
    window(m, "z", Z1, 15, 16, 1, 3)                                        # south
    window(m, "z", Z1, 19, 20, 1, 3)
    window(m, "x", X0, 25, 27, 1, 4, frame=ORANGE)                          # west (court side)
    # ---------------- doors
    door(m, X1, 1, 19, "east", "acacia_door")
    m.set(X1 + 1, 0, 19, "polished_andesite_stairs[facing=west]")
    m.fill(X1 + 1, 0, 18, X1 + 1, 1, 18, "iron_bars"); m.fill(X1 + 1, 0, 20, X1 + 1, 1, 20, "iron_bars")
    door(m, 24, 1, Z1, "south", "oak_door")
    m.set(24, 0, Z1 + 1, "polished_andesite_stairs[facing=north]")
    door(m, X0, 1, 22, "west", "acacia_door")
    m.set(X0 - 1, 0, 22, "polished_andesite_stairs[facing=east]")

    # ---------------- balconies + spiral fire escapes (east side)
    for zb, zd in ((26, 27), (1, 2)):           # balcony z range start, door z
        m.fill(X1 + 1, 5, zb, X1 + 2, 5, zb + 2, "smooth_stone_slab[type=top]")
        door(m, X1, 6, zd, "east", "spruce_door")
    m.fill(X1 + 1, 6, 26, X1 + 2, 6, 26, "iron_bars"); m.set(X1 + 2, 6, 27, "iron_bars")
    m.fill(X1 + 1, 6, 3, X1 + 2, 6, 3, "iron_bars"); m.set(X1 + 2, 6, 2, "iron_bars")
    spiral(m, X1 + 3, Z1 + 1, 11, 5)
    spiral(m, X1 + 3, Z0 - 1, 11, 5, mirror=True)
    roof(m)
    # attic balconies on both gables, with a walkway to the spiral stair
    for zg, zz, zo, zr in ((Z1, Z1 + 1, Z1 + 2, Z1 + 3), (Z0, Z0 - 1, Z0 - 2, Z0 - 3)):
        m.fill(21, E, zz, 25, E, zo, "smooth_stone_slab[type=top]")
        m.fill(26, E, zo, X1 + 1, E, zo, "smooth_stone_slab[type=top]")
        m.fill(21, E + 1, zr, X1 + 1, E + 1, zr, "iron_bars")
        m.fill(20, E + 1, zz, 20, E + 1, zo, "iron_bars")
        m.fill(26, E + 1, zz, 26, E + 1, zz, "iron_bars")
        m.fill(21, E + 1, zz, 25, E + 3, zo, "air")
        m.fill(26, E + 1, zo, X1 + 1, E + 2, zo, "air")
        # gable windows + balcony door
        window(m, "z", zg, 16, 17, 11, 12)
        window(m, "z", zg, 19, 20, 11, 12)
        window(m, "z", zg, 19, 20, 14, 14)
        door(m, 23, 11, zg, "south" if zg == Z1 else "north", "spruce_door")

    interior(m)


def interior(m):
    # ---------------- ground floor (walk y=1..4)  and upper floor (walk y=6..9)
    for fy in (1, 6):
        top = fy + 3
        m.fill(17, fy, Z0 + 1, 17, top, Z1 - 1, INTERIOR)           # corridor wall
        m.fill(18, fy, 8, X1 - 1, top, 8, INTERIOR)                 # stairwell | classroom A
        m.fill(18, fy, 19, X1 - 1, top, 19, INTERIOR)               # classroom A | B
        for z in (5, 13, 24):
            door(m, 17, fy, z, "east", "oak_door")
        lanterns(m, 14, 16, Z0 + 1, Z1 - 1, top, step=6)
        for (za, zb) in ((9, 18), (20, 28)):
            lanterns(m, 18, X1 - 1, za, zb, top, step=4)
            # blackboard on the north wall of each classroom, desks facing it
            m.fill(20, fy + 1, za, 24, fy + 2, za, "black_concrete")
            m.set(22, fy, za + 1, "spruce_stairs[facing=south]")
            desks(m, 19, 25, za + 3, zb - 1, fy, facing="north")
            m.set(X1 - 1, fy, zb, "bookshelf"); m.set(X1 - 1, fy + 1, zb, "bookshelf")
            m.set(18, fy, zb, "potted_red_tulip")
        m.fill(14, fy, Z1 - 2, 14, fy + 1, Z1 - 1, "bookshelf")
    # stairs: ground -> upper (rising east, z 2..3), upper -> attic (rising west, z 5..6)
    m.fill(20, 5, 2, 24, 5, 3, "air")
    for i in range(5):
        m.fill(20 + i, 1 + i, 2, 20 + i, 1 + i, 3, "oak_stairs[facing=east]")
    m.fill(20, E, 5, 24, E, 6, "air")
    for i in range(5):
        m.fill(24 - i, 6 + i, 5, 24 - i, 6 + i, 6, "oak_stairs[facing=west]")
    m.fill(20, 6, 4, 23, 6, 4, "oak_fence"); m.fill(19, 6, 2, 19, 6, 3, "oak_fence")
    m.fill(20, 11, 4, 24, 11, 4, "oak_fence"); m.fill(20, 11, 7, 24, 11, 7, "oak_fence")
    m.fill(25, 11, 5, 25, 11, 6, "oak_fence")
    # doors to the annex
    for z in (8, 16):
        m.fill(X0, 1, z, X0, 2, z, "air")
        m.set(X0 - 1, 0, z, "oak_stairs[facing=east]")
    # ---------------- attic: library / art room
    for x in (15, 25):
        m.fill(x, 11, 9, x, 12, 26, "bookshelf")
    for z in (11, 16, 21):
        table_with_chairs(m, 18, 11, z, length=5, top="spruce_slab[type=top]", chair="spruce_stairs")
    for x in (15, 25):
        for z in range(10, 27, 4):
            m.set(x, 13, z, "lantern")
    m.set(22, 11, 27, "loom"); m.set(21, 11, 27, "cartography_table"); m.set(23, 11, 27, "crafting_table")
