# orOS models: mockups/make.py
# Builds the cloth models of orOS Mockups (koulaxizis/oros, mockups/goods/
# cloth3d.js) with Blender's Python module, from nothing but this script:
# no scans, no downloaded meshes, so every file is our own work under CC0.
#
#   pip install bpy==5.2.3        (Blender 5.2.3 LTS as a Python module)
#   python mockups/make.py        (writes mockups/*.glb and mockups/index.json)
#
# Each garment is laid flat: its outline (mm, front view, y up) is filled,
# given a thickness, voxel-remeshed and smoothed into a soft "pillow", puffed
# away from its edges and given a few low folds. Every number that shapes a
# model is in this file and the noise is seeded, so a run gives the same files.
# A GLB holds named meshes with POSITION and NORMAL (metres) and indices, no
# materials or textures: orOS colours them and lays the print on from the
# front (its print areas are in index.json, in mm, origin at the centre).
import bpy, bmesh, math, json, hashlib, os, struct, random
from mathutils import Vector

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)))
VERSION = 1


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mirror_half(half):
    """Right half from the top middle clockwise to the bottom middle -> whole outline."""
    left = [(-x, y) for (x, y) in reversed(half[1:-1])]
    return half + left


def ellipse(cx, cy, rx, ry, a0, a1, n):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def dist_to_poly(p, poly):
    best = 1e9
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ax, ay, bx, by = a[0], a[1], b[0], b[1]
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy or 1
        t = max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
        qx, qy = ax + t * dx, ay + t * dy
        best = min(best, math.hypot(p[0] - qx, p[1] - qy))
    return best


class Folds:
    """A seeded sum of soft waves: low folds across the cloth."""
    def __init__(self, seed, n, amp, wl):
        r = random.Random(seed)
        self.w = []
        for _ in range(n):
            a = r.uniform(0, math.pi)
            self.w.append((math.cos(a), math.sin(a), 2 * math.pi / r.uniform(wl * 0.6, wl * 1.4), r.uniform(0, 6.283), amp * r.uniform(0.4, 1)))

    def __call__(self, x, y):
        return sum(a * math.sin((dx * x + dy * y) * k + ph) for (dx, dy, k, ph, a) in self.w)


def pillow(name, poly, thick=18.0, voxel=4.0, puff=7.0, puff_in=70.0, folds=None, smooth=12):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, -thick / 2)) for (x, y) in poly]
    f = bm.faces.new(vs)
    ex = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in ex["geom"] if isinstance(e, bmesh.types.BMVert)]:
        v.co.z += thick
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    m = ob.modifiers.new("remesh", "REMESH")
    m.mode = "VOXEL"; m.voxel_size = voxel; m.adaptivity = 0
    s = ob.modifiers.new("smooth", "SMOOTH")
    s.factor = 0.8; s.iterations = smooth
    bpy.ops.object.modifier_apply(modifier="remesh")
    bpy.ops.object.modifier_apply(modifier="smooth")
    # puff away from the edges, folds on both faces (more on top)
    for v in ob.data.vertices:
        x, y, z = v.co
        d = dist_to_poly((x, y), poly)
        k = min(1.0, d / puff_in)
        k = k * k * (3 - 2 * k)
        side = 1 if z >= 0 else -1
        v.co.z = z * 0.55 + side * puff * k
        if folds:
            v.co.z += folds(x, y) * (0.6 + 0.4 * k) * (1 if side > 0 else 0.5)
    return ob


def tube(name, pts, r, closed=True, flat=0.55):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, (x, y, z) in enumerate(pts):
        sp.points[i].co = (x, y, z, 1)
    sp.use_cyclic_u = closed
    cu.bevel_depth = r
    cu.bevel_resolution = 3
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    ob = bpy.context.view_layer.objects.active
    for v in ob.data.vertices:
        v.co.z *= flat
    return ob


def strap(name, pts, w, t):
    """A flat strap (handle) of width w along pts (x, y, z)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rows = []
    for i, p in enumerate(pts):
        a = pts[max(0, i - 1)]; b = pts[min(len(pts) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        row = []
        for sx in (-1, 1):
            for sz in (-1, 1):
                row.append(bm.verts.new((p[0] + nx * w / 2 * sx, p[1] + ny * w / 2 * sx, p[2] + sz * t / 2)))
        rows.append(row)
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        for (p, q) in ((0, 1), (1, 3), (3, 2), (2, 0)):
            bm.faces.new((a[p], a[q], b[q], b[p]))
    bm.faces.new((rows[0][0], rows[0][2], rows[0][3], rows[0][1]))
    bm.faces.new((rows[-1][0], rows[-1][1], rows[-1][3], rows[-1][2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def decimate(ob, ratio):
    bpy.context.view_layer.objects.active = ob
    m = ob.modifiers.new("dec", "DECIMATE")
    m.ratio = ratio
    bpy.ops.object.modifier_apply(modifier="dec")


def mesh_arrays(ob):
    """Triangles, smooth normals, positions in metres (rounded: same file every run)."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    pos, nor = [], []
    for v in me.vertices:
        pos.extend(round(c / 1000.0, 6) for c in v.co)
        nor.extend(round(c, 4) for c in v.normal)
    idx = []
    for t in me.loop_triangles:
        idx.extend(t.vertices)
    return pos, nor, idx


def write_glb(path, objs):
    """A plain GLB: one mesh per object, POSITION + NORMAL + uint32 indices."""
    bin_ = bytearray()
    views, accs, meshes, nodes = [], [], [], []

    def add(data, fmt, target, comp, typ, count, mn=None, mx=None):
        while len(bin_) % 4:
            bin_.append(0)
        off = len(bin_)
        bin_.extend(struct.pack("<%d%s" % (len(data), fmt), *data))
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(bin_) - off, "target": target})
        a = {"bufferView": len(views) - 1, "componentType": comp, "count": count, "type": typ}
        if mn is not None:
            a["min"] = mn; a["max"] = mx
        accs.append(a)
        return len(accs) - 1

    for name, ob in objs:
        pos, nor, idx = mesh_arrays(ob)
        n = len(pos) // 3
        mn = [min(pos[i::3]) for i in range(3)]; mx = [max(pos[i::3]) for i in range(3)]
        ap = add(pos, "f", 34962, 5126, "VEC3", n, mn, mx)
        an = add(nor, "f", 34962, 5126, "VEC3", n)
        ai = add(idx, "I", 34963, 5125, "SCALAR", len(idx))
        meshes.append({"name": name, "primitives": [{"attributes": {"POSITION": ap, "NORMAL": an}, "indices": ai}]})
        nodes.append({"name": name, "mesh": len(meshes) - 1})
    while len(bin_) % 4:
        bin_.append(0)
    js = {"asset": {"version": "2.0", "generator": "orOS Mockups make.py v%d (bpy %s)" % (VERSION, bpy.app.version_string), "copyright": "CC0 1.0"},
          "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes, "meshes": meshes,
          "accessors": accs, "bufferViews": views, "buffers": [{"byteLength": len(bin_)}]}
    j = json.dumps(js, separators=(",", ":"), sort_keys=True).encode()
    while len(j) % 4:
        j += b" "
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(j) + 8 + len(bin_))
    out += struct.pack("<II", len(j), 0x4E4F534A) + j + struct.pack("<II", len(bin_), 0x004E4942) + bytes(bin_)
    with open(path, "wb") as fh:
        fh.write(out)
    return out


# ---------- The models ----------
def tshirt():
    reset()
    neck = ellipse(0, 360, 95, 75, -math.pi / 2, 0, 10)          # front neck, middle to the shoulder
    half = neck + [(232, 332), (398, 214), (312, 96), (262, 150), (262, -300), (258, -352), (230, -362), (0, -364)]
    poly = mirror_half(half)
    body = pillow("shirt", poly, thick=20, voxel=4, puff=8, folds=Folds(7, 9, 2.2, 260))
    ring = [(95 * math.sin(a), 360 - 75 * math.cos(a) if math.cos(a) > 0 else 360 - 22 * math.cos(a), 7) for a in [i / 48 * 2 * math.pi - math.pi / 2 for i in range(48)]]
    collar = tube("collar", ring, 7.5, True, 0.7)
    decimate(body, 0.35)
    return [("shirt", body), ("collar", collar)], {
        "shirt": {"w": 796, "h": 726, "print": {"front": {"x": -150, "y": 250, "w": 300, "h": 400}, "chest": {"x": 60, "y": 250, "w": 95, "h": 95}}}}


def tote():
    reset()
    W, H, r = 380, 420, 6
    poly = []
    for (cx, cy, a0) in ((W / 2 - r, H / 2 - r, 0), (-W / 2 + r, H / 2 - r, math.pi / 2), (-W / 2 + r, -H / 2 + r, math.pi), (W / 2 - r, -H / 2 + r, 1.5 * math.pi)):
        poly += ellipse(cx, cy, r, r, a0, a0 + math.pi / 2, 4)
    body = pillow("bag", poly, thick=10, voxel=3.5, puff=1.5, puff_in=130, folds=Folds(11, 7, 2.0, 220), smooth=8)
    decimate(body, 0.4)
    objs = [("bag", body)]
    for nm, rise in (("long", 300), ("short", 150)):
        for k, (dx, dz) in enumerate(((0, 6.5), (10, 4.5))):
            pts = []
            for i in range(25):
                t = i / 24
                x = -85 + 170 * t + dx
                y = H / 2 - 30 + rise * math.sin(math.pi * t) ** 0.9
                pts.append((x, y, dz))
            objs.append(("handle_%s_%d" % (nm, k), strap("handle_%s_%d" % (nm, k), pts, 25, 2.4)))
    return objs, {"bag": {"w": W, "h": H, "print": {"front": {"x": -140, "y": 150, "w": 280, "h": 300}}}}


def hoodie():
    reset()
    neck = ellipse(0, 372, 100, 62, -math.pi / 2, 0, 10)
    half = neck + [(250, 332), (470, -250), (388, -300), (286, 110), (286, -330), (280, -398), (250, -406), (0, -408)]
    poly = mirror_half(half)
    body = pillow("hoodie", poly, thick=26, voxel=4, puff=9, folds=Folds(5, 9, 2.6, 240))
    hood_poly = ellipse(0, 400, 175, 140, 0, 2 * math.pi, 40)[:-1]
    hood = pillow("hood", hood_poly, thick=16, voxel=4, puff=5, puff_in=50, folds=Folds(9, 5, 1.5, 160))
    for v in hood.data.vertices:
        v.co.z -= 12
    pk = [(-150, -40), (150, -40), (196, -300), (-196, -300)]
    pocket = pillow("pocket", pk, thick=4, voxel=3, puff=1.5, puff_in=40, folds=None, smooth=6)
    for v in pocket.data.vertices:
        v.co.z += 17
    strings = []
    for k, sx in enumerate((-1, 1)):
        pts = [(sx * (38 + 4 * t), 312 - 140 * t, 16 + 2 * math.sin(t * 3)) for t in [i / 14 for i in range(15)]]
        strings.append(("string_%d" % k, tube("string_%d" % k, pts, 3, False, 0.8)))
    decimate(body, 0.35); decimate(hood, 0.5); decimate(pocket, 0.5)
    return [("hoodie", body), ("hood", hood), ("pocket", pocket)] + strings, {
        "hoodie": {"w": 940, "h": 780, "print": {"front": {"x": -140, "y": 235, "w": 280, "h": 250}, "chest": {"x": 60, "y": 250, "w": 95, "h": 95},
                                                  "back": {"x": -150, "y": 280, "w": 300, "h": 400}}}}


def socks():
    reset()
    def one(ox, oy):
        leg_l, leg_r, top, heel = -47, 47, 250, -40
        pts = [(leg_l, top), (leg_r, top), (leg_r, heel + 40)]
        pts += [(leg_r + 20, heel + 20), (150, heel + 10)]
        pts += ellipse(160, heel - 38, 48, 48, math.pi / 2, -math.pi / 2, 8)[1:]
        pts += [(60, heel - 86)]
        pts += ellipse(10, heel - 30, 57, 56, -math.pi / 2, -math.pi, 6)[1:]
        return [(x + ox, y + oy) for (x, y) in pts]
    objs = []
    for k, (ox, oy) in enumerate(((-75, 20), (75, -20))):
        ob = pillow("sock_%d" % k, one(ox, oy), thick=12, voxel=3, puff=4, puff_in=30, folds=Folds(13 + k, 6, 1.4, 120), smooth=8)
        for v in ob.data.vertices:
            v.co.z += 3 * k
        decimate(ob, 0.5)
        objs.append(("sock_%d" % k, ob))
    return objs, {"sock_0": {"w": 95, "h": 380, "print": {"front": {"x": -120, "y": 260, "w": 90, "h": 250}}},
                  "sock_1": {"w": 95, "h": 380, "print": {"front": {"x": 30, "y": 220, "w": 90, "h": 250}}}}


MODELS = {"tshirt": tshirt, "tote": tote, "hoodie": hoodie, "socks": socks}

if __name__ == "__main__":
    index = {"version": VERSION, "units": "mm", "models": {}}
    for name, fn in MODELS.items():
        objs, meta = fn()
        data = write_glb(os.path.join(OUT, name + ".glb"), objs)
        index["models"][name] = {"file": name + ".glb", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                                 "meshes": [n for n, _ in objs], "parts": meta}
        print(name, len(data), index["models"][name]["sha256"])
    with open(os.path.join(OUT, "index.json"), "w") as fh:
        json.dump(index, fh, indent=1, sort_keys=True)
        fh.write("\n")
