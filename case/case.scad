// =====================================================================
// Meeting Monitor - 3D Printable Case (parametric, OpenSCAD)
// Desk-stand style, two parts:
//   1) front_housing - front face (2x4 module windows) FUSED with the
//      side/top/bottom walls as a single continuous shell (no seam)
//   2) back_panel - removable lid: OLED, encoder, buttons, buzzer,
//      USB-C, power switch
// =====================================================================
// PRINT NOTE: FC-16 mounting-hole positions vary slightly between
// manufacturers. Verify hole_inset against your actual boards before
// printing - adjust the single variable below if needed.

// ---------- Module / array dimensions ----------
module_size      = 32;     // FC-16 PCB is ~32x32mm
module_gap_x     = 1;      // gap between modules within a row (chained, tight)
row_gap_y        = 6;      // gap between row 1 and row 2 (visual separation)
cols             = 4;
rows             = 2;

array_w = cols * module_size + (cols - 1) * module_gap_x;   // ~131mm
array_h = rows * module_size + row_gap_y;                    // ~70mm

// FC-16 mounting holes: 4 corners, inset from PCB edge (adjust if your
// boards differ - common value is ~2mm inset, M2.5/M3 clearance hole)
hole_inset   = 2;
hole_dia     = 3.2;   // M3 clearance

// LED viewing window per module (slightly smaller than PCB so the wall
// overlaps mounting tabs / solder points at the edge)
window_margin = 2;
window_w = module_size - 2 * window_margin;
window_h = module_size - 2 * window_margin;

// ---------- Housing dimensions ----------
plate_thickness   = 3;        // front-face / back-panel wall thickness
frame_border      = 8;        // border around the array on the front face
faceplate_w = array_w + 2 * frame_border;
faceplate_h = array_h + 2 * frame_border;

tilt_angle   = 20;            // desk-stand tilt, degrees back from vertical

cavity_depth      = 42;       // usable internal depth for Pico W, battery, boost, wiring
total_depth = cavity_depth + plate_thickness;  // overall housing depth incl. front face
wall_thickness    = 2.4;      // side/top/bottom wall thickness

// ---------- Back panel cutouts ----------
oled_w = 27.5;  oled_h = 27.5;       // 0.96" OLED active/board cutout window
encoder_hole_dia = 7.2;              // EC11 shaft clearance
btn_hole_dia = 7;
buzzer_hole_dia = 9;
usb_c_w = 9.5; usb_c_h = 4;
power_switch_w = 10; power_switch_h = 5;

// ---------- Rounding / organic shaping ----------
plate_corner_r   = 16;   // corner fillet on the back panel footprint
enclosure_edge_r = 11;   // fillet radius on all 12 edges of the housing shell
leg_round_r      = 9;    // roundness of the stand-leg gussets
back_lip_clearance = 0.25; // printable clearance between back panel and housing opening

// rounded rectangle (2D)
module rounded_rect(w, h, r) {
    hull() {
        for (cx = [r, w - r]) {
            for (cy = [r, h - r]) {
                translate([cx, cy]) circle(r = r, $fn = 48);
            }
        }
    }
}

module rounded_plate(w, h, th, r) {
    linear_extrude(height = th) rounded_rect(w, h, r);
}

// fully rounded box (all 12 edges filleted), outer bounding box = [w,h,d]
module rounded_box(w, h, d, r) {
    hull() {
        for (cx = [r, w - r]) {
            for (cy = [r, h - r]) {
                for (cz = [r, d - r]) {
                    translate([cx, cy, cz]) sphere(r = r, $fn = 32);
                }
            }
        }
    }
}

module boss(screw_r) {
    difference() {
        cylinder(d=7, h=6, $fn=24);
        cylinder(d=screw_r*2, h=7, $fn=24);
    }
}

// =====================================================================
// FRONT HOUSING - single fused shell: side/top/bottom walls + front
// face with module windows, all printed as one part (no seam).
// z=0 is the open BACK (back_panel attaches here); z=total_depth is
// the FRONT outer face where the 8 matrices mount.
// =====================================================================
module front_housing() {
    outer_w = faceplate_w;
    outer_h = faceplate_h;

    difference() {
        rounded_box(outer_w, outer_h, total_depth, enclosure_edge_r);

        // hollow out everything except the side walls + the front face
        // slab (thickness = plate_thickness). Cavity is inset by
        // wall_thickness in x/y, and open past the back (z<=0) so the
        // back stays fully accessible.
        translate([wall_thickness, wall_thickness, -1])
            rounded_box(outer_w - 2*wall_thickness, outer_h - 2*wall_thickness,
                        cavity_depth + 1, max(1, enclosure_edge_r - wall_thickness));

        // 8 viewing windows + 32 mounting holes, cut straight through
        // the integrated front face
        for (r = [0:rows-1]) {
            for (c = [0:cols-1]) {
                x = frame_border + c * (module_size + module_gap_x);
                y = frame_border + r * (module_size + row_gap_y);

                translate([x + window_margin, y + window_margin, total_depth - plate_thickness - 1])
                    linear_extrude(height = plate_thickness + 2)
                        rounded_rect(window_w, window_h, 2.5);

                for (hx = [hole_inset, module_size - hole_inset]) {
                    for (hy = [hole_inset, module_size - hole_inset]) {
                        translate([x + hx, y + hy, total_depth - plate_thickness - 1])
                            cylinder(d=hole_dia, h=plate_thickness + 2, $fn=24);
                    }
                }
            }
        }
    }

    // module mounting standoffs, printed on the INSIDE of the front
    // face, protruding back into the cavity
    for (r = [0:rows-1]) {
        for (c = [0:cols-1]) {
            x = frame_border + c * (module_size + module_gap_x);
            y = frame_border + r * (module_size + row_gap_y);
            for (hx = [hole_inset, module_size - hole_inset]) {
                for (hy = [hole_inset, module_size - hole_inset]) {
                    translate([x + hx, y + hy, total_depth - plate_thickness])
                        rotate([180,0,0])
                            difference() {
                                cylinder(d=6, h=4, $fn=24);
                                translate([0,0,-0.5]) cylinder(d=2.6, h=5, $fn=24); // pilot hole
                            }
                }
            }
        }
    }

    // internal mounting bosses for Pico W (approx 21x51mm board),
    // protruding from the inside of the front face into the cavity
    translate([15, 15, total_depth - plate_thickness])
        rotate([180,0,0]) boss(2.5);
    translate([15, 55, total_depth - plate_thickness])
        rotate([180,0,0]) boss(2.5);

    // 4 corner standoff posts near the open back rim, for back_panel
    // screws (back_panel becomes a removable lid)
    for (cx = [enclosure_edge_r + 4, outer_w - enclosure_edge_r - 4]) {
        for (cy = [enclosure_edge_r + 4, outer_h - enclosure_edge_r - 4]) {
            translate([cx, cy, wall_thickness])
                difference() {
                    cylinder(d=7, h=6, $fn=24);
                    cylinder(d=2.6, h=7, $fn=24); // self-tap pilot for M3
                }
        }
    }
}

// =====================================================================
// BACK PANEL (removable lid: OLED window, encoder, 2 buttons, buzzer
// hole, USB-C cutout, power switch cutout, + 4 screw clearance holes
// matching the standoff posts in front_housing)
// =====================================================================
module back_panel() {
    outer_w = faceplate_w;
    outer_h = faceplate_h;
    panel_w = outer_w - 2*back_lip_clearance;
    panel_h = outer_h - 2*back_lip_clearance;

    difference() {
        rounded_plate(panel_w, panel_h, plate_thickness, plate_corner_r);

        // OLED window, upper-center
        translate([panel_w/2 - oled_w/2, panel_h - 30, -1])
            cube([oled_w, oled_h, plate_thickness + 2]);

        // encoder, center
        translate([panel_w/2, panel_h/2, -1])
            cylinder(d=encoder_hole_dia, h=plate_thickness + 2, $fn=32);

        // two buttons either side of encoder
        translate([panel_w/2 - 25, panel_h/2, -1])
            cylinder(d=btn_hole_dia, h=plate_thickness + 2, $fn=24);
        translate([panel_w/2 + 25, panel_h/2, -1])
            cylinder(d=btn_hole_dia, h=plate_thickness + 2, $fn=24);

        // buzzer hole, lower-left
        translate([20, 20, -1])
            cylinder(d=buzzer_hole_dia, h=plate_thickness + 2, $fn=24);

        // USB-C charge port, bottom edge center
        translate([panel_w/2 - usb_c_w/2, -1, plate_thickness/2 - usb_c_h/2])
            cube([usb_c_w, plate_thickness + 2, usb_c_h]);

        // power slide switch, bottom-right
        translate([panel_w - 25, -1, plate_thickness/2 - power_switch_h/2])
            cube([power_switch_w, plate_thickness + 2, power_switch_h]);

        // 4 screw clearance holes matching front_housing standoff posts
        for (cx = [enclosure_edge_r + 4, outer_w - enclosure_edge_r - 4]) {
            for (cy = [enclosure_edge_r + 4, outer_h - enclosure_edge_r - 4]) {
                translate([cx - back_lip_clearance, cy - back_lip_clearance, -1])
                    cylinder(d=3.2, h=plate_thickness + 2, $fn=24);
            }
        }
    }
}

// =====================================================================
// STAND LEGS (rounded gussets giving the desk-stand tilt)
// =====================================================================
module stand_leg(h, base_depth) {
    linear_extrude(height = wall_thickness)
        hull() {
            translate([leg_round_r, leg_round_r]) circle(r = leg_round_r, $fn = 32);
            translate([base_depth - leg_round_r, leg_round_r]) circle(r = leg_round_r, $fn = 32);
            translate([leg_round_r, h - leg_round_r]) circle(r = leg_round_r, $fn = 32);
        }
}

module stand_assembly() {
    leg_height = total_depth * sin(tilt_angle) + 20;
    leg_depth  = total_depth * cos(tilt_angle) + 15;

    translate([0, 0, 0])
        rotate([90,0,90])
            stand_leg(leg_height, leg_depth);
    translate([faceplate_w - wall_thickness, 0, 0])
        rotate([90,0,90])
            stand_leg(leg_height, leg_depth);
}

// =====================================================================
// PREVIEW / EXPORT
// =====================================================================

PRINT_LAYOUT = false;
EXPORT_PART = 0; // 0=layout preview, 1=front_housing, 2=back_panel

if (EXPORT_PART == 1) {
    front_housing();
} else if (EXPORT_PART == 2) {
    back_panel();
} else if (PRINT_LAYOUT) {
    // lay out for slicing - each part printed separately
    translate([0, 0, 0]) front_housing();
    translate([faceplate_w + 20, 0, 0]) back_panel();
} else {
    // assembled preview: housing tilted back, back panel closing the
    // open rear, legs supporting the tilt
    rotate([tilt_angle, 0, 0]) {
        front_housing();
        translate([back_lip_clearance, back_lip_clearance, -plate_thickness])
            back_panel();
    }
    stand_assembly();
}
