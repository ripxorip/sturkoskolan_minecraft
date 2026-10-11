"""Small Minecraft-style renderer for previewing the voxel model.

Uses the real blockstate/model/texture assets from the Minecraft client jar,
renders every block's model elements as textured cuboids (orthographic,
isometric or straight elevation) and composites them with the painter's
algorithm.
"""
import json
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image

from model import parse_state
from blockrules import is_full

GRASS_TINT = (145, 189, 89)
FOLIAGE_TINT = {"birch_leaves": (128, 167, 85), "spruce_leaves": (97, 153, 97)}
DEFAULT_FOLIAGE = (119, 171, 47)

DEFAULT_PROPS = {"half": "bottom", "shape": "straight", "type": "bottom", "axis": "y",
                 "facing": "north", "open": "false", "powered": "false", "hinge": "left",
                 "north": "false", "south": "false", "east": "false", "west": "false",
                 "up": "true", "down": "false", "snowy": "false", "lit": "false",
                 "hanging": "false", "waterlogged": "false", "rotation": "0", "face": "wall",
                 "attachment": "floor", "persistent": "true", "distance": "7",
                 "part": "foot", "occupied": "false", "in_wall": "false"}
WALL_SIDE_DEFAULT = "none"

# direction vectors in world space
DIRV = {"up": (0, 1, 0), "down": (0, -1, 0), "north": (0, 0, -1), "south": (0, 0, 1),
        "west": (-1, 0, 0), "east": (1, 0, 0)}
MC_SHADE = {"up": 1.0, "down": 0.5, "north": 0.8, "south": 0.8, "east": 0.6, "west": 0.6}
TRANSPARENT_NAMES = ("glass", "ice", "_pane", "iron_bars", "_leaves")


class Assets:
    def __init__(self, root):
        self.root = root
        self.tex_cache = {}

    def _json(self, kind, name):
        name = name.replace("minecraft:", "")
        p = os.path.join(self.root, "assets/minecraft", kind, name + ".json")
        with open(p) as f:
            return json.load(f)

    @lru_cache(maxsize=None)
    def model(self, name):
        """Resolve a model with parents -> (textures dict, elements list)."""
        name = name.replace("minecraft:", "")
        if name.startswith("builtin/"):
            return {}, None
        try:
            j = self._json("models", name)
        except FileNotFoundError:
            return {}, None
        tex, elements = {}, None
        if "parent" in j:
            ptex, pel = self.model(j["parent"])
            tex.update(ptex)
            elements = pel
        tex.update(j.get("textures", {}))
        if "elements" in j:
            elements = j["elements"]
        return tex, elements

    def texture(self, ref, textures, depth=0):
        while ref.startswith("#") and depth < 10:
            ref = textures.get(ref[1:], "")
            depth += 1
        if not ref or ref.startswith("#"):
            return None
        ref = ref.replace("minecraft:", "")
        if ref in self.tex_cache:
            return self.tex_cache[ref]
        p = os.path.join(self.root, "assets/minecraft/textures", ref + ".png")
        img = None
        if os.path.exists(p):
            img = Image.open(p).convert("RGBA")
            if img.height > img.width:  # animated strip: first frame
                img = img.crop((0, 0, img.width, img.width))
        self.tex_cache[ref] = img
        return img

    @lru_cache(maxsize=None)
    def parts(self, state):
        """Block state -> list of (model_name, x_rot, y_rot)."""
        name, props = parse_state(state)
        try:
            bs = self._json("blockstates", name)
        except FileNotFoundError:
            return ()

        def val(k):
            if k in props:
                return props[k]
            if name.endswith("_wall") and k in ("north", "south", "east", "west"):
                return WALL_SIDE_DEFAULT
            return DEFAULT_PROPS.get(k)

        def match_kv(key):
            if key == "":
                return True
            for kv in key.split(","):
                k, v = kv.split("=")
                cur = val(k)
                if cur is not None and cur != v:
                    return False
            return True

        def cond_ok(c):
            if "OR" in c:
                return any(cond_ok(x) for x in c["OR"])
            if "AND" in c:
                return all(cond_ok(x) for x in c["AND"])
            for k, v in c.items():
                cur = val(k)
                if cur is None or cur not in str(v).split("|"):
                    return False
            return True

        out = []
        if "variants" in bs:
            for key, v in bs["variants"].items():
                if match_kv(key):
                    if isinstance(v, list):
                        v = v[0]
                    out.append((v["model"], v.get("x", 0), v.get("y", 0)))
                    break
        else:
            for part in bs["multipart"]:
                if "when" not in part or cond_ok(part["when"]):
                    ap = part["apply"]
                    if isinstance(ap, list):
                        ap = ap[0]
                    out.append((ap["model"], ap.get("x", 0), ap.get("y", 0)))
        return tuple(out)


def rot_x(p, deg):
    # rotate around X axis through block centre (8,8,8); MC rotates "x" first
    if deg % 360 == 0:
        return p
    x, y, z = p[0], p[1] - 8, p[2] - 8
    for _ in range((deg // 90) % 4):
        y, z = -z, y  # 90 degrees
    return (x, y + 8, z + 8)


def rot_y(p, deg):
    if deg % 360 == 0:
        return p
    x, y, z = p[0] - 8, p[1], p[2] - 8
    for _ in range((deg // 90) % 4):
        x, z = -z, x  # 90 degrees clockwise seen from above (MC convention)
    return (x + 8, y, z + 8)


def face_corners(d, f, t):
    """3D corners of an element face in texture order: (P00, P10, P01) i.e. at uv
    (u1,v1), (u2,v1), (u1,v2)."""
    x1, y1, z1 = f
    x2, y2, z2 = t
    if d == "up":
        return (x1, y2, z1), (x2, y2, z1), (x1, y2, z2)
    if d == "down":
        return (x1, y1, z2), (x2, y1, z2), (x1, y1, z1)
    if d == "north":
        return (x2, y2, z1), (x1, y2, z1), (x2, y1, z1)
    if d == "south":
        return (x1, y2, z2), (x2, y2, z2), (x1, y1, z2)
    if d == "west":
        return (x1, y2, z1), (x1, y2, z2), (x1, y1, z1)
    if d == "east":
        return (x2, y2, z2), (x2, y2, z1), (x2, y1, z2)


def default_uv(d, f, t):
    x1, y1, z1 = f
    x2, y2, z2 = t
    return {"up": (x1, z1, x2, z2), "down": (x1, 16 - z2, x2, 16 - z1),
            "north": (16 - x2, 16 - y2, 16 - x1, 16 - y1), "south": (x1, 16 - y2, x2, 16 - y1),
            "west": (z1, 16 - y2, z2, 16 - y1), "east": (16 - z2, 16 - y2, 16 - z1, 16 - y1)}[d]


def rotate_dir(d, xr, yr):
    v = DIRV[d]
    p = rot_y(rot_x((v[0] * 8 + 8, v[1] * 8 + 8, v[2] * 8 + 8), xr), yr)
    w = tuple(round((c - 8) / 8) for c in p)
    for k, vv in DIRV.items():
        if vv == w:
            return k
    return d


class View:
    def __init__(self, M, name):
        self.M = np.array(M, float)  # 2x3: screen px per block unit
        self.name = name
        # camera direction = null vector of M, pointing down/into the scene
        _, _, vt = np.linalg.svd(np.vstack([self.M, [0, 0, 0]]))
        cd = vt[-1]
        if cd[1] > 1e-9 or (abs(cd[1]) < 1e-9 and np.dot(cd, self._into()) < 0):
            cd = -cd
        self.cd = cd / np.linalg.norm(cd)
        vis = [d for d, v in DIRV.items() if np.dot(v, self.cd) < -1e-6]
        self.visible = vis
        mx = max(MC_SHADE[d] for d in vis)
        self.shade = {d: min(1.0, MC_SHADE[d] / mx * (0.92 if d != "up" else 1.0)) for d in DIRV}

    def _into(self):
        # for pure elevations, the "into" direction: screen-right x screen-up
        r = self.M[0] / (np.linalg.norm(self.M[0]) + 1e-9)
        u = -self.M[1] / (np.linalg.norm(self.M[1]) + 1e-9)
        return np.cross(u, r)

    def proj(self, p):
        return self.M @ np.asarray(p, float)


def iso_view(A=8, C=4, H=9, corner="sw"):
    # base: camera at south-west, looking north-east
    base = np.array([[A, 0, A], [-C, -H, C]], float)
    R = {"sw": np.eye(3),
         "nw": np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float),   # camera at north-west
         "ne": np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]], float),
         "se": np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]], float)}[corner]
    return View(base @ R, "iso_" + corner)


def elevation_view(side, T=8):
    # side = where the camera stands
    M = {"west": [[0, 0, T], [0, -T, 0]],    # camera west, looking east: screen right = south
         "east": [[0, 0, -T], [0, -T, 0]],
         "south": [[T, 0, 0], [0, -T, 0]],
         "north": [[-T, 0, 0], [0, -T, 0]]}[side]
    v = View(M, "elev_" + side)
    v.cd = -np.array(DIRV[side], float)  # looking towards the opposite side
    v.visible = [side]
    v.shade = {d: 1.0 if d == side else 0.8 for d in DIRV}
    v.shade["up"] = 1.0
    return v


class Renderer:
    def __init__(self, assets, view):
        self.assets = assets
        self.view = view
        self.cache = {}

    def tint_for(self, name):
        if name in ("grass_block", "short_grass", "tall_grass", "fern", "large_fern", "sugar_cane"):
            return GRASS_TINT
        if name.endswith("_leaves") or name == "vine":
            if name in ("cherry_leaves", "azalea_leaves", "flowering_azalea_leaves", "pale_oak_leaves"):
                return None
            return FOLIAGE_TINT.get(name, DEFAULT_FOLIAGE)
        return None

    def sprite(self, state, cullmask):
        """Return (RGBA image, (ox, oy)) for a block state; cullmask = frozenset of
        world directions whose neighbour is an opaque full block."""
        key = (state, cullmask)
        if key in self.cache:
            return self.cache[key]
        name, props = parse_state(state)
        V = self.view
        faces = []  # (depth, image_ops)
        for model_name, xr, yr in self.assets.parts(state):
            textures, elements = self.assets.model(model_name)
            if not elements:
                continue
            for el in elements:
                f, t = el["from"], el["to"]
                ctr = rot_y(rot_x(((f[0] + t[0]) / 2, (f[1] + t[1]) / 2, (f[2] + t[2]) / 2), xr), yr)
                for d, fd in el.get("faces", {}).items():
                    wd = rotate_dir(d, xr, yr)
                    if wd not in V.visible:
                        continue
                    cf = fd.get("cullface")
                    if cf and rotate_dir(cf, xr, yr) in cullmask:
                        continue
                    tex = self.assets.texture(fd.get("texture", ""), textures)
                    if tex is None:
                        continue
                    uv = fd.get("uv") or default_uv(d, f, t)
                    P = [rot_y(rot_x(p, xr), yr) for p in face_corners(d, f, t)]
                    tint = self.tint_for(name) if "tintindex" in fd else None
                    depth = float(np.dot(ctr, V.cd))
                    faces.append((depth, tex, uv, fd.get("rotation", 0), P, V.shade[wd], tint))
        if not faces:
            self.cache[key] = None
            return None
        # sprite canvas: project unit cube corners
        corners = [V.proj((x, y, z)) for x in (0, 1) for y in (0, 1) for z in (0, 1)]
        mn = np.floor(np.min(corners, axis=0)) - 2
        mx = np.ceil(np.max(corners, axis=0)) + 2
        W, Hh = int(mx[0] - mn[0]), int(mx[1] - mn[1])
        canvas = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
        faces.sort(key=lambda r: -r[0])  # far first
        for depth, tex, uv, rot, P, shade, tint in faces:
            img = self._face_image(tex, uv, rot, shade, tint)
            if img is None:
                continue
            S = [V.proj(np.array(p) / 16.0) - mn for p in P]
            self._blit(canvas, img, S)
        res = (canvas, (int(mn[0]), int(mn[1])))
        self.cache[key] = res
        return res

    @staticmethod
    @lru_cache(maxsize=None)
    def _face_cached(tex_id, tex_bytes, size, uv, rot, shade, tint):
        tex = Image.frombytes("RGBA", size, tex_bytes)
        N = tex.width
        u1, v1, u2, v2 = [c * N / 16.0 for c in uv]
        box = (int(round(min(u1, u2))), int(round(min(v1, v2))), int(round(max(u1, u2))), int(round(max(v1, v2))))
        if box[2] <= box[0] or box[3] <= box[1]:
            return None
        img = tex.crop(box)
        if u1 > u2:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if v1 > v2:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        if rot:
            img = img.rotate(-rot, expand=True)
        arr = np.asarray(img).astype(np.float32)
        if tint is not None:
            arr[..., :3] *= np.array(tint, np.float32) / 255.0
        arr[..., :3] *= shade
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    def _face_image(self, tex, uv, rot, shade, tint):
        return self._face_cached(id(tex), tex.tobytes(), tex.size, tuple(uv), rot, round(shade, 3), tint)

    @staticmethod
    def _blit(canvas, img, S):
        S00, S10, S01 = [np.asarray(s, float) for s in S]
        w, h = img.size
        a = (S10 - S00) / w
        b = (S01 - S00) / h
        Mx = np.array([[a[0], b[0]], [a[1], b[1]]])
        if abs(np.linalg.det(Mx)) < 1e-6:
            return
        # grow the parallelogram by ~0.35px on each side to hide seams
        cen = S00 + (S10 - S00) / 2 + (S01 - S00) / 2
        la, lb = np.linalg.norm(S10 - S00), np.linalg.norm(S01 - S00)
        ga = 1 + 0.7 / max(la, 1e-6)
        gb = 1 + 0.7 / max(lb, 1e-6)
        a2, b2 = a * ga, b * gb
        S00g = cen - a2 * w / 2 - b2 * h / 2
        M2 = np.array([[a2[0], b2[0]], [a2[1], b2[1]]])
        inv = np.linalg.inv(M2)
        pts = [S00g, S00g + a2 * w, S00g + b2 * h, S00g + a2 * w + b2 * h]
        x0 = int(math.floor(min(p[0] for p in pts))); y0 = int(math.floor(min(p[1] for p in pts)))
        x1 = int(math.ceil(max(p[0] for p in pts))); y1 = int(math.ceil(max(p[1] for p in pts)))
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, canvas.width), min(y1, canvas.height)
        if x1 <= x0 or y1 <= y0:
            return
        # output (X,Y) relative to (x0,y0) -> input
        c0 = -inv @ (S00g - np.array([x0, y0]))
        data = (inv[0, 0], inv[0, 1], c0[0], inv[1, 0], inv[1, 1], c0[1])
        out = img.transform((x1 - x0, y1 - y0), Image.AFFINE, data, resample=Image.NEAREST)
        canvas.alpha_composite(out, (x0, y0))


def render(model, assets, view, region=None, ymin=-1, bg=(178, 210, 240), ground_state="grass_block"):
    """Render model (optionally restricted to region=(x1,z1,x2,z2) inclusive)."""
    R = Renderer(assets, view)
    m = model
    x1, z1, x2, z2 = region if region else (m.x0, m.z0, m.x1 - 1, m.z1 - 1)
    ya = max(ymin, m.y0)
    sub = m.a[x1 - m.x0:x2 - m.x0 + 1, ya - m.y0:, z1 - m.z0:z2 - m.z0 + 1].copy()
    # palette for rendering: KEEP at ground layer -> grass
    pal = list(m.pal)
    gid = len(pal); pal.append(ground_state + "[snowy=false]")
    air_id = len(pal); pal.append("air")
    ground_layer = -1 - ya
    if 0 <= ground_layer < sub.shape[1]:
        layer = sub[:, ground_layer, :]
        layer[layer == 0] = gid
    sub[sub == 0] = air_id
    if ground_layer > 0:
        sub[:, :ground_layer, :] = air_id  # don't draw below ground
    names = [parse_state(s)[0] for s in pal]
    opaque = np.array([is_full(n, 0) and not any(t in n for t in TRANSPARENT_NAMES)
                       and n not in ("air", "<keep>") for n in names])
    opaque[gid] = True
    isair = np.array([n in ("air", "<keep>") for n in names])

    O = opaque[sub]
    # neighbour opacity in each visible direction
    def shifted(d):
        dx, dy, dz = DIRV[d]
        res = np.zeros_like(O)
        sx = slice(max(dx, 0), O.shape[0] + min(dx, 0)); tx = slice(max(-dx, 0), O.shape[0] + min(-dx, 0))
        sy = slice(max(dy, 0), O.shape[1] + min(dy, 0)); ty = slice(max(-dy, 0), O.shape[1] + min(-dy, 0))
        sz = slice(max(dz, 0), O.shape[2] + min(dz, 0)); tz = slice(max(-dz, 0), O.shape[2] + min(-dz, 0))
        res[tx, ty, tz] = O[sx, sy, sz]
        return res
    vis = view.visible
    nb = {d: shifted(d) for d in vis}
    hidden = np.ones_like(O)
    for d in vis:
        hidden &= nb[d]
    draw = ~isair[sub] & ~(hidden & O)
    xs, ys, zs = np.nonzero(draw)
    wx, wy, wz = xs + x1, ys + ya, zs + z1
    keyd = wx * view.cd[0] + wy * view.cd[1] + wz * view.cd[2]
    order = np.argsort(-keyd, kind="stable")
    # canvas extents
    cx = np.array([x1, x2 + 1]); cy = np.array([ya, ya + sub.shape[1]]); cz = np.array([z1, z2 + 1])
    pts = np.array([view.proj((a, b, c)) for a in cx for b in cy for c in cz])
    mn = np.floor(pts.min(0)) - 4; mx = np.ceil(pts.max(0)) + 4
    W, Hh = int(mx[0] - mn[0]), int(mx[1] - mn[1])
    canvas = Image.new("RGBA", (W, Hh), bg + (255,))
    for i in order:
        xi, yi, zi = xs[i], ys[i], zs[i]
        state = pal[sub[xi, yi, zi]]
        cm = frozenset(d for d in vis if nb[d][xi, yi, zi])
        sp = R.sprite(state, cm)
        if sp is None:
            continue
        img, (ox, oy) = sp
        p = view.proj((wx[i], wy[i], wz[i])) - mn
        canvas.alpha_composite(img, (int(round(p[0])) + ox, int(round(p[1])) + oy))
    return canvas
