#!/usr/bin/env python3
"""Pack OpenStreetMap traffic-separation schemes for the sea-distance map.

Source: OSM seamark:type = separation_zone, separation_line,
separation_boundary, separation_lane (ways and relations), via Overpass
`out geom`. The live query is below. A saved reply can be passed as the
first argument; otherwise the script downloads it.

Inland waterways mistagged as separation lanes (CEMT class, canal, river)
are dropped. Fairways such as the Kadetrenden stay.

Schemes the extract does not contain are merged from supplements.py.
Those are the US Atlantic and Gulf schemes in 33 CFR 167, plus the
Galveston Entrance Safety Fairway in 33 CFR 166. The regulation's own
coordinates and lane widths are used. Pacific schemes already in the
extract are not repeated. NGA Pub. 157 adds two precautionary outlines
whose corners or radius are printed there; lanes without a vertex list
are left out. COLREG.2/Circ.44 Annex 9 adds the two IMO schemes off
the South African coast, Off Alphard Banks and Off the FA Platform.
Harbour approaches that the circular and NGA Pub. 171 do not give
corners for are left out.

Each scheme is kept as mapped: zone polygons, boundary lines, separation
lines, and lane centrelines. Nothing is offset into a fake width. Two
simpler copies (zoom under 6.5, and 6.5 to 9) sit beside the full geometry
so the map can switch by zoom. Lane arrows follow the way, or
seamark:separation_lane:orientation when that tag is set. The same open
lane, oriented with that rule, is stored once as a routing axis. The chart
does not draw the axis; the arrows already show the direction.

The bytes are data/src/main/resources/sea_tss.bin (little-endian).
"""

from __future__ import annotations

import json
import math
import struct
import sys
import urllib.request
from pathlib import Path

from supplements import pieces as supplement_pieces

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "src" / "main" / "resources" / "sea_tss.bin"
QUERY = """[out:json][timeout:240];
(
  way["seamark:type"="separation_zone"];
  way["seamark:type"="separation_line"];
  way["seamark:type"="separation_boundary"];
  way["seamark:type"="separation_lane"];
  relation["seamark:type"="separation_zone"];
  relation["seamark:type"="separation_line"];
  relation["seamark:type"="separation_boundary"];
  relation["seamark:type"="separation_lane"];
);
out geom;
"""
OVERPASS = "https://overpass.openstreetmap.fr/api/interpreter"
INLAND_WATER = {"canal", "river", "stream", "ditch", "drain"}
# Zoom bands. max zoom is exclusive.
BANDS = ((0, 6.5, 0.025), (6.5, 9, 0.006), (9, 24, 0.0))
ARROW_BANDS = ((6.5, 9, 8.0), (9, 24, 3.0))
ZONE, LANE, BOUND, LINE, ARROW, HOLE, AXIS = 1, 2, 3, 4, 5, 6, 7


def fold(text: str) -> str:
    return (
        text.lower()
        .replace("ø", "o")
        .replace("ö", "o")
        .replace("ä", "a")
        .replace("é", "e")
        .replace("è", "e")
    )


def stable_id(name: str) -> str | None:
    n = fold(name).strip()
    if len(n) < 4:
        return None
    if n in {"tss", "separation zone", "separation line", "westbound lane", "eastbound lane",
             "northbound lane", "southbound lane", "southeasterly lane", "northwesterly lane"}:
        return None
    if "dover" in n:
        return "tss-dover"
    if "casquet" in n:
        return "tss-casquets"
    if "gibraltar" in n:
        return "tss-gibraltar"
    if "in the sound" in n or n.startswith("the sound") or "oresund" in n:
        return "tss-oresund"
    if "ushant" in n or "ouessant" in n:
        return "tss-ushant"
    keys = ("tss", "strait", "traffic", "approaches", "channel", "off ")
    if not any(key in n for key in keys):
        return None
    slug = []
    prev = False
    for ch in n:
        if ch.isascii() and ch.isalnum():
            slug.append(ch)
            prev = False
        elif not prev:
            slug.append("-")
            prev = True
    text = "".join(slug).strip("-")[:42]
    if not text or text in {"tss", "off", "strait"}:
        return None
    return text if text.startswith("tss-") else "tss-" + text


def download(path: Path) -> None:
    request = urllib.request.Request(
        OVERPASS,
        data=QUERY.encode(),
        headers={"User-Agent": "SaliroTSS/1.0"},
    )
    with urllib.request.urlopen(request, timeout=240) as response, path.open("wb") as out:
        out.write(response.read())


def coords_of(element: dict) -> list[list[dict]]:
    """One or more lines. Relations yield one line per member that has geometry."""
    if element["type"] == "way":
        geom = element.get("geometry") or []
        return [geom] if len(geom) >= 2 else []
    lines = []
    for member in element.get("members") or []:
        geom = member.get("geometry") or []
        if len(geom) >= 2:
            role = member.get("role") or "outer"
            lines.append((role, geom))
    return lines


def ring(geom: list[dict]) -> list[tuple[float, float]]:
    pts = [(p["lat"], p["lon"]) for p in geom]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return pts


def is_closed(geom: list[dict], tol: float = 0.0015) -> bool:
    if len(geom) < 4:
        return False
    return math.hypot(geom[0]["lat"] - geom[-1]["lat"], geom[0]["lon"] - geom[-1]["lon"]) <= tol


def bbox(pts: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    lats = [p[0] for p in pts]
    lngs = [p[1] for p in lngs_of(pts)]
    return min(lats), max(lats), min(lngs), max(lngs)


def lngs_of(pts: list[tuple[float, float]]) -> list[float]:
    return [p[1] for p in pts]


def expand(box: tuple[float, float, float, float], pad: float) -> tuple[float, float, float, float]:
    return box[0] - pad, box[1] + pad, box[2] - pad, box[3] + pad


def overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a[1] >= b[0] and b[1] >= a[0] and a[3] >= b[2] and b[3] >= a[2]


def centroid(pts: list[tuple[float, float]]) -> tuple[float, float]:
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def simplify(points: list[tuple[float, float]], eps: float) -> list[tuple[float, float]]:
    """Short chart rings stay exact. Only long outlines shed points when zoomed out."""
    if eps <= 0 or len(points) < 24:
        return points
    return dp(points, eps)


def dp(points: list[tuple[float, float]], eps: float) -> list[tuple[float, float]]:
    if eps <= 0 or len(points) < 3:
        return points
    closed = points[0] == points[-1] and len(points) >= 4
    body = points[:-1] if closed else points

    def rec(start: int, end: int, keep: list[bool]) -> None:
        if end <= start + 1:
            return
        ax, ay = body[start]
        bx, by = body[end]
        dx, dy = bx - ax, by - ay
        span = dx * dx + dy * dy
        best = -1.0
        at = -1
        for index in range(start + 1, end):
            px, py = body[index]
            if span == 0:
                dist = math.hypot(px - ax, py - ay)
            else:
                t = ((px - ax) * dx + (py - ay) * dy) / span
                t = max(0.0, min(1.0, t))
                dist = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
            if dist > best:
                best = dist
                at = index
        if best > eps and at >= 0:
            keep[at] = True
            rec(start, at, keep)
            rec(at, end, keep)

    keep = [False] * len(body)
    keep[0] = keep[-1] = True
    rec(0, len(body) - 1, keep)
    out = [body[i] for i, on in enumerate(keep) if on]
    if closed:
        if len(out) < 4:
            return points
        out.append(out[0])
    return out if len(out) >= 2 else points


def nm(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 3440.065 * math.asin(min(1.0, math.sqrt(h)))


def bearing(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlon = math.radians(b[1] - a[1])
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return math.degrees(math.atan2(y, x)) % 360.0


def arrows_along(pts: list[tuple[float, float]], step: float, forced: float | None) -> list[tuple[tuple[float, float], float]]:
    if len(pts) < 2:
        return []
    total = 0.0
    spans = []
    for start, end in zip(pts, pts[1:]):
        length = nm(start, end)
        spans.append((start, end, length, bearing(start, end)))
        total += length
    if total < 0.15:
        return []
    if total < step:
        marks = [total / 2.0]
    else:
        marks = []
        at = step / 2.0
        while at < total:
            marks.append(at)
            at += step
    out = []
    for mark in marks:
        walked = 0.0
        for start, end, length, seg_bearing in spans:
            if length < 1e-6:
                continue
            if walked + length + 1e-6 >= mark:
                frac = (mark - walked) / length
                frac = max(0.0, min(1.0, frac))
                point = (start[0] + (end[0] - start[0]) * frac, start[1] + (end[1] - start[1]) * frac)
                out.append((point, forced if forced is not None else seg_bearing))
                break
            walked += length
    return out


def orientation_of(tags: dict) -> float | None:
    raw = tags.get("seamark:separation_lane:orientation") or tags.get("seamark:orientation")
    if raw is None:
        return None
    try:
        value = float(str(raw).split(";")[0].strip())
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    return value % 360.0


def keep(tags: dict) -> bool:
    if tags.get("CEMT"):
        return False
    if tags.get("highway"):
        return False
    water = tags.get("waterway")
    return water not in INLAND_WATER


def load_elements(path: Path) -> tuple[list[dict], str]:
    data = json.loads(path.read_text())
    stamp = (data.get("osm3s") or {}).get("timestamp_osm_base") or ""
    return data["elements"], stamp


def pieces_of(element: dict) -> list[dict]:
    tags = element.get("tags") or {}
    kind = tags.get("seamark:type")
    name = (tags.get("seamark:name") or tags.get("name") or "").strip()
    orient = orientation_of(tags)
    osm = f"{element['type'][0]}{element['id']}"
    found = []
    if element["type"] == "way":
        geom = element.get("geometry") or []
        if len(geom) < 2:
            return []
        pts = [(p["lat"], p["lon"]) for p in geom]
        closed = is_closed(geom)
        found.append({"kind": kind, "name": name, "orient": orient, "osm": osm, "pts": pts, "closed": closed, "role": "outer"})
        return found
    for member in element.get("members") or []:
        geom = member.get("geometry") or []
        if len(geom) < 2:
            continue
        pts = [(p["lat"], p["lon"]) for p in geom]
        role = member.get("role") or "outer"
        closed = is_closed(geom) or role in {"outer", "inner"}
        found.append({"kind": kind, "name": name, "orient": orient, "osm": osm, "pts": pts, "closed": closed, "role": role})
    return found


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/tss_osm.json")
    if not source.exists():
        download(source)
    elements, stamp = load_elements(source)
    raw = []
    dropped = 0
    for element in elements:
        tags = element.get("tags") or {}
        if not keep(tags):
            dropped += 1
            continue
        raw.extend(pieces_of(element))
    features = []
    for piece in raw:
        pts = piece["pts"]
        if any(abs(pts[i][1] - pts[i + 1][1]) > 180 for i in range(len(pts) - 1)):
            continue
        box = (min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts))
        if box[3] - box[2] > 30 or box[1] - box[0] > 20:
            continue
        piece = dict(piece)
        piece["box"] = box
        piece["center"] = centroid(pts)
        piece["sid"] = stable_id(piece["name"])
        features.append(piece)

    # Supplements are complete published figures. They must not absorb a
    # nearby extract fragment, or a small Chinese scheme would be renamed
    # as the Qingdao precautionary area.
    osm_count = len(features)
    for piece in supplement_pieces():
        pts = piece["pts"]
        if any(abs(pts[i][1] - pts[i + 1][1]) > 180 for i in range(len(pts) - 1)):
            raise SystemExit(f"supplement crosses the dateline: {piece['sid']}")
        box = (min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts))
        if box[3] - box[2] > 30 or box[1] - box[0] > 20:
            raise SystemExit(f"supplement spans too far: {piece['sid']} {piece.get('part')}")
        piece = dict(piece)
        piece["box"] = box
        piece["center"] = centroid(pts)
        features.append(piece)

    parent = list(range(len(features)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_sid: dict[str, list[int]] = {}
    for index, feature in enumerate(features):
        if feature["sid"]:
            by_sid.setdefault(feature["sid"], []).append(index)
    for indexes in by_sid.values():
        for other in indexes[1:]:
            union(indexes[0], other)

    named = [i for i, feature in enumerate(features) if feature["sid"] and i < osm_count]
    for index, feature in enumerate(features):
        if index >= osm_count or feature["sid"]:
            continue
        best = None
        best_d = 1e9
        box = expand(feature["box"], 0.28)
        for other in named:
            if not overlaps(box, features[other]["box"]):
                continue
            dlat = feature["center"][0] - features[other]["center"][0]
            dlng = feature["center"][1] - features[other]["center"][1]
            dist = dlat * dlat + dlng * dlng
            if dist < best_d:
                best_d = dist
                best = other
        if best is not None:
            union(index, best)

    loose = [i for i, feature in enumerate(features) if not feature["sid"] and find(i) == i]
    for left in range(len(loose)):
        for right in range(left + 1, len(loose)):
            a, b = loose[left], loose[right]
            if overlaps(expand(features[a]["box"], 0.08), features[b]["box"]):
                union(a, b)

    groups: dict[int, list[int]] = {}
    for index in range(len(features)):
        groups.setdefault(find(index), []).append(index)

    schemes = []
    for indexes in groups.values():
        sids = [features[i]["sid"] for i in indexes if features[i]["sid"]]
        sid = sids[0] if sids else None
        names = [features[i]["name"] for i in indexes if features[i]["name"]]
        name = max(names, key=len) if names else ""
        if sid is None:
            osm_ids = sorted(features[i]["osm"] for i in indexes)
            sid = "tss-" + osm_ids[0]
        schemes.append({"id": sid[:48], "name": name[:80], "members": indexes})

    # A stable id must not be split. Merge scheme rows that share an id.
    merged: dict[str, dict] = {}
    for scheme in schemes:
        row = merged.get(scheme["id"])
        if row is None:
            merged[scheme["id"]] = scheme
        else:
            row["members"].extend(scheme["members"])
            if len(scheme["name"]) > len(row["name"]):
                row["name"] = scheme["name"]
    schemes = list(merged.values())
    schemes.sort(key=lambda row: row["id"])

    records = []
    seen_axes: set[tuple] = set()
    for scheme_index, scheme in enumerate(schemes):
        polygons: dict[str, dict] = {}
        for member in scheme["members"]:
            feature = features[member]
            kind = feature["kind"]
            pts = feature["pts"]
            closed = feature["closed"] or kind == "separation_zone"
            if kind in {"separation_zone", "separation_lane"} and closed:
                bucket = polygons.setdefault(feature["osm"], {"kind": LANE if kind == "separation_lane" else ZONE, "outers": [], "holes": [], "orient": feature["orient"], "pts": pts})
                (bucket["holes"] if feature["role"] == "inner" else bucket["outers"]).append(pts)
                continue
            if kind == "separation_lane":
                emit_axis(records, seen_axes, scheme_index, pts, feature["orient"])
                for min_z, max_z, step in ARROW_BANDS:
                    for point, deg in arrows_along(pts, step, feature["orient"]):
                        records.append((scheme_index, ARROW, min_z, max_z, int(round(deg * 10)), [[point]]))
                continue
            draw_kind = LINE if kind == "separation_line" else BOUND
            emit_lods(records, scheme_index, draw_kind, [pts], closed=False)
        for bucket in polygons.values():
            outers = bucket["outers"] or [bucket["pts"]]
            for outer in outers:
                holes = [hole for hole in bucket["holes"] if overlaps(bbox_of(hole), bbox_of(outer))]
                rings = [close_ring(outer)]
                for hole in holes:
                    closed_hole = close_ring(hole)
                    if len(closed_hole) >= 4:
                        rings.append(closed_hole)
                emit_lods(records, scheme_index, bucket["kind"], rings, closed=True)
            if bucket["kind"] == LANE and bucket["orient"] is not None:
                axis = transect(close_ring(outers[0]), bucket["orient"])
                for min_z, max_z, step in ARROW_BANDS:
                    for point, deg in arrows_along(axis, step, bucket["orient"]):
                        records.append((scheme_index, ARROW, min_z, max_z, int(round(deg * 10)), [[point]]))

    blob = bytearray()
    blob += b"TSS1"
    blob += struct.pack("<HH", 1, len(schemes))
    for scheme in schemes:
        ident = scheme["id"].encode()
        name = scheme["name"].encode()
        blob += struct.pack("<B", len(ident))
        blob += ident
        blob += struct.pack("<B", min(255, len(name)))
        blob += name[:255]
    blob += struct.pack("<I", len(records))
    for scheme_index, kind, min_z, max_z, bearing, rings in records:
        blob += struct.pack("<HBBBhH", scheme_index, kind, int(round(min_z * 2)), int(round(max_z * 2)), bearing, len(rings))
        for pts in rings:
            blob += struct.pack("<H", len(pts))
            for lat, lng in pts:
                blob += struct.pack("<ff", lat, lng)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(blob)
    print(f"wrote {OUT} bytes={len(blob)} schemes={len(schemes)} features={len(features)} records={len(records)} dropped_inland={dropped} stamp={stamp}")
    wanted = {
        "dover": (51.2, 1.5),
        "gibraltar": (35.95, -5.6),
        "oresund": (55.7, 12.7),
        "casquets": (49.7, -2.4),
        "singapore": (1.2, 103.8),
        "hormuz": (26.5, 56.5),
        "malacca": (2.5, 101.5),
        "tokyo": (35.1, 139.8),
        "newyork": (40.4, -73.7),
        "galveston": (29.22, -94.52),
        "boston": (42.2, -70.5),
        "chesapeake": (36.9, -75.8),
        "suez": (29.9, 32.55),
        "panama": (8.9, -79.6),
    }
    for label, (lat, lng) in wanted.items():
        hit = nearest_scheme(schemes, features, lat, lng)
        print(f"  {label}: {hit}")


def emit_axis(records: list, seen: set[tuple], scheme_index: int, pts: list[tuple[float, float]], orient: float | None) -> None:
    """One open-lane centreline, point order matching the traffic direction."""
    if len(pts) < 2:
        return
    aligned = pts
    if orient is not None:
        deg = axis_bearing(pts)
        diff = abs((orient - deg + 180.0) % 360.0 - 180.0)
        if diff > 90.0:
            aligned = list(reversed(pts))
    simplified = dp(aligned, 0.004) if len(aligned) >= 3 else aligned
    if len(simplified) < 2:
        return
    key = tuple((round(lat, 4), round(lng, 4)) for lat, lng in simplified)
    if key in seen:
        return
    seen.add(key)
    deg = axis_bearing(simplified)
    bearing = int(round(deg * 10.0)) % 3600
    records.append((scheme_index, AXIS, 0.0, 24.0, bearing, [simplified]))


def axis_bearing(pts: list[tuple[float, float]]) -> float:
    east = 0.0
    north = 0.0
    for start, end in zip(pts, pts[1:]):
        length = nm(start, end)
        if length < 1e-6:
            continue
        rad = math.radians(bearing(start, end))
        east += math.sin(rad) * length
        north += math.cos(rad) * length
    if abs(east) < 1e-9 and abs(north) < 1e-9:
        return bearing(pts[0], pts[-1])
    return math.degrees(math.atan2(east, north)) % 360.0


def emit_lods(records: list, scheme_index: int, kind: int, rings: list[list[tuple[float, float]]], closed: bool) -> None:
    """One record per zoom band, skipped when simplification changes nothing."""
    bands = []
    for min_z, max_z, eps in BANDS:
        simplified = []
        for ring in rings:
            nxt = simplify(ring, eps)
            if closed:
                nxt = close_ring(nxt)
                if len(nxt) < 4:
                    nxt = close_ring(ring)
            elif len(nxt) < 2:
                nxt = ring
            simplified.append(nxt)
        bands.append((min_z, max_z, simplified, sum(len(r) for r in simplified)))
    folded = []
    for min_z, max_z, simplified, count in bands:
        if folded and folded[-1][3] == count and folded[-1][2] == simplified:
            prev = folded[-1]
            folded[-1] = (prev[0], max_z, prev[2], prev[3])
        else:
            folded.append((min_z, max_z, simplified, count))
    for min_z, max_z, simplified, _count in folded:
        records.append((scheme_index, kind, min_z, max_z, 0, simplified))


def close_ring(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(pts) < 3:
        return pts
    if pts[0] == pts[-1]:
        return pts
    return pts + [pts[0]]


def bbox_of(pts: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    return (
        min(p[0] for p in pts),
        max(p[0] for p in pts),
        min(p[1] for p in pts),
        max(p[1] for p in pts),
    )


def transect(pts: list[tuple[float, float]], deg: float) -> list[tuple[float, float]]:
    """A chord through the centroid along [deg], clipped to the ring by sampling."""
    center = centroid(pts)
    step = 0.01
    rad = math.radians(deg)
    north, east = math.cos(rad), math.sin(rad)
    scale = max(0.2, math.cos(math.radians(center[0])))
    inside = []
    for mile in range(-80, 81):
        lat = center[0] + mile * step * north
        lng = center[1] + mile * step * east / scale
        if contains(pts, lat, lng):
            inside.append((lat, lng))
        elif inside:
            break
    # walk the other way too if we started inside the middle
    if inside and inside[0] != (center[0], center[1]):
        pass
    return inside


def contains(ring: list[tuple[float, float]], lat: float, lng: float) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        yi, xi = ring[i]
        yj, xj = ring[j]
        if ((xi > lng) != (xj > lng)) and (lat < (yi - yj) * (lng - xj) / (xi - xj + 1e-15) + yj):
            inside = not inside
        j = i
    return inside


def nearest_scheme(schemes, features, lat: float, lng: float) -> str:
    best = None
    best_d = 1e9
    for scheme in schemes:
        for member in scheme["members"]:
            c = features[member]["center"]
            dist = (c[0] - lat) ** 2 + (c[1] - lng) ** 2
            if dist < best_d:
                best_d = dist
                best = scheme
    if best is None:
        return "none"
    return f"{best['id']} {best['name']!r} d={best_d ** 0.5:.3f}"


if __name__ == "__main__":
    main()
