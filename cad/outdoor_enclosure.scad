// ---------------------------------------------------------------------------
// Outdoor enclosure for a Raspberry Pi + Meshnology Wio Tracker L1 (SX1262
// LoRa / nRF52840) -- a real-world LoRa range/propagation test node.
//
// Why this exists: every satlab LoRa test to date (docs/crosslink-setup.md,
// Phase 1/2) has been indoor bench range -- both Wio Tracker units a few
// feet apart on the same desk. This part gets one node outside and
// weatherproofed, for actual free-space-path-loss range testing per the
// iteration 2 radio plan (CLAUDE.md "Iteration 2 -- Radio"). It is a NEW
// physical build -- no prior enclosure exists in this repo, and there is no
// `cad/` directory on develop before this branch.
//
// CAD heritage / style: this borrows the parametric-vars-in-mm,
// measured-vs-assumed-labeling, render_part-switch, fast-test-coupon-before-
// full-print house style of cad/pivot_frame.scad on the unmerged
// feature/reaction-wheel-cad branch (see docs/reaction-wheel.md there). It
// is otherwise an unrelated part for an unrelated subsystem -- nothing here
// depends on that branch and it was not merged to produce this file.
//
// ---------------------------------------------------------------------------
// WHAT'S A REAL MEASUREMENT VS. AN ASSUMPTION -- READ BEFORE PRINTING
// ---------------------------------------------------------------------------
//
// MEASURED (cited public spec, not calipered off a physical unit -- this
// project has been burned before trusting published specs over calipers,
// see the reaction-wheel motor-holder note in docs/reaction-wheel.md, so
// treat "measured" here as weaker than "calipered"):
//   - Raspberry Pi 4B board outline 85 x 56mm, mounting holes on a 58 x 49mm
//     rectangle inset 3.5mm from two adjacent edges, 2.7mm hole dia for
//     M2.5 screws (Raspberry Pi official mechanical drawings). This exact
//     board outline and hole pattern is shared by the 3B, 3B+, 4B, and 5 --
//     so pi_board_l/w/pi_hole_* do NOT need to change to swap Pi models.
//     What DOES vary by model and is NOT modeled here: the USB/Ethernet/
//     power port stack-up on one short edge (position and height differ a
//     little by model/revision) -- this design leaves that whole edge open
//     to the interior rather than cutting model-specific port windows, see
//     docs/outdoor-enclosure.md open questions.
//   - Wio Tracker L1 bare PCB footprint ~48 x 34mm -- converged across
//     several reseller/marketplace listings (Botland, aggregated search
//     results), NOT an official Seeed mechanical drawing. The Seeed wiki
//     product page has no dimensions section as of this writing and the
//     DigiKey datasheet PDF is scanned/image-only, not machine-readable.
//     Treat as a rough number, not a tight-tolerance one.
//   - Antenna handling -- CONFIRMED (Meshnology product page, box-contents
//     list, meshnology.com): the Meshnology-sold Wio Tracker L1 kit ships
//     with a separate whip LoRa antenna wired through an included
//     "RF Cable (RP-SMA to IPEX)" pigtail, plus a separate GPS antenna.
//     This means the LoRa antenna is EXTERNAL by product design, not a PCB
//     trace antenna meant to radiate through a sealed case -- so this
//     enclosure passes the antenna OUT through the wall via the pigtail's
//     own RP-SMA bulkhead end (antenna_passthrough() below), it does not
//     rely on RF transparency through the printed shell. GPS antenna
//     handling is a separate, unresolved question -- see doc.
//
// ASSUMED -- CONFIRM BEFORE THE FIRST FULL PRINT:
//   - Exact Pi model. satlab's existing fleet Pi is a Pi 3 Model B
//     (docs/hardware.md, CLAUDE.md hardware inventory), but this is a NEW
//     node and no specific unit has been assigned to it yet. Defaulted to
//     Pi 4B dims as "most likely spare unit" per the task brief that
//     started this design, NOT because a Pi 4B has been confirmed on hand
//     for this build.
//   - Wio Tracker board+OLED stack height (wio_stack_h) -- no unit
//     calipered, this is a guess with slack, not a snug fit.
//   - 3000mAh LiPo pouch battery footprint (batt_pocket_*). CLAUDE.md and
//     docs/reaction-wheel.md both confirm a 3000mAh Meshnology LiPoly
//     exists on hand and is earmarked for this radio, but no physical
//     dimensions were found or measured anywhere in this repo. Sized
//     generously with slack (batt_pocket_slack), deliberately NOT a
//     press-fit pocket, because the size itself is a guess.
//   - Self-tapping M2.5 pilot hole for the Pi standoffs (pi_pilot_d) and
//     the M3 heat-set insert pilot for the corner bosses (corner_insert_d)
//     -- neither bench-validated on ASA/PETG on this printer. Test-print
//     the standoff/boss coupon (render_part = "boss_test") before
//     committing to the full base.
//   - sma_hole_d / gland_hole_d print margins (see those variables below)
//     -- verify with render_part = "gland_sma_test" before the full print.
//
// ---------------------------------------------------------------------------
// PRINTER / MATERIAL NOTES
// ---------------------------------------------------------------------------
// Printer: Creality K2 Pro Combo (multi-material). The reaction-wheel build
// (docs/reaction-wheel.md) found this printer needs wall/infill speeds well
// below slicer defaults (outer wall ~25-30mm/s, inner wall ~35-40mm/s,
// infill ~50-60mm/s, 4-5 slow first layers) to avoid F00528 flow-limit
// faults, and separately measured a press-fit 608ZZ bearing pocket printing
// ~0.21mm smaller than its designed diameter (21.85mm designed -> 21.64mm
// actual on the first attempt). That 0.21mm number came from ONE small
// precision press-fit bore on a much smaller, different part -- it is a
// starting point for "this printer's holes tend to print tight," NOT an
// assumed 1:1 transfer to this part. This enclosure has no press-fit holes
// (Pi/corner holes are self-tap pilots, not press fits; the gland and SMA
// holes are loose panel clearance holes with a nut/gland body doing the
// clamping, not the print tolerance) so the risk is lower, but every
// close-fit hole below is called out to verify with a test coupon rather
// than trusted blind. See render_part = "boss_test" / "gland_sma_test".
//
// Material: ASA or PETG. NOT PLA. This part lives outdoors -- UV exposure
// (PLA embrittles and chalks within weeks to months outside) and closed
// black-box summer heat (PLA starts softening well under temperatures a
// sealed enclosure can reach in direct sun; ASA/PETG have meaningfully
// higher heat deflection) both rule PLA out. The reaction-wheel project's
// PLA choice (docs/reaction-wheel.md print notes) was for an INDOOR
// demonstrator with no UV/thermal exposure -- not a precedent that applies
// here. ASA is the better choice if available (best UV stability of the
// two, similar-ish behavior to ABS without ABS's warping); PETG is an
// acceptable fallback with easier bed adhesion, fine for a shorter test
// deployment.
// ---------------------------------------------------------------------------

/* [Raspberry Pi board -- default Pi 4B, CONFIRM ACTUAL UNIT BEFORE PRINTING] */
pi_board_l      = 85;    // MEASURED (RPi mech. drawing): shared by 3B/3B+/4B/5
pi_board_w      = 56;    // MEASURED
pi_hole_dx      = 58;    // MEASURED: hole spacing along length
pi_hole_dy      = 49;    // MEASURED: hole spacing along width
pi_hole_inset_x = 3.5;   // MEASURED: inset from two adjacent edges
pi_hole_inset_y = 3.5;
pi_hole_d       = 2.75;  // MEASURED board hole (2.7mm official) + 0.05mm clearance
pi_pilot_d      = 2.0;   // ASSUMED self-tap M2.5 pilot -- verify on boss_test coupon
pi_standoff_od  = 6.5;
pi_standoff_h   = 6;     // clears microSD card / underside components
pi_port_clear_h = 17;    // ASSUMED headroom for USB-C/HDMI/Ethernet stack (not cut as windows -- see doc)

/* [Wio Tracker L1 board -- ASSUMED, no official Seeed mechanical drawing found] */
wio_board_l = 48;   // ASSUMED (converged reseller listings, not calipered)
wio_board_w = 34;
wio_stack_h = 15;   // ASSUMED clearance for OLED + header/connector stack above the PCB

/* [Battery bay -- 3000mAh LiPo pouch, ASSUMED, no physical unit measured] */
batt_pocket_l     = 65;
batt_pocket_w     = 40;
batt_pocket_h     = 12;
batt_wall_h       = 3;   // low retaining wall height around the pocket (not a lid, strap does retention)

/* [Enclosure shell] */
wall_t      = 3;     // ASA/PETG outdoor wall thickness
floor_t     = 3.5;
base_wall_h = 38;    // interior clear height = base_wall_h - floor_t = 34.5mm
lid_t       = 3;
lid_skirt_h = 8;      // downturned lid lip that overlaps the base wall's outer face
lid_skirt_clear = 0.3; // per-side clearance so the skirt slides over the base wall (not press-fit)
ext_l = 200;
ext_w = 110;

/* [Corner fasteners -- base<->lid] */
corner_inset        = 10;
corner_boss_od       = 10;
corner_insert_d      = 4.0;  // ASSUMED M3 heat-set insert pilot -- verify on boss_test coupon
corner_insert_depth  = 6;
corner_clear_d        = 3.4; // M3 clearance through the lid

/* [Antenna passthrough -- LoRa, external by product design, see header] */
// Standard SMA/RP-SMA bulkhead panel hole is 6.35mm (1/4in) nominal; the
// pigtail's own bulkhead nut/washer does the clamping and sealing (with a
// dab of silicone sealant around the nut face), so this only needs to be a
// loose clearance hole -- +0.35mm over nominal as a margin against this
// printer's hole-shrink tendency (see printer note above). ASSUMED margin
// amount -- verify on the gland_sma_test coupon.
sma_hole_d     = 6.7;
antenna_wall_z = floor_t + 18; // roughly mid-height on the +X end wall

/* [DC power cable entry] */
// PG7 cable gland (clamping range ~3-6.5mm cable OD -- fits a typical
// USB-C or 5.5/2.1mm barrel-jack pigtail cable jacket) has a 12.5mm nominal
// panel hole. +0.2mm margin for the same print-tight-hole reason as above.
// ASSUMED margin -- verify on gland_sma_test coupon.
gland_hole_d = 12.7;
gland_wall_z = floor_t + 18; // -X end wall, near the Pi zone

/* [Drainage / desiccant] */
drain_hole_d     = 3;   // commonly-cited practical minimum for a gravity drain that resists surface-tension blocking
desiccant_pack_w = 14;  // small silica gel packet (1-5g class), retained loosely by 4 locating pins
desiccant_pack_l = 30;
desiccant_pin_d  = 3;
desiccant_pin_h  = 10;

/* [Pole mount -- chosen default; see docs/outdoor-enclosure.md for why over wall-tab/stake] */
// Two shallow horizontal alignment grooves on the back (-Y) exterior wall.
// A stainless worm-gear hose clamp (or a pair of UV-stable strap ties)
// wraps around BOTH the enclosure and the pole and seats in these grooves
// so it can't ride up/down the pole under wind load. Pole diameter is
// intentionally NOT baked into the part -- the clamp/strap is sized
// separately to whatever pole/mast is actually used.
pole_groove_w = 140;  // spans most of the back wall width
pole_groove_h = 8;
pole_groove_d = 1.5;  // shallow -- just enough to key the band, not a structural slot

/* [Quality] */
$fn = 64;

// ---------------------------------------------------------------------------
// Derived layout -- interior floor plan
// ---------------------------------------------------------------------------
// Two zones side by side: Pi zone (standoffs) on the -X side, radio zone
// (Wio Tracker + battery bay) on the +X side, with a utility corridor at
// the far +X end for the antenna passthrough, drain, and desiccant. Antenna
// bulkhead lands on the +X end wall near the radio zone (short cable run
// from the Wio Tracker's LoRa u.FL connector); DC power gland lands on the
// -X end wall near the Pi zone.

interior_x0 = -ext_l/2 + wall_t;
interior_x1 =  ext_l/2 - wall_t;
interior_y0 = -ext_w/2 + wall_t;
interior_y1 =  ext_w/2 - wall_t;

pi_origin_x = interior_x0 + 8;
pi_origin_y = -pi_board_w/2;

wio_origin_x = pi_origin_x + pi_board_l + 20; // 20mm gap for wire routing / wall clearance
wio_origin_y = 6;

batt_origin_x = wio_origin_x;
batt_origin_y = wio_origin_y - 8 - batt_pocket_w; // 8mm gap below the Wio Tracker footprint

drain_x     = 90;
drain_y     = -45;
desiccant_x = 89;
desiccant_y = 0;

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------
module rect_prism_centered(l, w, h) {
    translate([-l/2, -w/2, 0]) cube([l, w, h]);
}

module pi_hole_positions() {
    for (sx = [0, pi_hole_dx])
        for (sy = [0, pi_hole_dy])
            translate([pi_origin_x + pi_hole_inset_x + sx, pi_origin_y + pi_hole_inset_y + sy, 0])
                children();
}

module corner_positions() {
    for (sx = [-1, 1])
        for (sy = [-1, 1])
            translate([sx * (ext_l/2 - corner_inset), sy * (ext_w/2 - corner_inset), 0])
                children();
}

// ---------------------------------------------------------------------------
// Base tray
// ---------------------------------------------------------------------------
module base_walls() {
    difference() {
        rect_prism_centered(ext_l, ext_w, base_wall_h);
        translate([0, 0, floor_t])
            rect_prism_centered(ext_l - 2*wall_t, ext_w - 2*wall_t, base_wall_h);
    }
}

module pi_standoffs() {
    pi_hole_positions()
        difference() {
            cylinder(h = floor_t + pi_standoff_h, d = pi_standoff_od);
            translate([0, 0, floor_t + pi_standoff_h - 4])
                cylinder(h = 5, d = pi_pilot_d);
        }
}

module wio_locating_pins() {
    pin_d = 3; pin_h = 4; inset = 2;
    for (sx = [wio_origin_x + inset, wio_origin_x + wio_board_l - inset])
        for (sy = [wio_origin_y + inset, wio_origin_y + wio_board_w - inset])
            translate([sx, sy, floor_t])
                cylinder(h = pin_h, d = pin_d);
}

module wio_tie_slots() {
    slot_l = 10; slot_w = 4;
    for (sy = [wio_origin_y + 4, wio_origin_y + wio_board_w - 4])
        translate([wio_origin_x + wio_board_l/2 - slot_l/2, sy - slot_w/2, -1])
            cube([slot_l, slot_w, floor_t + 2]);
}

module battery_bay() {
    difference() {
        translate([batt_origin_x, batt_origin_y, floor_t])
            cube([batt_pocket_l, batt_pocket_w, batt_wall_h]);
        translate([batt_origin_x + wall_t, batt_origin_y + wall_t, floor_t - 1])
            cube([batt_pocket_l - 2*wall_t, batt_pocket_w - 2*wall_t, batt_wall_h + 2]);
    }
}

module battery_tie_slots() {
    slot_l = 10; slot_w = 4;
    for (sy = [batt_origin_y + 6, batt_origin_y + batt_pocket_w - 6])
        translate([batt_origin_x + batt_pocket_l/2 - slot_l/2, sy - slot_w/2, -1])
            cube([slot_l, slot_w, floor_t + 2]);
}

module desiccant_pins() {
    for (sx = [desiccant_x - desiccant_pack_w/2, desiccant_x + desiccant_pack_w/2])
        for (sy = [desiccant_y - desiccant_pack_l/2, desiccant_y + desiccant_pack_l/2])
            translate([sx, sy, floor_t])
                cylinder(h = desiccant_pin_h, d = desiccant_pin_d);
}

module drain_hole_cut() {
    translate([drain_x, drain_y, -1])
        cylinder(h = floor_t + 2, d = drain_hole_d);
}

module antenna_passthrough_cut() {
    // +X end wall, external LoRa antenna bulkhead (see header rationale)
    translate([ext_l/2 - wall_t/2, wio_origin_y + wio_board_w/2, antenna_wall_z])
        rotate([0, 90, 0])
            cylinder(h = wall_t + 2, d = sma_hole_d, center = true);
}

module gland_passthrough_cut() {
    // -X end wall, DC power cable entry near the Pi zone
    translate([-ext_l/2 + wall_t/2, 0, gland_wall_z])
        rotate([0, 90, 0])
            cylinder(h = wall_t + 2, d = gland_hole_d, center = true);
}

module corner_bosses_base() {
    corner_positions()
        difference() {
            cylinder(h = base_wall_h, d = corner_boss_od);
            translate([0, 0, base_wall_h - corner_insert_depth])
                cylinder(h = corner_insert_depth + 1, d = corner_insert_d);
        }
}

module pole_mount_grooves_cut() {
    // Two shallow horizontal bands cut into the -Y exterior wall face
    for (gz = [floor_t + 8, base_wall_h - 8])
        translate([-pole_groove_w/2, -ext_w/2 - 1, gz - pole_groove_h/2])
            cube([pole_groove_w, wall_t/2 + pole_groove_d + 1, pole_groove_h]);
}

// -- debug-only reference geometry: preview overlay for fit-checking,
// excluded from CSG/STL output by the % modifier (OpenSCAD "background"
// object -- shown transparent in F5 preview, dropped from F6 render/export).
module debug_component_overlays() {
    // Pi board + port-stack headroom
    %translate([pi_origin_x, pi_origin_y, floor_t + pi_standoff_h])
        cube([pi_board_l, pi_board_w, 1.6]);
    %translate([pi_origin_x, pi_origin_y, floor_t + pi_standoff_h + 1.6])
        cube([pi_board_l, pi_board_w, pi_port_clear_h]);
    // Wio Tracker board + stack
    %translate([wio_origin_x, wio_origin_y, floor_t])
        cube([wio_board_l, wio_board_w, wio_stack_h]);
    // Battery pouch (drawn at its assumed nominal size, inside the pocket's slack)
    %translate([batt_origin_x + wall_t, batt_origin_y + wall_t, floor_t])
        cube([batt_pocket_l - 2*wall_t, batt_pocket_w - 2*wall_t, batt_pocket_h]);
}

module enclosure_base() {
    difference() {
        union() {
            base_walls();
            pi_standoffs();
            wio_locating_pins();
            battery_bay();
            corner_bosses_base();
        }
        wio_tie_slots();
        battery_tie_slots();
        drain_hole_cut();
        antenna_passthrough_cut();
        gland_passthrough_cut();
        pole_mount_grooves_cut();
    }
    desiccant_pins();
    debug_component_overlays();
}

// ---------------------------------------------------------------------------
// Lid
// ---------------------------------------------------------------------------
module enclosure_lid() {
    difference() {
        union() {
            // flat top
            rect_prism_centered(ext_l, ext_w, lid_t);
            // downturned skirt, slides over the base wall's outer face
            translate([0, 0, -lid_skirt_h])
                difference() {
                    rect_prism_centered(ext_l, ext_w, lid_skirt_h + lid_t);
                    translate([0, 0, -1])
                        rect_prism_centered(
                            ext_l - 2*wall_t + 2*lid_skirt_clear,
                            ext_w - 2*wall_t + 2*lid_skirt_clear,
                            lid_skirt_h + lid_t + 2);
                }
        }
        // corner screw clearance, straight through skirt + top
        corner_positions()
            translate([0, 0, -lid_skirt_h - 1])
                cylinder(h = lid_skirt_h + lid_t + 2, d = corner_clear_d);
    }
}

// ---------------------------------------------------------------------------
// Fast test coupons -- print these BEFORE the full base (~10+ hour part).
// Mirrors the reaction-wheel branch's bearing_test / quarter-coupon
// approach: validate one risky dimension on a small, fast print first.
// ---------------------------------------------------------------------------

// boss_test: one Pi standoff + one corner boss, for self-tap pilot hole
// (pi_pilot_d) and heat-set insert pilot hole (corner_insert_d) fit checks.
module boss_test() {
    base_plate_l = 30; base_plate_w = 30; base_plate_h = floor_t;
    difference() {
        union() {
            cube([base_plate_l, base_plate_w, base_plate_h]);
            translate([base_plate_l/2, base_plate_w/2, base_plate_h])
                difference() {
                    cylinder(h = pi_standoff_h, d = pi_standoff_od);
                    translate([0, 0, pi_standoff_h - 4])
                        cylinder(h = 5, d = pi_pilot_d);
                }
        }
    }
    translate([base_plate_l + 15, 0, 0]) {
        boss_h = 15;
        difference() {
            cylinder(h = boss_h, d = corner_boss_od);
            translate([0, 0, boss_h - corner_insert_depth])
                cylinder(h = corner_insert_depth + 1, d = corner_insert_d);
        }
    }
}

// gland_sma_test: short wall segment with both panel holes at true size,
// for the cable gland and SMA bulkhead fit checks.
module gland_sma_test() {
    seg_l = 60; seg_h = 40;
    difference() {
        cube([seg_l, wall_t, seg_h]);
        translate([15, -1, 18]) rotate([-90, 0, 0]) cylinder(h = wall_t + 2, d = gland_hole_d);
        translate([45, -1, 18]) rotate([-90, 0, 0]) cylinder(h = wall_t + 2, d = sma_hole_d);
    }
}

/* [Render selection] */
render_part = "base"; // "base" | "lid" | "boss_test" | "gland_sma_test"

if (render_part == "base") enclosure_base();
else if (render_part == "lid") enclosure_lid();
else if (render_part == "boss_test") boss_test();
else gland_sma_test();
