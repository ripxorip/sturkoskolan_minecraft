"""The modern parts of Sturköskolan that connect to the yellow building.

Volumes (block coords, x east, z south), derived from OpenStreetMap + the aerial:
  V1  NW low preschool wing          V2  preschool (solar roof)
  V3  porthole hall (library)        V4  the tall cream "wedge" (entrance hall)
  V5  corridor (solar roof)          V6  cream wing (orange windows)
  V7  gray wing                      V8  clerestory box
  V9  dining hall (glass roof)       V10 annex (fritidsgård + slöjd)
  V11 kitchen / connector            V12 east wing (classrooms)
  V13 gymnastics hall
"""
from lib import *


def volume(m, x1, z1, x2, z2, h, wall, floor="light_gray_concrete"):
    """Floor at y=-1 and walls from y=-1 to y=h (inclusive)."""
    m.fill(x1, -1, z1, x2, -1, z2, floor)
    m.walls(x1, z1, x2, z2, -1, h, wall)


def hang_lights(m, x1, x2, z1, z2, y_from, step=5, kind="lantern"):
    """Hang lanterns from whatever ceiling is above each grid point."""
    for x in range(x1 + 2, x2 - 1, step):
        for z in range(z1 + 2, z2 - 1, step):
            y = y_from
            while y < y_from + 20 and m.get(x, y + 1, z) in ("<keep>", "air"):
                y += 1
            if m.get(x, y, z) in ("<keep>", "air") and m.get(x, y + 1, z) not in ("<keep>", "air"):
                m.set(x, y, z, f"{kind}[hanging=true]")


def solar_panels(m, x1, x2, z1, z2, every=1):
    """Daylight detectors as solar panels on top of a roof (see notes in lib)."""
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            if (z - z1) % (every + 1):
                continue
            y = 30
            while y > 0 and m.get(x, y, z) in ("<keep>", "air"):
                y -= 1
            s = m.get(x, y, z)
            if "slab" in s and "type=bottom" in s:
                m.set(x, y, z, "daylight_detector")
            else:
                m.set(x, y + 1, z, "daylight_detector")


def roof_top_y(m, x, z, start=30):
    y = start
    while y > -1 and m.get(x, y, z) in ("<keep>", "air"):
        y -= 1
    return y


def build(m):
    # ===================================================== V2 preschool
    volume(m, 2, -56, 17, -33, 4, CREAM, floor="birch_planks")
    mono_roof(m, 2, 17, -56, -33, 6.0, 9.0, "north", wall=CREAM, wall_top=4, overhang=1)
    # big green-framed windows towards the playground (north)
    window(m, "z", -56, 3, 7, 0, 4, frame=GREEN, mullions=(5,), transoms=(2,))
    window(m, "z", -56, 10, 16, 0, 4, frame=GREEN, mullions=(12, 14), transoms=(2,))
    double_door(m, "z", -56, 8, 0, "north", "birch_door")
    m.fill(8, 2, -56, 9, 2, -56, "glass_pane"); m.fill(8, 3, -56, 9, 4, -56, GREEN)
    # preschool interior
    for x, c in ((4, "red"), (7, "yellow"), (10, "lime"), (13, "light_blue")):
        m.fill(x, 0, -52, x + 2, 0, -49, f"{c}_carpet")
    for z in (-45, -40):
        table_with_chairs(m, 5, 0, z, length=3, top="birch_slab[type=top]", chair="birch_stairs")
        table_with_chairs(m, 11, 0, z, length=3, top="birch_slab[type=top]", chair="birch_stairs")
    for z in (-54, -51, -48):  # nap beds along the east wall
        m.set(16, 0, z, "red_bed[part=head,facing=east]"); m.set(15, 0, z, "red_bed[part=foot,facing=east]")
    for x in (3, 4):
        m.set(x, 0, -35, "chest[facing=south]")
    m.set(5, 0, -35, "barrel[facing=up]"); m.set(6, 0, -35, "note_block")
    m.set(3, 0, -55, "potted_dandelion")

    # ===================================================== V1 NW low wing
    volume(m, -12, -56, 2, -48, 3, CREAM, floor="birch_planks")
    mono_roof(m, -12, 2, -56, -48, 5.0, 6.0, "north", wall=CREAM, wall_top=3, overhang=1)
    window(m, "x", -12, -55, -51, 0, 3, frame=GREEN, mullions=(-53,))
    window(m, "z", -56, -10, -6, 0, 3, frame=GREEN, mullions=(-8,))
    window(m, "z", -56, -3, 1, 0, 3, frame=GREEN, mullions=(-1,))
    door(m, -12, 0, -49, "west", "birch_door")
    m.fill(-10, 0, -54, -6, 0, -50, "pink_carpet")
    m.fill(-4, 0, -54, 0, 0, -51, "cyan_carpet")
    m.set(-11, 0, -55, "crafting_table"); m.set(1, 0, -55, "chest[facing=south]")

    # ===================================================== V3 porthole hall: library
    volume(m, -16, -48, 2, -33, 4, GRAY, floor="spruce_planks")
    mono_roof(m, -16, 2, -48, -33, 6.0, 10.0, "north", wall=GRAY, wall_top=4, overhang=1)
    for zc in (-45, -42, -38, -35):
        porthole(m, "x", -16, zc, 2)
    porthole(m, "z", -48, -14, 2)
    # library interior
    for z in (-46, -43, -40):
        m.fill(-9, 0, z, -1, 2, z, "bookshelf")
    m.fill(-15, 0, -47, -15, 2, -47, "bookshelf")
    m.fill(1, 0, -47, 1, 2, -36, "bookshelf")
    for z in (-37,):
        table_with_chairs(m, -9, 0, z, length=4, top="dark_oak_slab[type=top]", chair="dark_oak_stairs")
    m.set(-14, 0, -36, "lectern[facing=east]"); m.set(-3, 0, -36, "lectern[facing=west]")
    m.fill(-13, 0, -46, -11, 0, -38, "red_carpet")
    m.set(-12, 0, -34, "potted_fern")

    # ===================================================== V4 the wedge: entrance hall
    volume(m, -16, -33, -4, -23, 8, CREAM, floor="polished_diorite")
    for z in range(-33, -22):
        t = min(9 + (z + 33), 17)
        st = "polished_andesite_stairs[facing=south]" if z <= -25 else "polished_andesite"
        for x in range(-16, -3):
            m.set(x, t, z, st)
        for x in (-16, -4):
            m.fill(x, 9, z, x, t - 1, z, CREAM)
    m.fill(-16, 9, -23, -4, 16, -23, CREAM)   # tall south face
    for zc, yc in ((-31, 7), (-28, 8), (-25, 9)):
        porthole(m, "x", -16, zc, yc, ring="stripped_spruce_wood", center="light_blue_stained_glass")
    # entrance: teal doors, side lights, transom
    m.fill(-16, 0, -30, -16, 3, -27, "warped_planks")
    m.fill(-16, 0, -30, -16, 2, -30, "light_blue_stained_glass_pane")
    m.fill(-16, 0, -27, -16, 2, -27, "light_blue_stained_glass_pane")
    double_door(m, "x", -16, -29, 0, "west", "warped_door")
    m.fill(-16, 2, -29, -16, 2, -28, "light_blue_stained_glass_pane")
    # blue steel + glass canopy
    for z in (-31, -26):
        m.fill(-21, 0, z, -21, 4, z, "light_blue_concrete")
    for x in range(-21, -16):
        y = 4 if x <= -19 else 5
        m.set(x, y, -31, "light_blue_concrete"); m.set(x, y, -26, "light_blue_concrete")
        m.fill(x, y, -30, x, y, -27, "light_blue_stained_glass")
    m.fill(-21, 4, -31, -21, 4, -26, "light_blue_concrete")
    # entrance hall interior
    m.fill(-14, 0, -25, -11, 0, -24, "spruce_slab[type=top]")   # reception counter
    m.fill(-15, 0, -32, -13, 0, -32, "spruce_stairs[facing=north]")
    hang_lights(m, -15, -5, -32, -24, 6, step=4)
    m.fill(-12, -1, -31, -8, -1, -26, "light_blue_terracotta")   # entrance mat

    # ===================================================== V5 corridor with solar roof
    volume(m, -4, -33, 17, -23, 5, CREAM)
    flat_roof(m, -4, 17, -33, -23, 6, FLAT)

    # ===================================================== V6 cream wing, V7 gray wing (classrooms)
    volume(m, -16, -23, 5, -13, 4, CREAM)
    flat_roof(m, -16, 5, -23, -13, 5, FLAT, fascia="brown_terracotta", overhang=1)
    window(m, "x", -16, -22, -19, 1, 4, frame=ORANGE, mullions=())
    window(m, "x", -16, -17, -14, 1, 4, frame=ORANGE, mullions=())
    volume(m, -16, -13, 5, -3, 4, GRAY)
    flat_roof(m, -16, 5, -13, -3, 5, FLAT, fascia="brown_terracotta", overhang=1)
    window(m, "x", -16, -11, -7, 1, 4, frame=ORANGE, mullions=(-9,))
    door(m, -16, 0, -5, "west", "acacia_door")
    m.fill(-16, 2, -5, -16, 3, -5, ORANGE)
    m.fill(-6, 0, -13, 4, 3, -13, INTERIOR)                     # partition between the classrooms
    desks(m, -14, -9, -21, -15, 0, facing="north")
    m.fill(-14, 1, -22, -10, 2, -22, "black_concrete")
    desks(m, -14, -9, -11, -5, 0, facing="north")
    m.fill(-14, 1, -12, -10, 2, -12, "black_concrete")
    # teachers' room in the east part of V7
    table_with_chairs(m, -2, 0, -8, length=4, top="oak_slab[type=top]", chair="oak_stairs")
    m.set(3, 0, -11, "smoker[facing=west]"); m.set(3, 0, -10, "cauldron"); m.set(3, 0, -9, "barrel[facing=up]")

    # ===================================================== V8 clerestory box
    m.walls(-8, -20, -2, -14, 5, 9, CREAM)
    flat_roof(m, -8, -2, -20, -14, 10, FLAT)
    m.fill(-7, 5, -19, -3, 5, -15, "air")
    window(m, "x", -8, -19, -15, 6, 8, mullions=())
    window(m, "z", -20, -7, -3, 6, 8, mullions=())
    m.fill(-8, 7, -17, -8, 7, -17, CREAM); m.fill(-5, 7, -20, -5, 7, -20, CREAM)

    # ===================================================== V9 dining hall with glass roof
    volume(m, 5, -23, 17, -3, 6, CREAM, floor="smooth_stone")
    for x in range(5, 18):
        for z in range(-23, -2):
            frame = (x - 5) % 4 == 0 or (z + 23) % 4 == 0
            m.set(x, 7, z, METAL if frame else "glass")
    for z in (-19, -14, -9):
        table_with_chairs(m, 7, 0, z, length=8, top="birch_slab[type=top]", chair="birch_stairs")
    m.set(6, 0, -21, "potted_azalea_bush"); m.set(6, 0, -5, "potted_azalea_bush")

    # ===================================================== V10 annex: slöjd + fritidsgård
    volume(m, -11, -3, 13, 19, 4, GRAY)
    m.fill(-11, -1, 2, -11, 4, 14, CREAM)
    flat_roof(m, -11, 13, -3, 19, 5, FLAT, fascia="smooth_stone_slab[type=top]", overhang=1)
    window(m, "x", -11, -2, 1, 1, 4, frame=ORANGE, mullions=())
    window(m, "x", -11, 4, 6, 1, 3)
    window(m, "x", -11, 10, 12, 1, 3)
    door(m, -11, 0, 17, "west", "acacia_door")
    window(m, "x", -11, 15, 16, 0, 3, frame=ORANGE)
    m.fill(-11, 2, 17, -11, 3, 17, ORANGE)
    m.set(-12, 2, 8, "blue_concrete")
    m.sign(-13, 2, 8, "oak_wall_sign[facing=west]", ["", "Sturkö", "Fritidsgård", ""])
    for x1 in (-9, -2, 5):
        window(m, "z", 19, x1, x1 + 4, 1, 4, frame=ORANGE, mullions=(x1 + 2,))
    m.fill(1, 0, -2, 1, 4, 18, INTERIOR)                         # slöjd | fritidsgård
    m.fill(1, 0, 6, 1, 1, 7, "air")
    for z in (0, 4, 8, 12, 16):                                  # slöjd (woodwork) benches
        m.set(-6, 0, z, "crafting_table"); m.set(-5, 0, z, "crafting_table")
    m.set(-9, 0, -1, "smithing_table"); m.set(-8, 0, -1, "grindstone[face=floor,facing=north]")
    m.set(-7, 0, -1, "stonecutter[facing=north]"); m.set(-2, 0, -1, "fletching_table")
    m.set(-9, 0, 18, "anvil[facing=north]"); m.set(-1, 0, 18, "loom")
    # fritidsgård: ping-pong table, sofas, music corner
    m.fill(5, 0, 3, 6, 0, 7, "spruce_slab[type=top]"); m.fill(5, 1, 3, 6, 1, 7, "green_carpet")
    m.fill(5, 1, 5, 6, 1, 5, "white_carpet")
    for z in range(12, 17):
        m.set(12, 0, z, "red_wool"); m.set(11, 0, z, "red_carpet")
    m.set(9, 0, 18, "jukebox"); m.set(8, 0, 18, "note_block"); m.set(10, 0, 18, "note_block")
    m.fill(3, 0, 17, 5, 0, 18, "light_blue_carpet")

    # ===================================================== V11 kitchen + connector
    volume(m, 17, -29, 27, 0, 5, PALE, floor="white_concrete")
    flat_roof(m, 17, 27, -29, 0, 6, FLAT)
    volume(m, 13, -3, 17, 0, 5, PALE, floor="light_gray_concrete")
    flat_roof(m, 13, 17, -3, 0, 6, FLAT)
    door(m, 27, 0, -3, "east", "warped_door")
    m.fill(17, 1, -16, 17, 2, -11, "air")                        # serving hatch
    m.fill(17, 0, -16, 17, 0, -11, "smooth_quartz_slab[type=top]")
    for z in range(-27, -18, 2):
        m.set(26, 0, z, "smoker[facing=west]"); m.set(26, 0, z + 1, "furnace[facing=west]")
    m.fill(20, 0, -24, 23, 0, -21, "smooth_quartz_slab[type=top]")
    for z in (-10, -8, -6):
        m.set(26, 0, z, "cauldron"); m.set(25, 0, z, "barrel[facing=up]")
    m.fill(19, 0, -17, 23, 0, -17, "smooth_quartz_slab[type=top]")

    # ===================================================== V12 east wing
    volume(m, 27, -28, 41, -6, 5, PALE)
    flat_roof(m, 27, 41, -28, -6, 6, FLAT, parapet="birch_slab[type=bottom]")
    for z1 in range(-26, -8, 4):
        window(m, "x", 41, z1, z1 + 2, 1, 3)
        m.fill(41, 1, z1 + 3, 41, 3, z1 + 3, "white_concrete")
    m.fill(41, 0, -27, 41, 0, -7, "white_concrete"); m.fill(41, 4, -27, 41, 4, -7, "white_concrete")
    for x1 in range(29, 40, 4):
        window(m, "z", -6, x1, x1 + 2, 1, 3)
        m.fill(x1 + 3, 1, -6, x1 + 3, 3, -6, "white_concrete")
    m.fill(28, 0, -6, 40, 0, -6, "white_concrete"); m.fill(28, 4, -6, 40, 4, -6, "white_concrete")
    m.fill(28, 0, -17, 40, 4, -17, INTERIOR)
    m.set(33, 0, -17, "air"); m.set(33, 1, -17, "air")
    for (za, zb) in ((-27, -18), (-16, -7)):
        desks(m, 30, 39, za + 3, zb, 0, facing="north")
        m.fill(32, 1, za, 37, 2, za, "black_concrete")
    # rooftop ventilation housing ("C" shape seen on the aerial)
    m.walls(31, -24, 38, -12, 7, 8, "light_gray_concrete")
    m.fill(31, 7, -21, 31, 8, -15, "air")
    flat_roof(m, 32, 37, -23, -13, 9, "light_gray_concrete")
    m.fill(31, 9, -24, 38, 9, -24, "light_gray_concrete"); m.fill(31, 9, -12, 38, 9, -12, "light_gray_concrete")
    m.fill(38, 9, -24, 38, 9, -12, "light_gray_concrete")

    # ===================================================== V13 gymnastics hall
    volume(m, 17, -56, 41, -29, 10, PALE, floor="birch_planks")
    flat_roof(m, 17, 41, -56, -29, 11, FLAT, parapet="birch_slab[type=bottom]")
    for x1 in range(19, 39, 4):
        window(m, "z", -56, x1, x1 + 2, 7, 9)
        window(m, "z", -29, x1, x1 + 2, 8, 9)
    # canopy, doors, AC units on the Makes väg side
    m.fill(42, 4, -46, 43, 4, -30, "smooth_stone_slab[type=top]")
    for z in range(-46, -29, 4):
        m.fill(43, 0, z, 43, 3, z, "iron_bars")
    door(m, 41, 0, -43, "east", "warped_door")
    door(m, 41, 0, -34, "east", "warped_door")
    for z in (-39, -38, -36, -35):
        m.set(42, 5, z, "white_concrete")
    m.set(42, 6, -38, "iron_trapdoor[facing=east,half=bottom]")
    m.set(42, 6, -35, "iron_trapdoor[facing=east,half=bottom]")
    # rooftop: louvred box + silver cowl
    m.fill(32, 12, -47, 36, 13, -43, "light_gray_concrete")
    m.fill(32, 13, -47, 36, 13, -47, "iron_bars")
    m.set(37, 12, -36, "iron_block"); m.set(37, 13, -36, "waxed_lightning_rod")
    # gym interior: court lines, wall bars, ropes, goals, benches
    for x in range(19, 40):
        m.set(x, -1, -54, "red_concrete"); m.set(x, -1, -31, "red_concrete")
    for z in range(-54, -30):
        m.set(19, -1, z, "red_concrete"); m.set(39, -1, z, "red_concrete")
    for z in range(-54, -30):
        m.set(29, -1, z, "red_concrete")
    for a in range(0, 360, 10):
        import math as _m
        m.set(29 + round(4 * _m.cos(_m.radians(a))), -1, -42 + round(4 * _m.sin(_m.radians(a))), "red_concrete")
    for x in range(19, 40, 2):
        m.fill(x, 0, -55, x, 5, -55, "ladder[facing=south]")
    for x, z in ((25, -36), (27, -36), (29, -36), (31, -36), (33, -36)):
        m.fill(x, 2, z, x, 10, z, "iron_chain[axis=y]")
    for gx, back in ((19, 18), (39, 40)):
        m.fill(back, 0, -44, back, 2, -40, "iron_bars")
        m.fill(min(gx, back), 0, -44, max(gx, back), 2, -44, "iron_bars")
        m.fill(min(gx, back), 0, -40, max(gx, back), 2, -40, "iron_bars")
        m.fill(gx, 2, -44, gx, 2, -40, "iron_bars")
    m.fill(20, 0, -30, 38, 0, -30, "spruce_slab[type=bottom]")
    m.fill(34, 0, -53, 38, 0, -49, "blue_carpet")
    m.sign(29, 3, -30, "oak_wall_sign[facing=north]", ["", "Gymnastiksal", "", ""])

    # ===================================================== doors / openings between volumes
    opening(m, "x", -4, -30, -26, 0, 3)         # entrance hall -> corridor
    opening(m, "z", -33, -12, -10, 0, 2)        # entrance hall -> library
    opening(m, "z", -23, -12, -10, 0, 2)        # entrance hall -> classrooms
    double_door(m, "z", -33, 8, 0, "north", "birch_door")   # corridor -> preschool
    opening(m, "z", -33, -2, -1, 0, 2)          # corridor -> library
    opening(m, "z", -23, 9, 12, 0, 3)           # corridor -> dining hall
    door(m, -1, 0, -23, "south", "oak_door")    # corridor -> classroom wing
    opening(m, "x", 17, -31, -30, 0, 2)         # corridor -> gym
    opening(m, "x", 17, -27, -25, 0, 2)         # corridor -> kitchen/connector
    opening(m, "z", -3, 8, 9, 0, 2)             # dining hall -> annex
    opening(m, "x", 5, -18, -17, 0, 2)          # dining hall -> V6
    opening(m, "x", 5, -8, -7, 0, 2)            # dining hall -> V7
    opening(m, "x", 17, -2, -1, 0, 2)           # connector -> kitchen corridor
    opening(m, "x", 13, -2, -1, 0, 2)           # connector -> annex
    opening(m, "z", 0, 15, 16, 1, 2)            # connector -> yellow building (one step up)
    m.fill(15, 0, -1, 16, 0, -1, "polished_andesite_stairs[facing=south]")
    opening(m, "x", 27, -24, -23, 0, 2)         # connector -> east wing
    opening(m, "x", 27, -12, -11, 0, 2)
    opening(m, "z", -48, -6, -5, 0, 2)          # NW wing -> library
    opening(m, "x", 2, -52, -51, 0, 2)          # NW wing -> preschool
    opening(m, "x", 2, -40, -39, 0, 2)          # library -> preschool
    opening(m, "z", -29, 20, 21, 0, 2)          # gym -> kitchen corridor

    # ===================================================== roofs extras, lights
    solar_panels(m, -2, 15, -31, -25, every=1)
    solar_panels(m, 4, 11, -54, -37, every=0)
    for z in range(-55, -33):                   # glazed spine on the preschool roof
        for x in (13, 14, 15):
            y = roof_top_y(m, x, z)
            if y > 3:
                m.set(x, y, z, "glass")
    for (x1, x2, z1, z2) in ((2, 17, -56, -33), (-12, 2, -56, -48), (-16, 2, -48, -33), (-4, 17, -33, -23),
                             (-16, 5, -23, -3), (5, 17, -23, -3), (-11, 13, -3, 19), (17, 27, -29, 0),
                             (27, 41, -28, -6), (17, 41, -56, -29)):
        hang_lights(m, x1, x2, z1, z2, 2, step=5)
