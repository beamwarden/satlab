// ---------------------------------------------------------------------------
// Test-print coupon for the satlab reaction-wheel flywheel.
//
// Fast (~10 min) validation print. Confirms the printer is healthy AND that
// the hole dimensions used in flywheel_gm4108h.scad actually fit real
// hardware before committing to the full 2-hour flywheel:
//   - M8 through-hole (tuning-mass bolt)  -> should pass an M8 bolt cleanly
//   - M3 clearance + counterbore (rotor mount) -> M3 screw slides, head sits flush
// It also gives you a single-wall + dimension check (the coupon should
// measure 40.0 x 20.0 x 6.0 mm on calipers).
// ---------------------------------------------------------------------------

len   = 40;
wid   = 20;
thk   = 6;

m8_d        = 8.5;   // matches tuning_bore_d in flywheel_gm4108h.scad
m3_d        = 3.4;   // matches mount_bolt_d
m3_cbore_d  = 6.5;   // matches mount_cbore_d
m3_cbore_h  = 3;     // matches mount_cbore_h

$fn = 96;

difference() {
    cube([len, wid, thk]);

    // M8 tuning-mass hole (left)
    translate([12, wid/2, -1]) cylinder(h = thk + 2, d = m8_d);

    // M3 mount hole with top counterbore (right)
    translate([28, wid/2, -1]) cylinder(h = thk + 2, d = m3_d);
    translate([28, wid/2, thk - m3_cbore_h]) cylinder(h = m3_cbore_h + 1, d = m3_cbore_d);
}
