"""Build the Sturköskolan world with a real Minecraft 1.21.11 server and install it.

    python3 deploy.py SERVER_DIR [--install SAVES_DIR]

SERVER_DIR must contain server.jar, eula.txt and server.properties (flat world,
RCON enabled). Java must be on PATH (see ../shell.nix).
"""
import argparse
import os
import random
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import make_model, export, render_all, GROUND_Y, BOUNDS, ROOT  # noqa: E402
from rcon import Rcon  # noqa: E402

WORLD_NAME = "Sturköskolan"
FOLDER = "Sturkoskolan"
SPAWN = (-31, GROUND_Y, -14, -62.0, 0.0)     # x y z yaw pitch: looking at the school


def wait_for(path, text, timeout=180):
    t = time.time()
    while time.time() - t < timeout:
        if os.path.exists(path) and text in open(path, errors="replace").read():
            return
        time.sleep(0.5)
    raise TimeoutError(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("server_dir")
    ap.add_argument("--install", default=None)
    args = ap.parse_args()
    sd = os.path.abspath(args.server_dir)
    world = os.path.join(sd, "world")

    m = make_model()
    if os.path.exists(world):
        shutil.rmtree(world)
    export(m, os.path.join(world, "datapacks", "sturko"))

    log = open(os.path.join(sd, "server.log"), "w")
    proc = subprocess.Popen(["java", "-Xmx3G", "-jar", "server.jar", "--nogui"], cwd=sd,
                            stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    try:
        wait_for(os.path.join(sd, "server.log"), "RCON running")
        r = Rcon()
        print(r.cmd("datapack list"))
        x0, x1, z0, z1 = BOUNDS["x0"], BOUNDS["x1"] - 1, BOUNDS["z0"], BOUNDS["z1"] - 1
        print(r.cmd(f"forceload add {x0} {z0} -1 {z1}"))
        print(r.cmd(f"forceload add 0 {z0} {x1} {z1}"))
        for x, z in ((x0, z0), (x1, z1), (x0, z1), (x1, z0)):
            for _ in range(60):
                if "passed" in r.cmd(f"execute if loaded {x} {GROUND_Y} {z}"):
                    break
                time.sleep(0.5)
        fdir = os.path.join(world, "datapacks", "sturko", "data", "sturko", "function")
        for f in sorted(os.listdir(fdir)):
            print(r.cmd(f"function sturko:{f[:-len('.mcfunction')]}"))
        # verify a sample + every support-dependent block
        xs, ys, zs = m.nonkeep()
        idx = list(range(len(xs)))
        random.Random(2).shuffle(idx)
        fragile = ("door", "lantern", "ladder", "bed", "carpet", "chain", "trapdoor", "potted", "rod",
                   "sign", "daylight")
        bad, n = [], 0
        for i in range(len(xs)):
            s = m.get(int(xs[i]), int(ys[i]), int(zs[i]))
            if i in idx[:1500] or any(k in s for k in fragile):
                n += 1
                res = r.cmd(f"execute if block {xs[i]} {ys[i] + GROUND_Y} {zs[i]} minecraft:{s}")
                if "passed" not in res:
                    bad.append((int(xs[i]), int(ys[i]), int(zs[i]), s))
        print(f"verified {n} blocks, {len(bad)} mismatches", bad[:10])
        x, y, z, yaw, pitch = SPAWN
        for c in (f"setworldspawn {x} {y} {z} {yaw} {pitch}", "gamerule respawn_radius 0",
                  "gamerule spawn_monsters false", "time set 1000", "weather clear 120000",
                  "forceload remove all", "save-all flush"):
            print(c, "->", r.cmd(c))
        time.sleep(3)
        r.cmd("stop")
        proc.wait(timeout=120)
    finally:
        if proc.poll() is None:
            proc.kill()
        log.close()

    # ---- tidy the save: name, cheats on, creative, peaceful, no builder datapack
    import nbtlib
    lvl = nbtlib.load(os.path.join(world, "level.dat"))
    d = lvl["Data"]
    d["LevelName"] = nbtlib.String(WORLD_NAME)
    d["allowCommands"] = nbtlib.Byte(1)
    d["GameType"] = nbtlib.Int(1)
    d["Difficulty"] = nbtlib.Byte(0)
    if "DataPacks" in d:
        en = d["DataPacks"]["Enabled"]
        d["DataPacks"]["Enabled"] = nbtlib.List[nbtlib.String]([p for p in en if "sturko" not in str(p)])
    lvl.save()
    shutil.rmtree(os.path.join(world, "datapacks", "sturko"))
    src = os.path.join(ROOT, "renders", "school_sw.png")
    if os.path.exists(src):
        from PIL import Image
        im = Image.open(src)
        w, h = im.size
        im.crop((int(w * 0.30), int(h * 0.30), int(w * 0.78), int(h * 0.78))).resize(
            (64, 64), Image.LANCZOS).save(os.path.join(world, "icon.png"))
    for junk in ("session.lock",):
        p = os.path.join(world, junk)
        if os.path.exists(p):
            os.remove(p)

    stage = os.path.join(sd, FOLDER)
    if os.path.exists(stage):
        shutil.rmtree(stage)
    shutil.copytree(world, stage)
    out_zip = os.path.join(ROOT, FOLDER)
    shutil.make_archive(out_zip, "zip", sd, FOLDER)
    print("zipped", out_zip + ".zip")
    if args.install:
        dest = os.path.join(args.install, FOLDER)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(stage, dest)
        print("installed to", dest)


if __name__ == "__main__":
    main()
