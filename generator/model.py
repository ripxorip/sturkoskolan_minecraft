"""Voxel model of the build: a palette-indexed numpy array plus drawing helpers.

Coordinates: x = east, z = south (Minecraft convention), y = height relative to
ground: y = 0 is the first air layer above the grass, y = -1 is the grass layer.
"""
import numpy as np

KEEP = 0  # palette index meaning "leave the generated terrain untouched"


def parse_state(s):
    """'oak_stairs[facing=east,half=bottom]' -> ('oak_stairs', {'facing': 'east', ...})"""
    s = s.replace("minecraft:", "")
    if "[" in s:
        name, rest = s.split("[", 1)
        props = dict(kv.split("=") for kv in rest.rstrip("]").split(",") if kv)
    else:
        name, props = s, {}
    return name, props


def make_state(name, props):
    if not props:
        return name
    return name + "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"


class Model:
    def __init__(self, x0, x1, y0, y1, z0, z1):
        self.x0, self.x1, self.y0, self.y1, self.z0, self.z1 = x0, x1, y0, y1, z0, z1
        self.a = np.zeros((x1 - x0, y1 - y0, z1 - z0), np.int32)
        self.pal = ["<keep>"]
        self.idx = {"<keep>": 0}
        self.block_entities = {}  # (x,y,z) -> snbt string (applied with setblock after build)

    # ---- palette -------------------------------------------------------
    def id(self, state):
        if state is None:
            return KEEP
        name, props = parse_state(state)
        state = make_state(name, props)
        i = self.idx.get(state)
        if i is None:
            i = len(self.pal)
            self.pal.append(state)
            self.idx[state] = i
        return i

    def inside(self, x, y, z):
        return self.x0 <= x < self.x1 and self.y0 <= y < self.y1 and self.z0 <= z < self.z1

    # ---- primitives ----------------------------------------------------
    def set(self, x, y, z, state):
        if self.inside(x, y, z):
            self.a[x - self.x0, y - self.y0, z - self.z0] = self.id(state)

    def get(self, x, y, z):
        if not self.inside(x, y, z):
            return "<keep>"
        return self.pal[self.a[x - self.x0, y - self.y0, z - self.z0]]

    def getname(self, x, y, z):
        return parse_state(self.get(x, y, z))[0]

    def fill(self, x1, y1, z1, x2, y2, z2, state):
        """Inclusive box fill (corners in any order)."""
        xa, xb = sorted((x1, x2)); ya, yb = sorted((y1, y2)); za, zb = sorted((z1, z2))
        xa, xb = max(xa, self.x0), min(xb, self.x1 - 1)
        ya, yb = max(ya, self.y0), min(yb, self.y1 - 1)
        za, zb = max(za, self.z0), min(zb, self.z1 - 1)
        if xa > xb or ya > yb or za > zb:
            return
        self.a[xa - self.x0:xb - self.x0 + 1, ya - self.y0:yb - self.y0 + 1,
               za - self.z0:zb - self.z0 + 1] = self.id(state)

    def replace(self, x1, y1, z1, x2, y2, z2, old, new):
        xa, xb = sorted((x1, x2)); ya, yb = sorted((y1, y2)); za, zb = sorted((z1, z2))
        sub = self.a[xa - self.x0:xb - self.x0 + 1, ya - self.y0:yb - self.y0 + 1,
                     za - self.z0:zb - self.z0 + 1]
        sub[sub == self.id(old)] = self.id(new)

    def walls(self, x1, z1, x2, z2, y1, y2, state):
        """Hollow rectangle of walls (inclusive)."""
        self.fill(x1, y1, z1, x2, y2, z1, state)
        self.fill(x1, y1, z2, x2, y2, z2, state)
        self.fill(x1, y1, z1, x1, y2, z2, state)
        self.fill(x2, y1, z1, x2, y2, z2, state)

    def sign(self, x, y, z, state, lines, color="black", glow=False):
        """Place a sign (standing or wall) with up to 4 lines of text."""
        self.set(x, y, z, state)
        lines = (list(lines) + ["", "", "", ""])[:4]
        msgs = ",".join('{text:"%s",color:"%s"}' % (l.replace('"', '\\"'), color) for l in lines)
        glow_s = "true" if glow else "false"
        snbt = "{front_text:{messages:[%s],has_glowing_text:%s},back_text:{messages:[%s],has_glowing_text:%s}}" % (
            msgs, glow_s, msgs, glow_s)
        self.block_entities[(x, y, z)] = snbt

    # ---- iteration -----------------------------------------------------
    def nonkeep(self):
        xs, ys, zs = np.nonzero(self.a)
        return xs + self.x0, ys + self.y0, zs + self.z0
