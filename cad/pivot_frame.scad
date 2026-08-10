// ---------------------------------------------------------------------------
// Pivot frame for the satlab single-axis reaction-wheel demonstrator
//
// CAD heritage: charleslabs.fr reaction wheel (gaspode-wonder/reaction_wheel).
//   Their "base" (70x70x20mm) and "satellite disk" (130 OD x 29) are the
//   dimensional starting points -- see docs/reaction-wheel.md. Their base is
//   battery/untethered; ours adds the hollow-axle wire pass-through so the
//   platform electronics (Uno Q, SimpleFOC Shield, BNO055, LSM6DSOX) can talk
//   to the RPi/Uno R3 on the base without a slip ring (see docs "Platform
//   wire routing").
//
// Kinematics: the PIVOT AXLE IS STATIONARY -- it does not rotate. The
// PLATFORM rotates freely around it on two stacked 608ZZ bearings pressed
// into the platform's hub barrel. The base only needs to hold the axle
// rigidly (non-rotating); it gets a bearing pocket too (not for rotation,
// just as a precision-bore bushing/anchor -- a plain drilled hole would work
// electrically/mechanically the same, but reusing the 608ZZ here means only
// one bearing pocket diameter to get right, and it matches the "bearings at
// each end of the frame" language in docs/reaction-wheel.md). Confirm on the
// bench whether the press-fit alone stops the axle from creeping in the base
// pocket, or whether a dab of thread-lock/epoxy is needed once fit is
// validated -- flagged as open, not yet bench-tested.
//
// Two printable bodies, selected via render_part at the bottom:
//   "base"     -- fixed foot, anchors the axle, wires exit sideways to the
//                 RPi/Uno R3 side of the build.
//   "platform" -- rotating disk, hub rides the axle on two bearings, wires
//                 exit the top of the hollow axle into a cavity here.
//
// Bearing/axle dims are catalog/purchased-part numbers (608ZZ is a standard
// skate bearing; the K&S #9807 axle tube is bought to an 8mm OD spec), not
// physical measurements off a specific unit -- lower risk than the motor
// interface, but still verify the press-fit tightness on a test print before
// committing to the full part (see bearing_fit_clearance below).
// ---------------------------------------------------------------------------

/* [Axle / bearing interface] */
axle_od               = 8;     // K&S #9807 tube OD (mm) -- also matches 608ZZ bore
axle_clear_d          = 8.4;   // running clearance bore for sections where the axle passes through but isn't press-fit (mm)
bearing_od            = 22;    // 608ZZ outer diameter (mm)
bearing_width         = 7;     // 608ZZ width (mm)
bearing_fit_clearance = -0.15; // undersize applied to the bearing pocket bore for an FDM press-fit (mm). Negative = pocket printed smaller than bearing_od. Verify on a test coupon first -- printers/nozzles vary (see the flywheel's F00528 note on this printer's quirks); loosen toward 0 if the bearing won't seat, tighten if it spins loose in the pocket.
bearing_pocket_d      = bearing_od + bearing_fit_clearance;

/* [Base] */
base_w      = 70;    // footprint (mm), charleslabs heritage
base_d      = 70;
base_h      = 18;    // enough for one bearing pocket (7mm) + floor + wire channel headroom
base_pocket_depth = bearing_width + 1; // press-fit pocket depth, +1mm so the bearing seats below the top face
wire_channel_w = 8;   // side-exit channel for the 4 platform wires (mm)
wire_channel_h = 5;
mount_hole_d   = 3.4; // M3 clearance, corner mounting to a larger plate/desk bracket (optional)
mount_inset    = 6;   // corner hole inset from each edge (mm)

/* [Platform] */
platform_od     = 130;  // charleslabs "satellite disk" heritage OD (mm)
platform_thick  = 6;    // deck thickness (mm)
hub_od          = bearing_od + 8;  // hub barrel wall thickness around the bearings (mm)
hub_height      = 32;   // vertical span between the two stacked bearings -- taller = more tip stability on the axle (mm)
wire_cavity_d   = 16;   // pocket at the top of the hub where axle wires emerge before routing out to the platform deck (mm)
wire_cavity_h   = 8;
perim_hole_d    = 3.4;  // M3 tie-down holes around the platform perimeter for zip-tie/adhesive-mounting electronics (generic -- Uno Q / BNO055 / LSM6DSOX footprints not yet confirmed, see docs open questions)
perim_hole_count = 8;
perim_hole_pcd  = platform_od - 20;

/* [Quality] */
$fn = 120;

// ---------------------------------------------------------------------------
module base_bracket() {
    difference() {
        // foot block
        translate([-base_w/2, -base_d/2, 0])
            cube([base_w, base_d, base_h]);

        // axle anchor: press-fit bearing pocket at the top, running clearance
        // bore the rest of the way through
        translate([0, 0, base_h - base_pocket_depth])
            cylinder(h = base_pocket_depth + 1, d = bearing_pocket_d);
        translate([0, 0, -1])
            cylinder(h = base_h - base_pocket_depth + 1, d = axle_clear_d);

        // wire exit: horizontal channel from the axle bore out to +Y face,
        // positioned mid-height so it clears the bearing pocket above it
        translate([-wire_channel_w/2, 0, base_h/2 - wire_channel_h/2])
            cube([wire_channel_w, base_d/2 + 1, wire_channel_h]);

        // corner mounting holes
        for (sx = [-1, 1]) for (sy = [-1, 1])
            translate([sx * (base_w/2 - mount_inset), sy * (base_d/2 - mount_inset), -1])
                cylinder(h = base_h + 2, d = mount_hole_d);
    }
}

module platform() {
    difference() {
        union() {
            // deck
            cylinder(h = platform_thick, d = platform_od);
            // hub barrel, rises from the deck to carry the two bearings
            cylinder(h = hub_height, d = hub_od);
        }

        // two bearing pockets, one at the hub base (through the deck) and
        // one at the hub top -- axle runs clearance-fit between them
        translate([0, 0, -1])
            cylinder(h = bearing_width + 1, d = bearing_pocket_d);
        translate([0, 0, hub_height - bearing_width])
            cylinder(h = bearing_width + 1, d = bearing_pocket_d);
        translate([0, 0, bearing_width - 0.5])
            cylinder(h = hub_height - 2*bearing_width + 1, d = axle_clear_d);

        // wire cavity at the hub top -- axle's hollow bore opens up here so
        // wires can be dressed sideways onto the deck
        translate([0, 0, hub_height - wire_cavity_h])
            cylinder(h = wire_cavity_h + 1, d = wire_cavity_d);

        // generic perimeter tie-down holes
        for (i = [0 : perim_hole_count - 1]) {
            ang = i * 360 / perim_hole_count;
            translate([perim_hole_pcd/2 * cos(ang), perim_hole_pcd/2 * sin(ang), -1])
                cylinder(h = platform_thick + 2, d = perim_hole_d);
        }
    }
}

// Bearing-pocket test coupon: just enough of the hub barrel to contain one
// full press-fit pocket, for a fast print-and-check of bearing_fit_clearance
// before committing to the full ~32mm hub (platform()) or the full base
// block. Same fast-iteration approach that caught the flywheel's mount-hole
// engagement problem in a 24-minute coupon instead of a 10+ hour full print.
bearing_test_h = bearing_width + 6; // pocket depth + a few mm of margin below it

module bearing_test() {
    difference() {
        cylinder(h = bearing_test_h, d = hub_od);
        translate([0, 0, bearing_test_h - bearing_width])
            cylinder(h = bearing_width + 1, d = bearing_pocket_d);
        translate([0, 0, -1])
            cylinder(h = bearing_test_h - bearing_width + 1, d = axle_clear_d);
    }
}

/* [Render selection] */
render_part = "base"; // "base" | "platform" | "bearing_test"

if (render_part == "base") base_bracket();
else if (render_part == "platform") platform();
else bearing_test();

// ---------------------------------------------------------------------------
// Print notes: PLA fine for the demonstrator. Print base_bracket() with the
// bearing-pocket face up, no supports needed. Print platform() hub-up (deck
// down) so the bearing pockets print without supports; the wire cavity at
// the hub top will need light supports or a bridge -- check in slicer preview.
//
// Not yet physically test-fit. Bearing pocket clearance (bearing_fit_clearance)
// is a first-pass guess consistent with typical FDM press-fits, not measured
// on this printer -- print a short test sleeve (a few mm of hub_od/pocket
// geometry) before committing to a full-height print, same lesson as the
// flywheel's speed-tuning fix.
// ---------------------------------------------------------------------------
