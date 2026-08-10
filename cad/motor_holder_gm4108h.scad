// ---------------------------------------------------------------------------
// Motor holder for the satlab reaction-wheel demonstrator (GM4108H-120T)
//
// Bolts to the motor's STATIONARY base plate (the wire-exit face, opposite
// the rotating bell/flywheel end -- see docs/reaction-wheel.md "Encoder
// mounting" for the spin-test that identified which face is which). Sits
// flat on the pivot frame's platform() deck with the motor standing
// upright: base plate down, flywheel up, spinning in a horizontal plane
// well above the deck. No standoff height needed beyond the motor's own
// body length for flywheel clearance.
//
// MEASURED 2026-08-09/10 off the physical motor's base plate:
//   - Base OD: 47.05mm (matches the separately-measured rotor bell OD of
//     47.13mm -- both ends of the can are the same diameter)
//   - Base plate thickness: ~4.59mm
//   - 4 mounting holes, clean SQUARE pattern, 26.32mm side (trusted reading;
//     a diagonal reading of 38.26mm was ~3% off the sqrt(2) relationship,
//     attributed to parallax measuring across a round part, not a real
//     asymmetry)
//   - Mounting hole diameter: 2.3mm (the motor's own screw packet threads
//     into these -- not yet confirmed whether they're tapped directly or
//     the shaft passes through to a captured nut, doesn't change this
//     holder's design either way, just needs aligned clearance holes)
//   - Center hex nut (shaft lock nut): 12.8mm across-flats, stands ~1mm
//     proud of the base plate face
//
// NOT YET INCLUDED: an AS5600 standoff arm reaching the rotating bell's
// flywheel face at the OPPOSITE end of the motor, per docs/reaction-wheel.md
// "Motor holder" section. That needs the motor's axial body length, which
// hasn't been calipered (only the published 32.3mm datasheet figure, and
// this project has already been burned twice by trusting this motor's
// published specs over physical measurement -- see the flywheel's
// mount-hole and encoder-face corrections). Measure motor length before
// extending this design; this pass is the mounting bracket only.
//
// Design: an open skeletal cross (not a solid disk) -- four arms from a
// center hub out to four corner bosses at the measured bolt pattern,
// leaving gaps between the arms so the 3-wire phase harness can exit in
// whatever direction it actually comes off the base plate, without needing
// to measure that angle.
// ---------------------------------------------------------------------------

/* [Motor interface -- measured] */
base_od           = 47.05; // motor base plate OD (mm)
hole_pattern_side = 26.32; // square hole pattern side length (mm)
hole_d_motor      = 2.3;   // MEASURED hole diameter on the motor itself (mm)
hole_clearance    = 0.3;   // added for a free fit + FDM shrinkage, same convention as the flywheel's mount_bolt_d
hole_d            = hole_d_motor + hole_clearance;
hex_af            = 12.8;  // hex lock-nut across-flats (mm)
hex_proud_h       = 1.0;   // how far the nut stands proud of the base plate (mm)

/* [Bracket geometry] */
plate_thick   = 5;                     // overall bracket thickness (mm)
hex_pocket_d  = hex_af + 2.5;          // generous round clearance over the hex (not hex-shaped -- nut orientation isn't controlled when bolted on)
hex_pocket_h  = hex_proud_h + 1.5;     // recess depth: proud height + margin, so the bracket's flat face registers on the true base-plate surface, not the nut
hub_d         = 20;                    // center hub diameter (mm)
boss_d        = 9;                     // corner boss diameter, around each mounting hole (mm)
arm_w         = 7;                     // connecting arm width (mm)

/* [Platform mounting tabs] */
tab_hole_d = 3.4; // M3 clearance, zip-tie or screw to the platform deck's generic tie-down holes
tab_len    = 8;   // how far each tab extends past its corner boss (mm)

/* [Quality] */
$fn = 96;

// ---------------------------------------------------------------------------
hole_positions = [
    [ hole_pattern_side/2,  hole_pattern_side/2],
    [-hole_pattern_side/2,  hole_pattern_side/2],
    [-hole_pattern_side/2, -hole_pattern_side/2],
    [ hole_pattern_side/2, -hole_pattern_side/2],
];

module corner_boss(pos) {
    translate(pos) cylinder(h = plate_thick, d = boss_d);
}

module corner_hole(pos) {
    translate([pos.x, pos.y, -1]) cylinder(h = plate_thick + 2, d = hole_d);
}

module mounting_tab(pos) {
    // extends radially outward from each corner boss, away from center
    dir = pos / norm(pos);
    tab_center = pos + dir * (boss_d/2 + tab_len/2);
    translate([tab_center.x, tab_center.y, 0])
        rotate([0, 0, atan2(dir.y, dir.x)])
        linear_extrude(height = plate_thick)
            square([tab_len + boss_d/2, arm_w], center = true);
}

module tab_hole(pos) {
    dir = pos / norm(pos);
    hole_center = pos + dir * (boss_d/2 + tab_len - 2);
    translate([hole_center.x, hole_center.y, -1])
        cylinder(h = plate_thick + 2, d = tab_hole_d);
}

module holder() {
    difference() {
        union() {
            cylinder(h = plate_thick, d = hub_d); // center hub
            for (pos = hole_positions) {
                corner_boss(pos);
                // connecting arm from hub to this boss
                dir = pos / norm(pos);
                mid = pos / 2;
                rotate([0, 0, atan2(pos.y, pos.x)])
                    translate([0, -arm_w/2, 0])
                    cube([norm(pos), arm_w, plate_thick]);
            }
            // two opposite mounting tabs (indices 0 and 2 are diagonal corners)
            mounting_tab(hole_positions[0]);
            mounting_tab(hole_positions[2]);
        }

        // hex nut clearance pocket, centered, recessed from the motor-facing
        // (top) side so the bracket's flat face bottoms out on the real
        // base-plate surface, not on the proud nut
        translate([0, 0, plate_thick - hex_pocket_h])
            cylinder(h = hex_pocket_h + 1, d = hex_pocket_d);

        for (pos = hole_positions) corner_hole(pos);
        tab_hole(hole_positions[0]);
        tab_hole(hole_positions[2]);
    }
}

holder();

// ---------------------------------------------------------------------------
// Print notes: PLA fine for the demonstrator. Print flat, motor-facing side
// up (matches the hex pocket recess direction above) -- no supports needed,
// it's a flat bracket. Orient either diagonal along the bed's long axis if
// bed adhesion on the thin arms is a concern; it's a small, fast print.
//
// Not yet physically test-fit -- hole_clearance (0.3mm) follows the same
// convention that worked for the flywheel's mount holes, but this hasn't
// been verified on this printer for THIS hole size. Dry-fit with the actual
// mounting screws before committing to final assembly.
// ---------------------------------------------------------------------------
