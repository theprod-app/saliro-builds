# How these databases were built

The bytes are the files shipped in Saliro.

| File | SHA-256 | Bytes |
| --- | --- | --- |
| sea_tss.bin | 8f98b20be1e831fb41e2ed03b1508025e841b00c00a9d8b1b216a39f66f75c5d | 235360 |
| sea_zones.bin | b83135c47ca406cb54398e3dcaaf98912930eaaa73510457404c213b7747669e | 1105181 |

## sea_tss.bin

Header `TSS1`, little-endian. Built by `scripts/build_sea_tss.py`.

The OpenStreetMap extract is an Overpass query (`out geom`) for ways and
relations tagged `seamark:type` as one of `separation_zone`,
`separation_line`, `separation_boundary`, or `separation_lane`. Inland
waterways mistagged as separation lanes are dropped. Each scheme is kept
as mapped: zone polygons, boundary lines, separation lines, and lane
centrelines. Lane arrows follow the way, or
`seamark:separation_lane:orientation` when that tag is set.

Schemes missing from the extract are merged from `scripts/supplements.py`.
Those use coordinates printed in 33 CFR 166 and 167, NGA Pub. 157, and
COLREG.2/Circ.44. They are not OpenStreetMap and not a chart product.

## sea_zones.bin

Header `SZN2`, version 1. Most records are IMO and domestic limit lines
closed on the Natural Earth 10 m coast. Natural Earth is public domain.

The record `china-yangtze` is a centreline taken from OpenStreetMap and
buffered between the published endpoints of that river section. That
record is the OpenStreetMap-derived part of this file.

## What is not here

UKHO, Admiralty, and the MARNET / Eurostat searoute graph are not in
these databases and are not used to build them.
