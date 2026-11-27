#!/usr/bin/env python3
"""Schemes the OSM seamark extract does not contain.

The August 2026 Overpass extract has no separation geometry on the US
Atlantic coast or in the Gulf of Mexico. 33 CFR Part 167 Subpart B
publishes those schemes (coordinates and lane widths) and is public
domain. Part 166 publishes the Galveston Entrance Safety Fairway the
same way. Widths below are the widths the regulation states, not a guess.

Pacific schemes in the same part (San Francisco, Santa Barbara, Los
Angeles, Puget Sound, Prince William Sound) are already in the extract
and are not repeated here.

Precautionary areas are dashed outlines. They are not separation zones,
so the router does not treat them as obstacles. The fairway is the same:
two limit lines, no centreline, because traffic in it runs both ways.

NGA Sailing Directions (Enroute), 2026, are US government works
(no copyright claimed under 17 U.S.C.) and are kept under
docs/reference/nga/. They name many schemes and then say the limits
are best seen on the chart. A scheme is drawn here only when the
volume prints the corners or a centre and a radius. A direction, a
reporting point, or a single pilot position is not a polygon.

South Africa's two IMO schemes are drawn below from COLREG.2/Circ.44
(May 1998) Annex 9, adopted by MSC 69 under resolution A.858(20)
and implemented on 1 December 1998. The annex prints the corners.
Pub. 171 does not: §1.14 only places Alphard Banks at 35°02'S,
20°51'E and repeats the 6-mile avoidance, and §1.16 only places
Platform FA 40.5 miles SSE of Kanonpunt. That 6-mile circle is the
area to be avoided MSC 70 abolished (it cut about 2 miles into the
northern lane) and is not drawn. The positions in the annex are
Cape Datum (Clarke 1880 modified), as the annex says for the SAN
charts, and are shifted onto this WGS 84 chart with the DMA
geocentric translation EPSG:1128. The USCG NAVCEN circular index
skips Circ.44 (Circ.43, then Circ.48); the text used here is the
Swedish Transport Agency's public copy of the IMO circular.

The port approaches are still not drawn. Pub. 171 §2.3 says the
Port Elizabeth scheme is shown on the chart; the positions in that
section are the pilot (33°55.6'S, 25°40.9'E) and VTS reporting
points, not lane corners. Durban (§2.23) has vessel traffic
services and no scheme. Table Bay, Cape Point, Saldanha Bay and
Richards Bay are not given corners. None of those harbours is in
COLREG.2/Circ.44 or a later circular in that public set, and a
polygon placed on the Cape route without those vertices can seal
the route.

Pub. 175 §2.68 (printed page 45) and §5.1 (printed page 113) likewise
leave the Darwin scheme and the south-west Australia scheme to the
chart. The Cape Leeuwin scheme is already in the OpenStreetMap
extract. The area to be avoided off North West Cape (§4.63 and §5.2)
is described as a band 3 to 12 miles offshore, with no corner list.

Pub. 173 describes the Mumbai approaches and the Nine Degree Channel
without corners. The Mumbai scheme is already in the extract.

Pub. 157 prints two closed figures, both precautionary areas rather
than lanes, and those two are drawn below. The lanes of Chengshan
Jiao (§4.46), Qingdao (§5.16), and the Korean and Chinese schemes
that are only "best seen on the chart" are not invented from an
entry point and a bearing.
"""

from __future__ import annotations

import math

# kind strings the packer already understands
ZONE = "separation_zone"
LANE = "separation_lane"
BOUND = "separation_boundary"
LINE = "separation_line"


def dm(deg: float, minutes: float, hemi: str) -> float:
    value = deg + minutes / 60.0
    return -value if hemi in {"S", "W"} else value


def dms(deg: float, minutes: float, seconds: float, hemi: str) -> float:
    return dm(deg, minutes + seconds / 60.0, hemi)


def p(lat_deg: float, lat_min: float, lng_deg: float, lng_min: float) -> tuple[float, float]:
    return (dm(lat_deg, lat_min, "N"), dm(lng_deg, lng_min, "W"))


def ne_dm(lat_deg: float, lat_min: float, lng_deg: float, lng_min: float) -> tuple[float, float]:
    return (dm(lat_deg, lat_min, "N"), dm(lng_deg, lng_min, "E"))


def ne_dms(
    lat_d: float, lat_m: float, lat_s: float, lng_d: float, lng_m: float, lng_s: float,
) -> tuple[float, float]:
    return (dms(lat_d, lat_m, lat_s, "N"), dms(lng_d, lng_m, lng_s, "E"))


# Clarke 1880 (Arc), EPSG:7013. Cape Datum, EPSG:4222.
_CAPE_A = 6378249.145
_CAPE_F = 1.0 / 293.4663077
_WGS_A = 6378137.0
_WGS_F = 1.0 / 298.257223563
# EPSG:1128 Cape to WGS 84 (1), DMA. Added to Cape geocentric coordinates.
_CAPE_TO_WGS = (-136.0, -108.0, -292.0)


def _ecef(lat: float, lng: float, a: float, f: float) -> tuple[float, float, float]:
    lat_r, lng_r = math.radians(lat), math.radians(lng)
    e2 = f * (2.0 - f)
    n = a / math.sqrt(1.0 - e2 * math.sin(lat_r) ** 2)
    return (
        n * math.cos(lat_r) * math.cos(lng_r),
        n * math.cos(lat_r) * math.sin(lng_r),
        n * (1.0 - e2) * math.sin(lat_r),
    )


def _geodetic(x: float, y: float, z: float, a: float, f: float) -> tuple[float, float]:
    b = a * (1.0 - f)
    e2 = f * (2.0 - f)
    ep2 = e2 / (1.0 - e2)
    p = math.hypot(x, y)
    theta = math.atan2(z * a, p * b)
    lat = math.atan2(
        z + ep2 * b * math.sin(theta) ** 3,
        p - e2 * a * math.cos(theta) ** 3,
    )
    return (math.degrees(lat), math.degrees(math.atan2(y, x)))


def cape(lat_deg: float, lat_min: float, lng_deg: float, lng_min: float) -> tuple[float, float]:
    """A Cape Datum position from COLREG.2/Circ.44, on the WGS 84 chart."""
    lat = dm(lat_deg, lat_min, "S")
    lng = dm(lng_deg, lng_min, "E")
    x, y, z = _ecef(lat, lng, _CAPE_A, _CAPE_F)
    dx, dy, dz = _CAPE_TO_WGS
    return _geodetic(x + dx, y + dy, z + dz, _WGS_A, _WGS_F)


def ps(lat_d: float, lat_m: float, lat_s: float, lng_d: float, lng_m: float, lng_s: float) -> tuple[float, float]:
    return (dms(lat_d, lat_m, lat_s, "N"), dms(lng_d, lng_m, lng_s, "W"))


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


def angle_diff(a: float, b: float) -> float:
    delta = abs(a - b) % 360.0
    if delta > 180.0:
        delta = 360.0 - delta
    return delta


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


def close(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if pts[0] != pts[-1]:
        return pts + [pts[0]]
    return pts


def destination(origin: tuple[float, float], dist_nm: float, brg: float) -> tuple[float, float]:
    rad = math.radians(brg)
    dlat = math.cos(rad) * dist_nm / 60.0
    dlng = math.sin(rad) * dist_nm / 60.0 / max(0.2, math.cos(math.radians(origin[0])))
    return (origin[0] + dlat, origin[1] + dlng)


def to_xy(pt: tuple[float, float], lat0: float, lng0: float) -> tuple[float, float]:
    scale = 60.0 * max(0.2, math.cos(math.radians(lat0)))
    return ((pt[1] - lng0) * scale, (pt[0] - lat0) * 60.0)


def from_xy(xy: tuple[float, float], lat0: float, lng0: float) -> tuple[float, float]:
    scale = 60.0 * max(0.2, math.cos(math.radians(lat0)))
    return (lat0 + xy[1] / 60.0, lng0 + xy[0] / scale)


def origin_of(pts: list[tuple[float, float]]) -> tuple[float, float]:
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def offset(pts: list[tuple[float, float]], dist_nm: float, starboard: bool) -> list[tuple[float, float]]:
    """Parallel curve. starboard is the right-hand side walking along pts.

    A ship keeps the separation zone to port, so each lane sits to starboard
    of its own direction of travel along the zone centreline.
    """
    lat0, lng0 = origin_of(pts)
    xy = [to_xy(pt, lat0, lng0) for pt in pts]
    normals = []
    for start, end in zip(xy, xy[1:]):
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy) or 1e-9
        ux, uy = dx / length, dy / length
        normals.append((uy, -ux) if starboard else (-uy, ux))
    out = []
    for index in range(len(xy)):
        if index == 0:
            nx, ny = normals[0]
            scale = 1.0
        elif index == len(xy) - 1:
            nx, ny = normals[-1]
            scale = 1.0
        else:
            left, right = normals[index - 1], normals[index]
            nx, ny = left[0] + right[0], left[1] + right[1]
            length = math.hypot(nx, ny)
            if length < 0.25:
                nx, ny = right
                scale = 1.0
            else:
                nx, ny = nx / length, ny / length
                denom = nx * right[0] + ny * right[1]
                scale = 1.0 / denom if abs(denom) > 0.35 else 1.0
                scale = max(-2.5, min(2.5, scale))
        x, y = xy[index]
        out.append(from_xy((x + nx * dist_nm * scale, y + ny * dist_nm * scale), lat0, lng0))
    return out


def contains(ring: list[tuple[float, float]], lat: float, lng: float) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        yi, xi = ring[i]
        yj, xj = ring[j]
        if (yi > lat) != (yj > lat):
            edge = (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi
            if lng < edge:
                inside = not inside
        j = i
    return inside


def dist_seg(point: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    lat0 = (a[0] + b[0] + point[0]) / 3.0
    lng0 = (a[1] + b[1] + point[1]) / 3.0
    ax, ay = to_xy(a, lat0, lng0)
    bx, by = to_xy(b, lat0, lng0)
    px, py = to_xy(point, lat0, lng0)
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    if length <= 1e-9:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def dist_line(point: tuple[float, float], line: list[tuple[float, float]]) -> float:
    return min(dist_seg(point, a, b) for a, b in zip(line, line[1:]))


def resample(pts: list[tuple[float, float]], count: int) -> list[tuple[float, float]]:
    if count <= 1 or len(pts) == count:
        return list(pts)
    lengths = [0.0]
    for start, end in zip(pts, pts[1:]):
        lengths.append(lengths[-1] + nm(start, end))
    total = lengths[-1]
    if total < 1e-6:
        return [pts[0]] * count
    out = []
    for index in range(count):
        target = total * index / (count - 1)
        for k in range(1, len(lengths)):
            if lengths[k] + 1e-9 >= target:
                span = lengths[k] - lengths[k - 1]
                t = 0.0 if span < 1e-9 else (target - lengths[k - 1]) / span
                a, b = pts[k - 1], pts[k]
                out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
                break
    return out


def middle(pts: list[tuple[float, float]]) -> tuple[float, float]:
    return resample(pts, 3)[1]


def align(ref: list[tuple[float, float]], pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if nm(ref[0], pts[0]) > nm(ref[0], pts[-1]):
        return list(reversed(pts))
    return list(pts)


def orient(pts: list[tuple[float, float]], target: float) -> list[tuple[float, float]]:
    if angle_diff(axis_bearing(pts), target) > 90.0:
        return list(reversed(pts))
    return list(pts)


def sides_of(ring: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    """The two long sides of a separation zone, split at the two short ends."""
    pts = ring[:-1] if ring[0] == ring[-1] else list(ring)
    n = len(pts)
    if n < 4:
        raise ValueError("a separation zone needs four corners")
    lengths = [nm(pts[i], pts[(i + 1) % n]) for i in range(n)]
    ends = set(sorted(range(n), key=lambda i: lengths[i])[:2])
    chains: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] | None = None
    start = min(ends)
    for step in range(n):
        i = (start + step) % n
        a = pts[i]
        b = pts[(i + 1) % n]
        if i in ends:
            if current:
                chains.append(current)
                current = None
            continue
        if current is None:
            current = [a, b]
        else:
            current.append(b)
    if current:
        chains.append(current)
    if len(chains) != 2:
        raise ValueError(f"expected two zone sides, got {len(chains)}")
    return chains


def facing(ring: list[tuple[float, float]], outer: list[tuple[float, float]]) -> list[tuple[float, float]]:
    def score(chain: list[tuple[float, float]]) -> float:
        return sum(dist_line(pt, outer) for pt in chain) / len(chain)

    return min(sides_of(ring), key=score)


def strip(outer: list[tuple[float, float]], inner: list[tuple[float, float]]) -> list[tuple[float, float]]:
    inner = align(outer, inner)
    return close(list(outer) + list(reversed(inner)))


def midline(outer: list[tuple[float, float]], inner: list[tuple[float, float]]) -> list[tuple[float, float]]:
    inner = align(outer, inner)
    count = max(len(outer), len(inner), 2)
    a = resample(outer, count)
    b = resample(inner, count)
    return [((u[0] + v[0]) / 2.0, (u[1] + v[1]) / 2.0) for u, v in zip(a, b)]


def circle(center: tuple[float, float], radius_nm: float, count: int = 48) -> list[tuple[float, float]]:
    pts = [destination(center, radius_nm, 360.0 * i / count) for i in range(count)]
    return close(pts)


def arc(
    center: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
    bulge: str | None = None,
) -> list[tuple[float, float]]:
    """Arc from start to end. No bulge keeps the shorter arc.

    A compass bulge (N/E/S/W) keeps the arc whose middle lies that way.
    Boston's offshore precautionary area is the eastern arc, which is the
    longer of the two. A boundary that merely says "thence by an arc" is
    the shorter one.
    """
    b0 = bearing(center, start)
    r0 = nm(center, start)
    r1 = nm(center, end)

    def walk(clockwise: bool) -> list[tuple[float, float]]:
        b1 = bearing(center, end)
        if clockwise:
            delta = (b1 - b0) % 360.0 or 360.0
        else:
            delta = -((b0 - b1) % 360.0 or 360.0)
        steps = max(2, int(abs(delta) / 6.0))
        pts = []
        for index in range(steps + 1):
            t = index / steps
            pts.append(destination(center, r0 + (r1 - r0) * t, (b0 + delta * t) % 360.0))
        pts[0] = start
        pts[-1] = end
        return pts

    left, right = walk(True), walk(False)
    if bulge is None:
        return left if len(left) <= len(right) else right

    def score(pts: list[tuple[float, float]]) -> float:
        mid = pts[len(pts) // 2]
        if bulge == "N":
            return mid[0]
        if bulge == "S":
            return -mid[0]
        if bulge == "E":
            return mid[1]
        return -mid[1]

    return left if score(left) >= score(right) else right


class Scheme:
    def __init__(self, sid: str, name: str) -> None:
        self.sid = sid
        self.name = name[:80]
        self.parts: list[dict] = []
        self._n = 0

    def add(self, kind: str, pts: list[tuple[float, float]], *, closed: bool, orient_deg: float | None = None, role: str = "") -> None:
        if len(pts) < 2:
            raise ValueError(f"{self.sid} {role} has no geometry")
        self._n += 1
        self.parts.append({
            "kind": kind,
            "name": self.name,
            "orient": orient_deg,
            "osm": f"cfr-{self.sid}-{self._n}",
            "pts": pts,
            "closed": closed,
            "role": "outer",
            "sid": self.sid,
            "part": role,
        })

    def zone(self, ring: list[tuple[float, float]], role: str) -> list[tuple[float, float]]:
        ring = close(ring)
        self.add(ZONE, ring, closed=True, role=role)
        return ring

    def lane(self, poly: list[tuple[float, float]], axis: list[tuple[float, float]], target: float, role: str) -> None:
        axis = orient(axis, target)
        poly = close(poly)
        self.add(LANE, poly, closed=True, role=role)
        self.add(LANE, axis, closed=False, orient_deg=axis_bearing(axis), role=role + " axis")
        mid = middle(axis)
        if not contains(poly, mid[0], mid[1]):
            raise ValueError(f"{self.sid} {role} centreline left its lane")
        deg = axis_bearing(axis)
        if angle_diff(deg, target) > 70.0:
            raise ValueError(f"{self.sid} {role} bears {deg:.0f}, wanted {target:.0f}")

    def outline(self, pts: list[tuple[float, float]], role: str, dashed: bool = True) -> None:
        self.add(LINE if dashed else BOUND, pts, closed=False, role=role)

    def loop(self, pts: list[tuple[float, float]], role: str) -> None:
        self.add(LINE, close(pts), closed=False, role=role)


def centerline_part(
    scheme: Scheme,
    center: list[tuple[float, float]],
    zone_nm: float,
    lane_nm: float,
    toward: tuple[float, float],
    role: str,
) -> None:
    """Zone and both lanes from a centreline and the widths the regulation gives.

    [toward] is the inshore end (a precautionary area, or the bay). Inbound
    traffic runs toward it and takes the starboard lane.
    """
    if nm(center[0], toward) <= nm(center[-1], toward):
        inbound = list(reversed(center))
    else:
        inbound = list(center)
    outbound = list(reversed(inbound))
    half = zone_nm / 2.0
    scheme.zone(
        offset(center, half, starboard=True) + list(reversed(offset(center, half, starboard=False))),
        role + " zone",
    )
    for travel, target_from, label in (
        (inbound, toward, "inbound"),
        (outbound, outbound[-1], "outbound"),
    ):
        inner = offset(travel, half, starboard=True)
        outer = offset(travel, half + lane_nm, starboard=True)
        axis = offset(travel, half + lane_nm / 2.0, starboard=True)
        target = bearing(travel[0], travel[-1])
        scheme.lane(outer + list(reversed(inner)), axis, target, f"{role} {label}")


def between(
    scheme: Scheme,
    zone_ring: list[tuple[float, float]] | None,
    inner_line: list[tuple[float, float]],
    outer: list[tuple[float, float]],
    target: float,
    role: str,
) -> None:
    """A lane between a zone side (or a separation line) and its outer limit."""
    inner = facing(zone_ring, outer) if zone_ring is not None else inner_line
    scheme.lane(strip(outer, inner), midline(outer, inner), target, role)


def chengshan_jiao() -> Scheme:
    """Pub. 157 §4.46, printed page 197. The northern precautionary area only.

    The inner and outer lanes are not given corners. The wreck cited in the
    central part of the scheme (37°19'15"N, 122°47'24"E) is not a vertex.
    """
    scheme = Scheme("tss-chengshan-jiao-precaution", "Chengshan Jiao north precautionary area")
    scheme.loop(circle(ne_dm(37, 34.5, 122, 42.9), 5.0), "north precautionary area")
    return scheme


def qingdao_precaution() -> Scheme:
    """Pub. 157 §5.16, printed page 208. Precautionary Area No. 2.

    Pilots board vessels of less than 15 m draft inside this ring. The three
    sections of the Qingdao scheme, and Routes 2 and 3, are described by one
    entry position and a direction, which is not enough to draw a lane.
    """
    scheme = Scheme("tss-qingdao-precaution-2", "Qingdao Gang precautionary area No. 2")
    scheme.loop([
        ne_dms(36, 1, 47, 120, 19, 19),
        ne_dms(36, 1, 8, 120, 19, 9),
        ne_dms(36, 0, 54, 120, 20, 20),
        ne_dms(36, 1, 35, 120, 20, 32),
    ], "precautionary area No. 2")
    return scheme


def alphard_banks() -> Scheme:
    """COLREG.2/Circ.44 Annex 9. Off Alphard Banks, 34 miles south of Cape Infanta.

    Westbound traffic takes the northern lane and eastbound the southern
    lane, so each keeps the separation zone to port. The banks themselves
    (35°02.40'S, 020°51.80'E on the same datum) sit in the zone.
    """
    scheme = Scheme("tss-alphard-banks", "Off Alphard Banks")
    nw = cape(34, 58.79, 20, 45.00)
    ne = cape(34, 56.48, 21, 5.00)
    sw = cape(35, 9.54, 20, 45.00)
    se = cape(35, 8.10, 21, 5.00)
    zone = scheme.zone([nw, ne, se, sw], "separation zone")
    between(scheme, None, [nw, ne], [cape(34, 55.76, 20, 45.00), cape(34, 53.45, 21, 5.00)], 260.0, "westbound")
    between(scheme, None, [sw, se], [cape(35, 12.55, 20, 45.00), cape(35, 11.11, 21, 5.00)], 80.0, "eastbound")
    banks = cape(35, 2.40, 20, 51.80)
    if not contains(zone, banks[0], banks[1]):
        raise ValueError("Alphard Banks are outside the separation zone")
    _lanes_ordered(scheme, "Alphard")
    return scheme


def fa_platform() -> Scheme:
    """COLREG.2/Circ.44 Annex 9. Off the FA Platform, 47 miles south of Mossel Bay.

    The southern limit is the five-sided zone in the annex: a southward
    kink at 022°10.86'E, with the eastbound line kinked beside it. The
    northern lane is westbound and the southern lane is eastbound.
    """
    scheme = Scheme("tss-fa-platform", "Off the FA Platform")
    nw = cape(34, 50.11, 22, 0.00)
    ne = cape(34, 47.39, 22, 20.00)
    sw = cape(35, 4.06, 22, 0.00)
    kink = cape(35, 3.37, 22, 10.86)
    se = cape(35, 1.77, 22, 20.00)
    scheme.zone([nw, ne, se, kink, sw], "separation zone")
    between(scheme, None, [nw, ne], [cape(34, 47.07, 22, 0.00), cape(34, 44.75, 22, 20.00)], 260.0, "westbound")
    between(
        scheme,
        None,
        [sw, kink, se],
        [cape(35, 7.16, 22, 0.00), cape(35, 6.35, 22, 11.18), cape(35, 4.81, 22, 20.00)],
        80.0,
        "eastbound",
    )
    _lanes_ordered(scheme, "FA Platform")
    return scheme


def _lanes_ordered(scheme: Scheme, label: str) -> None:
    west = next(part for part in scheme.parts if part["part"] == "westbound axis")
    east = next(part for part in scheme.parts if part["part"] == "eastbound axis")
    if middle(west["pts"])[0] <= middle(east["pts"])[0]:
        raise ValueError(f"{label} westbound lane is not north of the eastbound lane")
    if angle_diff(axis_bearing(west["pts"]), 260.0) > 25.0:
        raise ValueError(f"{label} westbound bears {axis_bearing(west['pts']):.0f}")
    if angle_diff(axis_bearing(east["pts"]), 80.0) > 25.0:
        raise ValueError(f"{label} eastbound bears {axis_bearing(east['pts']):.0f}")


def pieces() -> list[dict]:
    schemes = [
        portland(),
        boston(),
        narragansett(),
        new_york(),
        delaware(),
        chesapeake(),
        cape_fear(),
        galveston(),
        chengshan_jiao(),
        qingdao_precaution(),
        alphard_banks(),
        fa_platform(),
    ]
    out: list[dict] = []
    for scheme in schemes:
        check(scheme)
        out.extend(scheme.parts)
    return out


def check(scheme: Scheme) -> None:
    kinds = {part["kind"] for part in scheme.parts}
    if kinds == {LINE}:
        # A printed precautionary outline, with no lane corners in the source.
        if not scheme.parts:
            raise ValueError(f"{scheme.sid} has no geometry")
        return
    zones = [part["pts"] for part in scheme.parts if part["kind"] == ZONE]
    axes = [part for part in scheme.parts if part["kind"] == LANE and not part["closed"]]
    if scheme.sid != "tss-chesapeake" and not zones:
        raise ValueError(f"{scheme.sid} has no separation zone")
    if not axes:
        raise ValueError(f"{scheme.sid} has no lane centreline")
    for axis in axes:
        pts = axis["pts"]
        mid = middle(pts)
        for zone in zones:
            if contains(zone, mid[0], mid[1]):
                raise ValueError(f"{scheme.sid} {axis['part']} sits in the separation zone")
        if zones:
            gap = min(dist_line(mid, zone) for zone in zones)
            if gap > 8.0:
                raise ValueError(f"{scheme.sid} {axis['part']} is {gap:.1f} nm from its zone")


def portland() -> Scheme:
    scheme = Scheme("tss-portland-me", "In the approaches to Portland, ME")
    # §167.51. The circle excludes the lanes; the lane drawing covers that part.
    scheme.loop(circle(p(43, 31.60, 70, 5.53), 5.45), "precautionary area")
    centerline_part(
        scheme,
        [p(43, 30.18, 69, 59.17), p(43, 24.28, 69, 32.70)],
        zone_nm=1.0,
        lane_nm=0.5,
        toward=p(43, 31.60, 70, 5.53),
        role="eastern approach",
    )
    centerline_part(
        scheme,
        [p(43, 27.00, 70, 3.48), p(43, 7.82, 69, 54.95)],
        zone_nm=1.0,
        lane_nm=1.5,
        toward=p(43, 31.60, 70, 5.53),
        role="southern approach",
    )
    return scheme


def boston() -> Scheme:
    scheme = Scheme("tss-boston", "In the approach to Boston, MA")
    scheme.loop(circle(p(42, 22.71, 70, 46.97), 6.17), "precautionary area")
    # §167.76(b). Eastern arc of the 15.5 nm circle, and the western limit.
    # The same water is described again in §167.151; drawn once, from the
    # NAD 83 positions in §167.76.
    center = p(40, 35.01, 68, 59.96)
    north = p(40, 50.47, 68, 58.67)
    south = p(40, 23.75, 69, 13.95)
    scheme.outline(arc(center, north, south, "E"), "offshore precautionary arc")
    scheme.outline([p(40, 48.03, 69, 2.95), p(40, 36.76, 69, 15.13)], "offshore precautionary limit")
    zone = scheme.zone(
        offset(
            [p(42, 20.73, 70, 39.06), p(42, 18.28, 70, 1.14), p(40, 49.25, 69, 0.81)],
            0.5,
            starboard=True,
        )
        + list(reversed(offset(
            [p(42, 20.73, 70, 39.06), p(42, 18.28, 70, 1.14), p(40, 49.25, 69, 0.81)],
            0.5,
            starboard=False,
        ))),
        "separation zone",
    )
    between(scheme, zone, [], [
        p(40, 50.47, 68, 58.67), p(42, 20.17, 69, 59.40), p(42, 22.71, 70, 38.62),
    ], 0.0, "northbound")
    between(scheme, zone, [], [
        p(42, 18.82, 70, 40.49), p(42, 16.39, 70, 2.88), p(40, 48.03, 69, 2.95),
    ], 180.0, "southbound")
    return scheme


def narragansett() -> Scheme:
    scheme = Scheme("tss-narragansett-buzzards", "Approaches to Narragansett Bay and Buzzards Bay")
    scheme.loop(circle(p(41, 6.00, 71, 23.30), 5.4), "offshore precautionary area")
    scheme.loop(circle(p(41, 25.60, 71, 23.30), 3.55), "inshore precautionary area")
    centerline_part(
        scheme,
        [p(41, 22.70, 71, 23.30), p(41, 11.10, 71, 23.30)],
        zone_nm=2.0,
        lane_nm=1.0,
        toward=p(41, 25.60, 71, 23.30),
        role="Narragansett Bay approach",
    )
    centerline_part(
        scheme,
        [p(41, 10.20, 71, 19.10), p(41, 21.80, 71, 7.10)],
        zone_nm=1.0,
        lane_nm=1.0,
        toward=p(41, 25.00, 71, 0.00),
        role="Buzzards Bay approach",
    )
    return scheme


def new_york() -> Scheme:
    scheme = Scheme("tss-new-york", "Off New York")
    scheme.loop(circle(p(40, 27.50, 73, 49.90), 7.0), "precautionary area")
    nantucket = scheme.zone([
        p(40, 28.75, 69, 14.83), p(40, 27.62, 70, 13.77),
        p(40, 30.62, 70, 14.00), p(40, 31.75, 69, 14.97),
    ], "eastern approach off Nantucket zone")
    between(scheme, nantucket, [], [p(40, 36.75, 69, 15.17), p(40, 35.62, 70, 14.15)], 270.0, "Nantucket westbound")
    between(scheme, nantucket, [], [p(40, 22.62, 70, 13.60), p(40, 23.75, 69, 14.63)], 90.0, "Nantucket eastbound")
    eastern = scheme.zone([
        p(40, 24.33, 73, 4.97), p(40, 24.20, 73, 11.50), p(40, 26.00, 73, 40.93),
        p(40, 27.00, 73, 40.75), p(40, 27.20, 73, 11.50), p(40, 27.33, 73, 4.95),
    ], "eastern approach zone")
    between(scheme, eastern, [], [
        p(40, 32.33, 73, 4.95), p(40, 32.20, 73, 11.50), p(40, 28.00, 73, 40.73),
    ], 270.0, "eastern westbound")
    between(scheme, eastern, [], [
        p(40, 25.05, 73, 41.32), p(40, 19.20, 73, 11.50), p(40, 19.33, 73, 4.97),
    ], 90.0, "eastern eastbound")
    southeast = scheme.zone([
        p(40, 3.10, 73, 17.93), p(40, 6.50, 73, 22.73), p(40, 22.45, 73, 43.55),
        p(40, 23.20, 73, 42.70), p(40, 8.72, 73, 20.10), p(40, 5.32, 73, 15.28),
    ], "south-eastern approach zone")
    between(scheme, southeast, [], [
        p(40, 8.98, 73, 10.87), p(40, 12.42, 73, 15.67), p(40, 24.02, 73, 41.97),
    ], 315.0, "south-eastern north-westbound")
    between(scheme, southeast, [], [
        p(40, 21.82, 73, 44.55), p(40, 2.80, 73, 27.15), p(39, 59.43, 73, 22.35),
    ], 135.0, "south-eastern south-eastbound")
    southern = scheme.zone([
        p(39, 45.70, 73, 48.00), p(40, 20.63, 73, 48.33),
        p(40, 20.87, 73, 47.07), p(39, 45.70, 73, 44.00),
    ], "southern approach zone")
    between(scheme, southern, [], [p(39, 45.70, 73, 37.70), p(40, 21.25, 73, 45.85)], 0.0, "southern northbound")
    between(scheme, southern, [], [p(40, 20.53, 73, 49.65), p(39, 45.70, 73, 54.40)], 180.0, "southern southbound")
    return scheme


def delaware() -> Scheme:
    scheme = Scheme("tss-delaware-bay", "Off Delaware Bay")
    eastern = scheme.zone([
        p(38, 46.30, 74, 34.45), p(38, 46.33, 74, 55.75),
        p(38, 47.45, 74, 55.40), p(38, 47.35, 74, 34.50),
    ], "eastern approach zone")
    between(scheme, eastern, [], [p(38, 48.32, 74, 55.30), p(38, 49.80, 74, 34.60)], 270.0, "eastern westbound")
    between(scheme, eastern, [], [p(38, 45.45, 74, 56.20), p(38, 44.45, 74, 34.35)], 90.0, "eastern eastbound")
    southeast = scheme.zone([
        p(38, 27.00, 74, 42.30), p(38, 43.40, 74, 58.00),
        p(38, 44.20, 74, 57.20), p(38, 27.60, 74, 41.30),
    ], "southeastern approach zone")
    between(scheme, southeast, [], [p(38, 28.80, 74, 39.30), p(38, 45.10, 74, 56.60)], 315.0, "southeastern north-westbound")
    between(scheme, southeast, [], [p(38, 42.80, 74, 58.90), p(38, 27.00, 74, 45.40)], 135.0, "southeastern south-eastbound")
    # §167.173. A two-way route for tugs, not a separation zone and not one-way.
    scheme.outline([
        p(38, 50.75, 75, 3.40), p(38, 47.50, 75, 1.80), p(38, 48.32, 74, 55.30),
        p(38, 50.20, 74, 49.73), p(39, 0.00, 74, 40.23),
    ], "two-way route", dashed=False)
    scheme.outline([
        p(39, 0.00, 74, 41.00), p(38, 50.48, 74, 50.30), p(38, 48.80, 74, 55.25),
        p(38, 48.33, 74, 59.30), p(38, 49.10, 75, 1.65), p(38, 51.27, 75, 2.83),
    ], "two-way route", dashed=False)
    scheme.loop(delaware_precautionary(), "precautionary area")
    return scheme


def delaware_precautionary() -> list[tuple[float, float]]:
    # §167.174. NAD 83. Two arcs of the circle centred on the same point.
    center = p(38, 48.90, 75, 5.60)
    start = p(38, 42.80, 74, 58.90)
    first = arc(center, start, p(38, 48.32, 74, 55.30))
    knee = p(38, 54.80, 75, 1.60)
    second = arc(center, knee, p(38, 55.53, 75, 5.87))
    return (
        first
        + [p(38, 47.50, 75, 1.80), p(38, 50.75, 75, 3.40), p(38, 51.27, 75, 2.83), knee]
        + second[1:]
        + [p(38, 54.00, 75, 8.00), p(38, 46.60, 75, 3.55), start]
    )


def chesapeake() -> Scheme:
    scheme = Scheme("tss-chesapeake", "In the approaches to Chesapeake Bay")
    scheme.loop(circle(p(36, 56.13, 75, 57.45), 2.0), "precautionary area")
    # §167.202. A separation line, not a zone. Lanes lie either side of it.
    sep = [p(36, 57.50, 75, 48.21), p(36, 56.40, 75, 52.40), p(36, 56.40, 75, 54.95)]
    scheme.outline(sep, "eastern separation line")
    between(scheme, None, sep, [
        p(36, 57.94, 75, 48.41), p(36, 56.90, 75, 52.40), p(36, 56.90, 75, 55.14),
    ], 270.0, "eastern westbound")
    between(scheme, None, sep, [
        p(36, 57.04, 75, 48.01), p(36, 55.88, 75, 52.40), p(36, 55.88, 75, 54.95),
    ], 90.0, "eastern eastbound")
    # §167.203. Four separation lines. Inbound is (a)–(b), outbound is (c)–(d).
    # The deep-water route between (b) and (c) is two-way, so it has no axis.
    line_a = [p(36, 50.33, 75, 46.29), p(36, 52.90, 75, 51.52), p(36, 55.96, 75, 54.97)]
    line_b = [p(36, 55.11, 75, 55.23), p(36, 52.35, 75, 52.12), p(36, 49.70, 75, 46.80)]
    line_c = [p(36, 49.52, 75, 46.94), p(36, 52.18, 75, 52.29), p(36, 54.97, 75, 55.43)]
    line_d = [p(36, 54.44, 75, 56.09), p(36, 51.59, 75, 52.92), p(36, 48.87, 75, 47.42)]
    for line, label in ((line_a, "a"), (line_b, "b"), (line_c, "c"), (line_d, "d")):
        scheme.outline(line, f"southern separation line {label}")
    between(scheme, None, line_a, line_b, 0.0, "southern inbound")
    between(scheme, None, line_c, line_d, 180.0, "southern outbound")
    return scheme


def cape_fear() -> Scheme:
    scheme = Scheme("tss-cape-fear", "In the approaches to the Cape Fear River")
    scheme.loop(cape_fear_precautionary(), "precautionary area")
    zone = scheme.zone([
        p(33, 44.94, 78, 4.81), p(33, 32.75, 78, 9.66),
        p(33, 34.50, 78, 14.70), p(33, 45.11, 78, 4.98),
    ], "separation zone")
    between(scheme, zone, [], [p(33, 32.75, 78, 5.99), p(33, 44.38, 78, 3.77)], 0.0, "northbound")
    between(scheme, zone, [], [p(33, 36.22, 78, 18.00), p(33, 46.03, 78, 5.41)], 180.0, "southbound")
    return scheme


def cape_fear_precautionary() -> list[tuple[float, float]]:
    # §167.251. The last leg is a 2 nm arc back to the origin.
    origin = p(33, 47.65, 78, 4.78)
    knee = p(33, 44.28, 78, 3.02)
    center = p(33, 46.03, 78, 5.41)
    return [
        origin,
        p(33, 48.50, 78, 4.27),
        p(33, 49.53, 78, 3.10),
        p(33, 48.00, 78, 1.00),
        p(33, 41.00, 78, 1.00),
        p(33, 41.00, 78, 4.00),
        knee,
    ] + arc(center, knee, origin)[1:]


def galveston() -> Scheme:
    scheme = Scheme("tss-galveston", "In the approaches to Galveston Bay")
    # §167.350. Precautionary areas stay outlines: a hatched zone here would
    # sit across the entrance and the router would treat it as an obstacle.
    scheme.loop([
        p(29, 18.10, 94, 39.20), p(29, 16.10, 94, 37.00), p(29, 18.00, 94, 34.90),
        p(29, 19.40, 94, 37.10), p(29, 19.80, 94, 38.10),
    ], "inshore precautionary area")
    zone = scheme.zone([
        p(29, 17.13, 94, 35.86), p(29, 9.55, 94, 25.80),
        p(29, 9.41, 94, 25.95), p(29, 17.00, 94, 36.00),
    ], "separation zone")
    between(scheme, zone, [], [p(29, 18.00, 94, 34.90), p(29, 11.20, 94, 24.00)], 315.0, "inbound")
    between(scheme, zone, [], [p(29, 16.10, 94, 37.00), p(29, 7.70, 94, 27.80)], 135.0, "outbound")
    scheme.loop([
        p(29, 7.70, 94, 27.80), p(29, 6.40, 94, 26.20), p(29, 6.40, 94, 23.90),
        p(29, 9.10, 94, 20.60), p(29, 11.20, 94, 24.00),
    ], "offshore precautionary area")
    # §166.200(d)(10). Limit lines of the safety fairway. No centreline:
    # the fairway is two-way, and a one-way axis would close the Gulf exit.
    scheme.outline([
        ps(27, 44, 3, 94, 26, 12), ps(28, 4, 48, 94, 26, 12), ps(28, 7, 46, 94, 26, 12),
        ps(29, 6, 24, 94, 26, 12), ps(29, 7, 42, 94, 27, 48), ps(29, 18, 10, 94, 39, 16),
        ps(29, 19, 39, 94, 41, 33), ps(29, 20, 44, 94, 40, 44), ps(29, 19, 23, 94, 37, 8),
        ps(29, 10, 30, 94, 22, 54), ps(29, 10, 17, 94, 22, 30), ps(29, 9, 6, 94, 20, 36),
        ps(28, 17, 17, 92, 57, 59),
    ], "Galveston Entrance Safety Fairway", dashed=False)
    scheme.outline([
        ps(27, 44, 13, 94, 23, 57), ps(29, 6, 24, 94, 23, 55),
        ps(29, 7, 41, 94, 22, 23), ps(28, 11, 57, 92, 53, 25),
    ], "Galveston Entrance Safety Fairway", dashed=False)
    inbound = next(part for part in scheme.parts if part["part"] == "inbound axis")
    outbound = next(part for part in scheme.parts if part["part"] == "outbound axis")
    mid_in = middle(inbound["pts"])
    mid_out = middle(outbound["pts"])
    # Inbound (north-westerly) is the north-east lane; outbound is south-west of it.
    if not (mid_in[1] > mid_out[1]):
        raise ValueError("Galveston inbound lane is not north-east of the outbound lane")
    return scheme


def report() -> None:
    rows = pieces()
    print(f"pieces {len(rows)}")
    current = None
    for part in rows:
        if part["sid"] != current:
            current = part["sid"]
            print(f"\n{current}  {part['name']}")
        extra = ""
        if part["kind"] == LANE and not part["closed"]:
            extra = f"  bearing {axis_bearing(part['pts']):.0f}"
        print(f"  {part['part']}: {part['kind']} n={len(part['pts'])}{extra}")


if __name__ == "__main__":
    report()
