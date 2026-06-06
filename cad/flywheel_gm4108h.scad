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
// !!! VERIFY BEFORE PRINTING !!!
// The GM4108H rotor bolt pattern below is a PLACEHOLDER. Measure your motor's
// rotating bell: the mounting-hole bolt-circle diameter, hole count, hole
// size, and the diameter/height of the center boss. Set the `mount_*` and
// `boss_*` parameters to your measured values. The flywheel bolts to the
// ROTOR (the part that spins), not the stator and not the shaft -- the shaft
// end is reserved for the AS5600 encoder magnet.
// ---------------------------------------------------------------------------

/* [Wheel] */
wheel_od            = 120;   // outer diameter (mm). 120 keeps it under a 130 bed corner-to-corner and under the charleslabs 130 disk.
rim_width           = 12;    // radial thickness of the heavy rim (mm)
rim_height          = 16;    // axial height of the rim (mm) -- matches charleslabs flywheel thickness
web_height          = 4;     // thickness of the central web connecting hub to rim (mm)

/* [Hub / motor interface] */
boss_clear_d        = 11;    // bore to clear the 10 mm hollow shaft / rotor boss (mm). >10 so the wheel never touches the shaft.
boss_clear_h        = 6;     // depth of the shaft/boss clearance recess from the motor side (mm)
hub_d               = 34;    // diameter of the solid hub region around the bolt circle (mm)

mount_bolt_circle_d = 25;    // PLACEHOLDER: GM4108H rotor mounting bolt-circle diameter (mm) -- MEASURE
mount_bolt_count    = 3;     // PLACEHOLDER: number of rotor mounting holes -- MEASURE
mount_bolt_d        = 3.4;   // clearance hole for M3 (mm). Change if your motor uses M2.5.
mount_cbore_d       = 6.5;   // counterbore so the screw head sits flush/below the web (mm)
mount_cbore_h       = 3;     // counterbore depth (mm)

/* [Adjustable tuning masses] */
// A ring of pockets sized for M8 hardware (bolt + nut), exactly like the
// charleslabs tuning method. Add/remove bolts symmetrically to trim inertia
// and balance empirically (see Open questions in docs/reaction-wheel.md).
tuning_enable       = true;
tuning_count        = 6;     // number of pockets around the rim (use an even count for easy balancing)
tuning_bore_d       = 8.5;   // through-hole for M8 (mm)
tuning_pcd          = 90;    // pitch-circle diameter the tuning holes sit on (mm). Keep inside the rim.

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
    // recess on the motor side so the wheel clears the shaft/boss
    translate([0,0,-1]) cylinder(h = boss_clear_h + 1, d = boss_clear_d + 2); // boss pocket
    translate([0,0,-1]) cylinder(h = rim_height + 2, d = boss_clear_d);        // through bore for shaft
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

flywheel();

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
