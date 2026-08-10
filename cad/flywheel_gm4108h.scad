// ---------------------------------------------------------------------------
// Reaction-wheel flywheel for the satlab single-axis demonstrator
//
// Target motor: iPower GM4108H-120T gimbal BLDC (10 mm hollow shaft).
// CAD heritage: charleslabs.fr reaction wheel (gaspode-wonder/reaction_wheel).
//   Their wheel is a 130 mm disk driven by a NEMA 17 stepper and tuned with
//   M8 threaded rod + nuts. This part keeps the *adjustable-mass tuning* idea
//   (a ring of bolt pockets) but is bored and bolted for the GM4108H rotor
//   instead of a NEMA 17 face.
//
// Design intent: rim-loaded disk. Mass is concentrated in a thick outer rim
// (web in the middle is thin) to maximize moment of inertia per gram, so the
// motor gets the most angular-momentum authority for the least rotor load.
//
// MEASURED 2026-08-08 (digital caliper, off the physical motor):
// The rotor bell (the outer barrel + this cap -- confirmed by spin test: the
// barrel turns freely as one piece with this face) is NOT the same face as
// the wire-exit base. That base is fixed/stationary and carries a small
// protruding shaft stub; this cap has no protrusion at all -- the 7.85mm
// center feature is a flush RECESSED bore, nothing sticks through it. So
// unlike the original charleslabs-derived assumption, the flywheel hub does
// not need to clear a protruding shaft on this face -- `shaft_clearance()`
// below is now just a plain pass-through bore, not a boss pocket.
//   - Cap OD: 47.13mm
//   - Center bore: 7.85mm (recessed, flush -- not a protrusion)
//   - Mounting holes: 4, bolt-circle diameter 30.80mm (33.19mm outer-edge-to
//     -outer-edge across two opposite holes, minus the 2.39mm hole dia)
//   - Motor hole diameter: 2.39mm as measured -- these are TAPPED holes
//     (confirmed once the motor's screw packet was found: 2.78mm shaft,
//     5.39mm head -- shaft is larger than the 2.39mm hole reading because
//     that reading was off the thread crests, not a clearance bore). Screws
//     thread into the motor; `mount_bolt_d`/`mount_cbore_d` below are clearance
//     for the FLYWHEEL side only, sized off the real screw dimensions.
//
// NOTE for docs/reaction-wheel.md: the shaft does not rotate (it's fixed to
// the stationary base plate), so the AS5600 encoder magnet cannot go on "the
// shaft end" as currently written -- it needs to mount on the rotating bell
// instead. Not fixed here; flagged for a follow-up doc edit.
// ---------------------------------------------------------------------------

/* [Wheel] */
wheel_od            = 120;   // outer diameter (mm). 120 keeps it under a 130 bed corner-to-corner and under the charleslabs 130 disk.
rim_width           = 12;    // radial thickness of the heavy rim (mm)
rim_height          = 16;    // axial height of the rim (mm) -- matches charleslabs flywheel thickness
web_height          = 4;     // thickness of the central web connecting hub to rim (mm)

/* [Hub / motor interface] */
boss_clear_d        = 8.5;   // plain pass-through bore over the recessed 7.85mm register (mm) -- no protrusion to clear on this face, just clearance so the hub material doesn't foul the register ring.
boss_clear_h        = 6;     // unused now that shaft_clearance() is a single through-bore; kept for reference, see module below.
hub_d               = 44;    // diameter of the solid hub region around the bolt circle (mm) -- sized to clear the 30.80mm bolt circle + counterbores with margin, roughly matching the 47.13mm cap OD.

mount_bolt_circle_d = 30.80; // MEASURED: GM4108H rotor mounting bolt-circle diameter (mm)
mount_bolt_count    = 4;     // MEASURED: number of rotor mounting holes
mount_bolt_d        = 3.1;   // MEASURED: actual screw (from the motor's hardware packet) has a 2.78mm shaft -- motor holes are tapped, screws thread into the motor, not through-bolted. 3.1mm gives ~0.3mm clearance for a free fit + FDM shrinkage.
mount_cbore_d       = 6.0;   // MEASURED: screw head is 5.39mm -- 6.0mm gives clearance for the head to sit flush/below the web.
mount_cbore_h       = 5.9;   // counterbore depth (mm). CORRECTED 2026-08-09, second pass: the 7.4mm depth (targeting 4mm engagement) test-fit with a ~1mm gap between the hub's motor-facing face and the motor even with the screw seated as far as it would go -- the screw bottomed out IN THE MOTOR'S TAPPED HOLE before its head reached the counterbore shoulder, meaning real engagement was only ~3mm (4mm target minus the ~1mm gap), not a counterbore/head-seating problem. Backed off to a 2.5mm target with margin below that ~3mm observed limit (only one of the 4 holes has been test-fit, so leaving room for per-hole variance in the tapped metal): mount_cbore_h = rim_height - shank_length + engagement = 16 - 12.6 + 2.5 = 5.9. Not yet re-test-fit at this depth.

/* [Adjustable tuning masses] */
// A ring of pockets sized for M8 hardware (bolt + nut), exactly like the
// charleslabs tuning method. Add/remove bolts symmetrically to trim inertia
// and balance empirically (see Open questions in docs/reaction-wheel.md).
tuning_enable       = true;
tuning_count        = 6;     // number of pockets around the rim (use an even count for easy balancing)
tuning_bore_d       = 8.5;   // through-hole for M8 (mm)
tuning_pcd          = 90;    // pitch-circle diameter the tuning holes sit on (mm). Keep inside the rim.

/* [CFS multi-material color pattern] */
// Alternating orange/black wedges on the top (non-motor, visible) face only
// -- a thin cap, not full rim height -- so the "is it spinning" visual comes
// from far fewer filament swaps. Full-height wedges would mean a swap at
// every wedge boundary on every layer (~320 swaps at 0.2mm layers over the
// full 16mm rim_height); capped at 3mm that drops to ~60. Base color (all
// material below the cap, plus the "black" wedges within the cap) prints in
// one continuous object; "orange" is a second object for the other wedges.
// Import both STLs into OrcaSlicer at the same origin, assign to different
// CFS filament slots.
color_segments      = 4;     // alternating wedge count (even number). 4 = 90 deg wedges, fewer per-layer swaps.
color_cap_height     = 3;    // mm of color pattern at the top (visible, non-motor) face. Rest of rim_height prints as the base/black object.

/* [Quality] */
$fn                 = 160;

// ---------------------------------------------------------------------------
module rim() {
    difference() {
        cylinder(h = rim_height, d = wheel_od);
        translate([0,0,-1])
            cylinder(h = rim_height + 2, d = wheel_od - 2*rim_width);
    }
}

module web() {
    cylinder(h = web_height, d = wheel_od - 2*rim_width + 1); // +1 to fuse into rim
}

module hub() {
    cylinder(h = rim_height, d = hub_d);
}

module mount_holes() {
    for (i = [0 : mount_bolt_count - 1]) {
        ang = i * 360 / mount_bolt_count;
        translate([mount_bolt_circle_d/2 * cos(ang),
                   mount_bolt_circle_d/2 * sin(ang), 0]) {
            // through clearance hole
            translate([0,0,-1]) cylinder(h = rim_height + 2, d = mount_bolt_d);
            // counterbore from the top (non-motor) side
            translate([0,0,rim_height - mount_cbore_h])
                cylinder(h = mount_cbore_h + 1, d = mount_cbore_d);
        }
    }
}

module shaft_clearance() {
    // plain through-bore over the recessed register on the rotor cap --
    // nothing protrudes into this face, so no stepped pocket is needed.
    translate([0,0,-1]) cylinder(h = rim_height + 2, d = boss_clear_d);
}

module tuning_holes() {
    if (tuning_enable)
        for (i = [0 : tuning_count - 1]) {
            ang = i * 360 / tuning_count;
            translate([tuning_pcd/2 * cos(ang), tuning_pcd/2 * sin(ang), -1])
                cylinder(h = rim_height + 2, d = tuning_bore_d);
        }
}

module flywheel() {
    difference() {
        union() {
            rim();
            web();
            hub();
        }
        shaft_clearance();
        mount_holes();
        tuning_holes();
    }
}

// Angular wedge mask from a0 to a1 degrees, radius r, height h, at the given
// z offset. Follows the arc with intermediate points so it never chords
// inward of the flywheel's actual radius, regardless of wedge angle.
module pie_mask(a0, a1, r, h, z0, steps = 8) {
    pts = concat([[0, 0]],
                 [for (i = [0 : steps]) let(a = a0 + (a1 - a0) * i / steps) [r * cos(a), r * sin(a)]]);
    translate([0, 0, z0]) linear_extrude(height = h) polygon(pts);
}

module color_cap(parity) {
    // parity 0 = wedge indices 0,2,4... ; parity 1 = wedge indices 1,3,5...
    // NOTE: radius arg is wheel_od/2 (wheel_od is diameter) -- previously
    // passed wheel_od directly (2x too large). Harmless in practice since
    // the intersection() in flywheel_orange() below clips it back to the
    // real flywheel radius either way, but fixed 2026-08-10 for correctness.
    union()
        for (i = [0 : color_segments - 1])
            if (i % 2 == parity)
                pie_mask(i * 360 / color_segments, (i + 1) * 360 / color_segments,
                         wheel_od/2, color_cap_height + 1, rim_height - color_cap_height);
}

module flywheel_orange() {
    intersection() {
        flywheel();
        color_cap(0);
    }
}

module flywheel_black() {
    difference() {
        flywheel();
        flywheel_orange();
    }
}

// Quarter-hub test coupon: a 90deg wedge centered on mount hole 0 (ang=0 in
// mount_holes()), so it carries one full through-hole + counterbore intact
// for a real screw dry-fit -- fast iteration on mount_cbore_h without a full
// ~10h print. Wedge is wide enough (90deg > 360/mount_bolt_count = 90deg
// exactly) to just contain the one hole; centered so there's margin on both
// sides of it.
wedge_width = 90;

module quarter_hub() {
    intersection() {
        flywheel();
        pie_mask(-wedge_width/2, wedge_width/2, wheel_od/2, rim_height + 2, -1);
    }
}

// Color-swap test coupon: intersects the same quarter-wedge mask with the
// orange/black split instead of the full flywheel. wedge_width=90 straddles
// the color boundary at angle 0 (wedge i=3, black, spans 270-360; wedge i=0,
// orange, spans 0-90), so this small pair carries one real color transition
// -- enough to test whether the CFS toolhead swap actually triggers and
// shows up, without betting another ~10h print on it. Import both STLs at
// the SAME origin (0,0) in the slicer, same as the full orange/black pair --
// if the slicer's auto-arrange moves them apart, you'll get two separate
// single-color parts instead of one two-color part, and this test won't
// tell you anything useful.
module quarter_orange() {
    intersection() {
        quarter_hub();
        color_cap(0);
    }
}

// Mirrors flywheel_black()'s own definition (everything else, minus the
// orange sliver) rather than just the opposite-parity cap alone -- this
// keeps the coupon's black body a solid full-height chunk like the real
// print's black object, not a second disconnected thin shell, and exercises
// the same "mostly-black-then-swap-near-the-top" toolpath the full print
// actually needs.
module quarter_black() {
    difference() {
        quarter_hub();
        quarter_orange();
    }
}

/* [Render selection] */
// "full" | "orange" | "black" | "quarter" | "quarter_orange" | "quarter_black"
// -- which body this render produces. Render orange and black separately
// (openscad -D 'render_part="orange"' ...) for the two CFS multi-material
// STLs; "quarter" for the fast mount-hole test coupon; "quarter_orange" /
// "quarter_black" for the fast color-swap test coupon pair; "full" (default)
// renders the single-color part as before.
render_part = "full";

if (render_part == "orange") flywheel_orange();
else if (render_part == "black") flywheel_black();
else if (render_part == "quarter") quarter_hub();
else if (render_part == "quarter_orange") quarter_orange();
else if (render_part == "quarter_black") quarter_black();
else flywheel();

// ---------------------------------------------------------------------------
// Rough inertia sanity check (PLA ~1.24 g/cm^3):
//   This rim-loaded geometry lands ~120-180 g and I ~= 1.5e-4 .. 2.5e-4 kg*m^2
//   before tuning masses. Each M8x20 bolt+nut (~12 g) at the 45 mm tuning
//   radius adds ~2.4e-5 kg*m^2. Measure and tune empirically -- the build doc
//   open question on flywheel sizing stays open until bench-measured.
// Print notes: PLA fine for the demonstrator; PETG if it sees heat near the
//   motor. 50-60% infill (or solid rim via 6+ perimeters) to keep mass in the
//   rim. Print web-side down; no supports needed with the counterbores up.
// ---------------------------------------------------------------------------
