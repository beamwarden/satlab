# Outdoor Enclosure — RPi + Wio Tracker L1 LoRa Range Test Node

3D-printed weatherproof enclosure for a Raspberry Pi paired with a Meshnology
Wio Tracker L1 (SX1262 LoRa + nRF52840), built to get one satlab LoRa node
outside for real free-space-path-loss range/propagation testing. Every LoRa
test so far (`docs/crosslink-setup.md`) has been indoor bench range — both
Wio Tracker units a few feet apart on the same desk. This is the physical
enclosure for iteration 2's "outdoor node," a new subsystem with no prior
build in this repo.

CAD: `cad/outdoor_enclosure.scad`. STLs committed alongside per this repo's
existing CAD convention (see `cad/pivot_frame.scad`'s STL siblings on
`feature/reaction-wheel-cad`).

---

## Hardware BOM

Everything the design assumes gets installed, beyond the two printed parts
themselves. "Likely in a generic screw/nut assortment kit" items still
worth confirming the exact size is actually in the kit, not just assuming.

| Item | Qty | Spec | Notes |
|---|---|---|---|
| Socket-head cap screws | 4 | M3 × 30mm | Corner fasteners, bottom-entry. This length is *not* a generic short assortment size — the screw spans nearly the full enclosure height (see the "Corner fasteners" design note above). Worth confirming a generic kit actually has 30mm, not just the more common 6–16mm range. |
| Heat-set threaded inserts | 4 | M3 | Lid-side corner bosses. A specialty 3D-printing item, not typically in a general hardware assortment — check separately, don't assume the screw kit has these. Needs a soldering iron (or heat-set insert tool) to install, not just pressed in cold. |
| Self-tapping screws | 4 | M2.5 | Pi board mounting, into the standoff pilot holes. Standard Pi/HAT mounting hardware — likely already in a generic kit or leftover from other Pi builds. |
| Cable gland | 1 | PG7 (clamping range ~3–6.5mm cable OD) | DC power entry. Not in a generic screw kit — a distinct purchased part. |
| SMA/RP-SMA bulkhead hardware | 1 set | — | **Already included** with the Meshnology Wio Tracker L1 kit's own RF pigtail (its own bulkhead nut/washer does the clamping) — not something to separately source. |
| Insect-screen mesh | 1 sheet, enough for 2 discs | Fiberglass or aluminum window-screen stock | Cut to ~42mm and ~48mm discs (fan/intake rebate sizes). Real mesh, not part of the print — see "Pest exclusion" design note. |
| Outdoor-rated adhesive | small amount | — | Bonds the mesh discs into their rebates. |
| Gasket tape | ~0.6m | Self-adhesive closed-cell foam weatherstrip, ~3mm thick uncompressed (EPDM/neoprene) | Base wall's top rim, compressed by the lid's 4 corner screws. Not yet sourced/specified beyond this spec — see Open questions. |
| Hose clamps or UV-stable strap ties | 2 | Stainless worm-gear, sized to the actual pole/mast diameter (not baked into the part) | Pole mount, one per groove band. |
| Small fan | 1 | ~40mm, generic — **confirm the real unit's air-opening and mount-hole spacing against `fan_hole_d`/`fan_mount_spacing` before printing**, see Open questions | Not yet identified/sourced. |
| Silica gel packet | 1 | Small, 1–5g class | Desiccant cage. |

**Not in this BOM, already accounted for as existing project hardware:**
Raspberry Pi (model still unconfirmed for this build — see Open questions),
a Wio Tracker L1 unit, and the 3000mAh LiPo pouch battery. Worth flagging:
CLAUDE.md's inventory shows 2 Wio Tracker L1 units, both already deployed
(beamrider-0003, beamrider-0004) — plus a third unit went to
beamrider-cluster-01 for the 3-node mesh test (satlab WORKLOG, 2026-08-23).
**This outdoor build needs its own unit; confirm a 4th Wio Tracker is
actually on hand, or which existing deployment this one relocates,** before
assuming the hardware exists.

---

## CAD style heritage

Follows the parametric/documentation style of `cad/pivot_frame.scad` on the
unmerged `feature/reaction-wheel-cad` branch: named variables in mm grouped
into `/* [Section] */` blocks, a header comment distinguishing measured vs.
assumed dimensions, a `render_part` switch at the bottom, and small fast
test coupons to validate risky dimensions before committing to the full
(multi-hour) print. It is an independent part for an independent subsystem
— nothing here depends on that branch, and it was not merged to produce
this file.

---

## What this had to actually solve (not a generic box)

**Weatherproof DC power entry.** A PG7 cable gland (clamping range ~3–6.5mm
cable OD) through a 12.5mm nominal panel hole, sized for a typical USB-C or
5.5/2.1mm barrel-jack power cable jacket. The gland body does the
clamping/sealing on the cable; the enclosure only needs a clean round hole
(`gland_hole_d = 12.7mm`, +0.2mm print margin — see Tolerances below).

**LoRa antenna RF path — external, not through the shell.** Checked before
assuming either way (see Sources below): the Meshnology-sold Wio Tracker L1
kit ships with a separate whip LoRa antenna connected via an included
**RF Cable (RP-SMA to IPEX)** pigtail, plus a separate GPS antenna. That
means the LoRa antenna is external by product design — the board doesn't
rely on a PCB trace antenna radiating through the case. The enclosure
therefore has a **6.7mm bulkhead passthrough hole** (`antenna_passthrough_cut()`)
on the +X end wall for the pigtail's own RP-SMA bulkhead connector; the
board's IPEX end stays inside, a short cable run to the bulkhead, whip
antenna screws on from outside. This is a hard requirement this design
solves, not an assumption — do not print a version that seals the antenna
inside plastic.

GPS antenna handling is a separate, **unresolved** question — see Open
questions below.

**Drainage / condensation.** A sealed outdoor box will accumulate
condensation from temperature swings regardless of gasket quality — sealing
it "tighter" makes this worse, not better. Two features:
- A 3mm drain hole (`drain_hole_cut()`, commonly-cited practical minimum
  that resists surface-tension blocking) through the floor in the utility
  corridor, away from both boards and the battery pocket.
- A small desiccant packet cage (`desiccant_pins()`, 4 locating pins sized
  for a small 1–5g silica gel packet) so humidity that does get in has
  something to be absorbed by, replaceable through the lid at service time.

The drain hole's position assumes the enclosure is mounted with its floor
at the true low point once installed — see the pole-mount note below on why
that's not fully nailed down yet.

**Mounting — pole-mount, chosen over wall-tab or ground stake.** Two
shallow horizontal alignment grooves (`pole_mount_grooves_cut()`) on the
back (−Y) exterior wall. A stainless worm-gear hose clamp (or a pair of
UV-stable strap ties) wraps around **both** the enclosure and the pole/mast
and seats in these grooves so it can't ride up or down under wind load.
Chosen over a wall-mount tab because a mast/pole is the most likely
available outdoor mounting point for a range test (fence post, sign post,
antenna mast) and over a ground stake because a stake puts the node at
ground level, which both weakens LoRa's line-of-sight range and puts it in
the most flood/runoff-prone spot for the drain hole. Pole diameter is
deliberately **not** baked into the part — the clamp/strap is sized
separately to whatever pole is actually used. This is a design choice, not
an oversight; a wall-tab variant would be a small, mostly-independent
addition if a future deployment needs it.

**Convex/crowned lid — no standing water.** The original flat-top lid design
was changed to a shallow domed top (`lid_top()`, a flattened ellipsoid
intersected with the lid footprint) so rain sheds outward instead of
pooling on a flat horizontal surface. Shallow enough (10mm rise over the
200×110mm footprint) to print with no slicer supports.

**Fasteners enter from the bottom, not through the top.** The original
design had the 4 corner screws going straight down through the lid's top
face into inserts in the base. Changed so the screw enters from the base's
**underside** instead and threads **up** into an insert now living in the
lid (`corner_bosses_lid()`), reached through a full-height clearance bore
in the base's corner post with a counterbore at the very bottom so the
screw head sits flush/recessed rather than protruding. Two reasons, both
about keeping every fastener penetration off the rain-facing top: the
head-to-hole interface at a top-entry screw is itself a hard-to-seal
water-entry point over years outdoors, and so is the insert pocket it
threads into. Bottom entry puts both on the underside, which stays
shadowed from direct rain regardless of mount orientation.

**Consequence worth knowing before ordering hardware:** the screw now has
to span nearly the full enclosure height plus reach into the lid's insert
— roughly 28mm of engagement with the dimensions as designed. Use **M3 ×
30mm socket-head cap screws** (4×), not a generic short assortment screw.

**Ventilation for an active fan.** User plans to run a small fan for active
airflow, not passive-only. The +Y wall (front, over the radio zone) gets a
plain circular opening sized to a generic 40mm fan's air-opening plus its
standard 4-hole mounting pattern (`fan_vent_cut()`) — deliberately **not**
behind a slotted grille, which would choke a small fan's already-modest
static pressure. The fan mounts against the interior wall face and blows
out through the hole. The opposite (−Y) wall gets a same-style but larger
passive intake opening (`intake_vent_cut()`, no fan, positioned over the Pi
zone for a straight through-flow path) — it only needs adequate free area,
not a fan-shaped hole, so it can afford to be simpler. Both openings get a
self-supporting wedge-shaped rain hood (`rain_hood()`) — thick at the wall,
tapering to a thin drip edge, sloped underside so it prints with no
supports and sheds water off the tip instead of letting it run back down
the wall face toward the vent.

**Pest exclusion — birds, bats, wasps.** A plain open vent hole is an
entry point for all three. Two layers, not one, because no single printed
feature does both jobs: printed portcullis-style bars (`pest_grille()`)
sit in each opening — wide enough gaps for airflow, narrow enough (8mm)
to comfortably block birds/bats — plus a shallow rebate on the interior
wall face (`mesh_rebate_cut()`) sized for a cut disc of real insect-screen
mesh (fiberglass or aluminum window-screen stock, **not printed** — see
Open questions). The bars alone do **not** stop wasps; that gap is nowhere
near fine enough. Printing genuine insect-screen tightness directly in
ASA/PETG was ruled out — at that scale FDM walls become fragile lace, not
a durable outdoor part; the screen has to be real mesh, glued into the
rebate, with the bars there to give it something rigid to rest against
under wind/fan suction rather than sag or tear.

**Material — ASA or PETG, not PLA.** UV exposure (PLA embrittles and
chalks outdoors within weeks to months) and closed-black-box summer heat
(PLA softens well under a temperature a sealed enclosure can reach in
direct sun; ASA/PETG have meaningfully higher heat deflection) both rule
PLA out. The reaction-wheel project's PLA choice
(`docs/reaction-wheel.md` print notes) was for an **indoor** demonstrator
with zero UV/thermal exposure — not a precedent that applies here. ASA is
preferred if available (best UV stability, ABS-like without ABS's
warping); PETG is an acceptable fallback with easier bed adhesion, fine for
a shorter test deployment.

---

## Dimensional assumptions — what's real vs. guessed

| Value | Status | Source / rationale |
|---|---|---|
| Pi 4B board 85×56mm, holes on 58×49mm rect, 3.5mm inset, 2.7mm hole dia | Cited public spec (Raspberry Pi official mechanical drawings) | Same outline + hole pattern confirmed shared across 3B/3B+/4B/5 — swapping Pi model should not require moving the standoffs |
| **Exact Pi model = 4B** | **ASSUMED, confirm before printing** | satlab's existing fleet Pi is a Pi 3 Model B (`docs/hardware.md`); no specific unit has actually been assigned to this new outdoor node. Defaulted to 4B as "most likely spare" per the task that started this design — not a confirmed allocation |
| Wio Tracker L1 PCB ~48×34mm | Converged across reseller/marketplace listings | No official Seeed mechanical drawing found — the Seeed wiki product page has no dimensions section, and the DigiKey datasheet PDF is scanned/image-only, not machine-readable text. Treat as approximate, not tight-tolerance |
| Wio Tracker antenna = external, RP-SMA/IPEX pigtail | **Confirmed** | Meshnology product page (meshnology.com), box-contents list: "1 × LoRa Antenna, 1 × GPS Antenna, 1 × RF Cable (RP-SMA to IPEX)" |
| Wio Tracker board+OLED stack height (15mm) | **Guessed**, not calipered | No unit measured for this dimension anywhere in the repo |
| 3000mAh LiPo pouch battery footprint (65×40×12mm pocket) | **Guessed, generously oversized with slack** | CLAUDE.md / `docs/reaction-wheel.md` confirm a 3000mAh Meshnology LiPoly is on hand and earmarked for this radio, but no physical dimensions exist anywhere in the repo. Sized as a loose pocket + strap retention, deliberately not a snug press-fit, because the guess itself is unverified |
| Self-tap M2.5 pilot (2.0mm) for Pi standoffs, M3 heat-set insert pilot (4.0mm) for corner bosses | **Assumed, not bench-validated** on ASA/PETG on the K2 Pro Combo | Print `render_part = "boss_test"` and physically test-fit an M2.5 screw and an M3 heat-set insert before trusting the full base |
| SMA/gland hole print margins (+0.35mm / +0.2mm over nominal) | **Assumed** | Print `render_part = "gland_sma_test"` and test-fit an actual PG7 gland and an SMA bulkhead connector before the full print |
| Fan opening 36mm dia, 32mm mounting-hole spacing | **Assumed generic 40mm-fan spec** | No specific fan unit identified yet — confirm against whatever fan actually gets used before printing; a non-standard hole spacing would need `fan_mount_spacing` updated |
| Rain-hood dimensions (16mm projection, wedge angle) | **Assumed, not engineered** | Sized to visually/geometrically clear the vent openings, not calculated against expected rain angle/wind-driven rain for the actual deployment site |

---

## Tolerances and the K2 Pro Combo's known quirk

The reaction-wheel build (`docs/reaction-wheel.md`) measured a press-fit
608ZZ bearing pocket printing **~0.21mm smaller** than its designed diameter
on this printer (21.85mm designed → 21.64mm actual, first attempt). That
number came from **one small precision press-fit bore on a much smaller,
different part** — it is a starting point for "this printer's holes tend to
print tight," **not** an assumed 1:1 transfer to this part. This enclosure
has no press-fit holes: the Pi/corner bosses are self-tap pilots, and the
gland/SMA holes are loose panel-clearance holes where a nut or gland body
does the actual clamping, not the print tolerance. Risk here is lower than
the reaction-wheel's bearing pocket, but every close-fit hole is called out
above to verify with a test coupon rather than trusted blind, precisely
because the shrinkage mechanism on this printer isn't fully understood
(see the reaction-wheel doc's own open root-cause question on the flywheel
print).

Print settings: use the same conservative regime the reaction-wheel build
converged on for this printer — outer wall ~25–30mm/s, inner wall
~35–40mm/s, infill ~50–60mm/s, 4–5 slow first layers, 0.18–0.2mm layer
height. That regime was found necessary to avoid F00528 "printing without
extruding" flow-limit faults on a much smaller part; there is no reason to
expect a larger part to be more forgiving, so start there rather than
slicer defaults.

---

## Validation performed

`openscad` (2026.06.12, headless) is installed in the environment
(`which openscad` → `/opt/homebrew/bin/openscad`), so this was actually
rendered, not just written and assumed to work:

```bash
openscad -D 'render_part="base"'          -o cad/outdoor_enclosure_base.stl        cad/outdoor_enclosure.scad
openscad -D 'render_part="lid"'           -o cad/outdoor_enclosure_lid.stl         cad/outdoor_enclosure.scad
openscad -D 'render_part="boss_test"'     -o cad/outdoor_enclosure_boss_test.stl   cad/outdoor_enclosure.scad
openscad -D 'render_part="gland_sma_test"' -o cad/outdoor_enclosure_gland_sma_test.stl cad/outdoor_enclosure.scad
```

All four render **manifold, `Status: NoError`** (checked via the CLI's own
render-quality report, not just "no exception thrown"). PNG previews were
also rendered (`--imgsize`/`--camera`) and visually inspected, including a
preview-mode render (no `--render`, so the `%`-tagged debug overlays are
included) that overlays translucent placeholder blocks for the Pi board,
Wio Tracker board, and battery pouch at their designed positions/heights —
confirming by inspection that the three component zones (Pi standoffs, Wio
Tracker locating pins, battery pocket) do not overlap each other, the
corner bosses, or the four wall passthroughs (gland, antenna, drain,
desiccant), and that each zone has real clearance to the walls. This is a
genuine geometric check, not just "it compiled" — but it is a **visual**
check against placeholder rectangular stand-ins for the real boards, not a
dimensioned interference check against actual board 3D models (none exist
for the Wio Tracker publicly, per the dimensions gap above), and it has
**not been checked against a physical print** — see Open questions.

The `%` debug overlay blocks are OpenSCAD "background" modifiers: visible
in preview (`F5`/no `--render`), automatically excluded from the actual
solid geometry on `--render`/STL export — confirmed empirically (the
`--render` PNG and the exported STL both show the physical part only, with
no overlay artifacts).

**Second validation pass (convex lid / bottom-entry fasteners /
ventilation change):** re-rendered all four `render_part` variants after
this change. The first attempt surfaced a real bug via OpenSCAD's own
`WARNING: Ignoring unknown variable` output — `fan_x_center`/
`intake_x_center` were declared in the parameter section, textually
*before* the "Derived layout" section that computes the `wio_origin_x`/
`pi_origin_x` values they depend on, so they silently evaluated against
`undef`. Moved them into the Derived layout section where the values
they reference actually exist; re-rendered clean with zero warnings on
all four variants, still manifold/`NoError`. Camera-angle PNG previews of
both the base (both vent walls) and the lid were visually checked: the
crown is clearly convex, both rain hoods sit cleanly over their vent
openings with no collision against the corner posts, and the lid's new
underside bosses are present.

---

## Open questions — resolve before printing/deploying for real

- **Confirm the actual Pi model** going into this node. If it's the fleet's
  Pi 3B rather than a 4B, the mounting holes/outline are identical so no
  `.scad` changes are needed for the standoffs — but the port stack-up
  (USB/Ethernet/power connector positions and heights) differs slightly by
  model and is **not modeled at all** in this design (no port cutout
  windows — the whole short edge above the standoffs is left open to the
  interior). Confirm the model, then confirm the ports actually clear the
  open edge/gland routing as intended.
- **Caliper the actual Wio Tracker L1 unit** on hand (2 units per
  `CLAUDE.md` inventory) — board footprint, OLED/component stack height,
  and where the IPEX LoRa connector physically sits relative to the board
  edge (determines cable routing length to the SMA bulkhead). No official
  Seeed mechanical drawing was found; everything here is a
  reseller-listing convergence, the same failure mode that cost two wasted
  print attempts on the reaction-wheel flywheel per its own build doc.
- **Measure the actual 3000mAh battery pouch.** The battery bay is
  deliberately oversized with slack because this number was never found —
  confirm it's not, in fact, larger than the guessed 65×40×12mm pocket
  before committing to a full print.
- **GPS antenna handling is unresolved.** This design solves the LoRa
  antenna passthrough (the task's explicit requirement) but the Wio Tracker
  L1 also has an active GPS receiver with its own antenna. Two plausible
  approaches, neither implemented: (a) mount the small GPS patch antenna
  flat under a clear section of the lid — PETG/ASA are both RF-transparent
  enough at 1.575GHz that this is usually fine, but it needs a bench GPS-
  lock test before trusting it outdoors; (b) add a second SMA-class
  passthrough. If GPS is not actually needed for the range test (LoRa RSSI/
  SNR logging plus a known fixed test-node location may be sufficient),
  the simplest fix is to just not use the GPS pigtail at all.
- **Test-print `boss_test` and `gland_sma_test` before the full base.**
  Confirm the M2.5 self-tap pilot, the M3 heat-set insert pilot, the PG7
  gland fit, and the SMA bulkhead fit on real hardware. The full base is a
  ~200×110×38mm part — likely a multi-hour print on this printer at the
  conservative speed settings above, so validate the small stuff first,
  same reasoning the reaction-wheel build used for its bearing/mount-hole
  coupons.
- **Gasket.** The design assumes a self-adhesive closed-cell foam
  weatherstrip applied to the flat top rim of the base wall, compressed by
  the lid's 4 corner screws. No gasket material has been sourced or
  specified — pick one (common EPDM/neoprene foam tape, ~3mm thick
  uncompressed) before the first outdoor deployment.
- **Verify mounting orientation vs. drain placement.** The drain hole
  assumes the enclosure sits with its floor genuinely at the low point once
  pole-mounted. Depending on how the pole-mount grooves end up oriented in
  practice (which face ends up "down"), the drain position may need to
  move — confirm against the actual mounting orientation before the final
  print, not just the CAD's implicit assumption.
- **Confirm the actual fan.** `fan_hole_d`/`fan_mount_spacing` assume a
  generic 40mm fan; measure the real unit's air-opening and mounting-hole
  spacing before printing, and update those variables if they differ.
- **Source insect-screen mesh** (fiberglass or aluminum window-screen
  stock) and cut two discs to fit the mesh rebates (`fan_hole_d`/
  `intake_hole_d` + `mesh_rebate_extra_d`), plus an outdoor-rated
  adhesive to bond them in place. This is real hardware, not something
  the print provides — the printed grille bars only handle birds/bats.
- **Source M3 × 30mm socket-head cap screws** (4×) for the corner
  fasteners — see the bottom-entry design change above for why they need
  to be this long, not a generic short assortment screw.
- **No IP rating claimed.** This is a gasketed, gland-sealed, drained
  design following good outdoor-electronics practice, not a part tested or
  rated to any IP standard. Treat it as "weather-resistant for a bench-
  adjacent range test," not "submersible" or "storm-proof."

---

## Sources

- Raspberry Pi mounting-hole pattern (58×49mm, M2.5, 2.7mm dia, 3.5mm
  inset) and confirmation the 3B/3B+/4B/5 share the same board outline and
  hole pattern: Raspberry Pi official mechanical drawings
  (`datasheets.raspberrypi.com`), cross-checked against multiple secondary
  summaries.
- Wio Tracker L1 PCB footprint (~48×34mm): converged from reseller listings
  (Botland product listing and aggregated search results); no official
  Seeed dimensioned drawing was found.
- Wio Tracker L1 external antenna confirmation (RP-SMA/IPEX pigtail + GPS
  antenna, both external): Meshnology product page
  (`meshnology.com/products/meshnology-n37-wio-tracker-l1-lora-meshtastic-gps-dev-board-with-1-3-oled`),
  box-contents list.
- Seeed Wio Tracker L1 wiki (`wiki.seeedstudio.com/wio_tracker_l1_node/`)
  and product page (`seeedstudio.com/Wio-Tracker-L1-p-6453.html`): confirmed
  USB-C 5V/1A power, 2P-1.25mm 3.7V battery connector, but no mechanical
  dimensions section.
