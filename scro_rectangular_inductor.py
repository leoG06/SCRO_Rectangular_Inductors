#!/usr/bin/env python3
"""
SCRO Two-Layer Stacked Rectangular Inductor — Parametric Mask Generator
========================================================================
Generates the GDSII layout mask for the SCRO two-layer stacked square inductor.
Both metal layers contain matching spiral coils created by a loop of progressively
shorter lines. The spirals connect at the center via, and both probe pads connect
to the outer terminals of the inductor.

Layers & Photoresist Polarities (Sentaurus SProcess / NRF Tapeout #2):
  1. SI_SUB    (1/0) : Silicon wafer substrate boundary
  2. SI_ETCH   (2/0) : Mask 1 (M1_Align)   — AZ1512 (Positive PR, RIE Si etch)
  3. N_OX1     (3/0) : Mask 2 (M2_Active)  — AZ1512 (Positive PR, BOE field ox)
  4. NPLUS_SOG (4/0) : Mask 3 (M3_nplus)   — AZ1512 (Positive PR, BOE P-SOG)
  5. THIN_OX   (5/0) : Mask 4 (M4_Channel) — AZ1512 (Positive PR, BOE channel ox)
  6. OX2       (6/0) : Mask 5 (M5_Contact) — AZ1512 (Positive PR, BOE contact ox)
  7. METAL1    (7/0) : Mask 6 (M6_M1)      — AZ nLOF 2035 (Negative PR, Al liftoff)
  8. VIA       (8/0) : Mask 7 (M7_Vias)    — AZ1512 (Positive PR, BOE PVD SiO2 via)
  9. METAL2    (9/0) : Mask 8 (M8_M2)      — AZ nLOF 2035 (Negative PR, Al liftoff)
"""

import os
import pya

# =============================================================================
# PARAMETERS (in microns)
# =============================================================================
DEFAULT_D_OUT    = 400.0    # Outer dimension of inductor (um)
DEFAULT_W        = 10.0     # Line width / trace thickness (um)
DEFAULT_S        = 10.0     # Line spacing between turns (um)
DEFAULT_TURNS    = 9.0      # Number of turns
DEFAULT_PAD_SIZE = 100.0    # Probe pad dimension (um)
DEFAULT_PITCH    = 150.0    # Pad pitch center-to-center (um)
DEFAULT_MARGIN   = 50.0     # Die edge clearance margin (um)


def generate_spiral_points(d_out, w, s, n_turns):
    """
    Creates spiral centerline coordinates using a loop that produces
    progressively shorter lines.

    Each full turn consists of 4 orthogonal segments.
    Every half-turn (2 segments), the line length decreases by pitch p = w + s.
    """
    p = w + s
    num_segments = int(round(n_turns * 4))
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # Up, Right, Down, Left

    # Start w / 2 lower so the outer vertical segment extends down by half a wire width
    curr_x = -d_out / 2.0 + w / 2.0
    curr_y = -d_out / 2.0
    points = [(curr_x, curr_y)]

    # Loop creating shorter and shorter lines
    for k in range(num_segments):
        if k == 0:
            line_length = (d_out - w) + (w / 2.0)
        else:
            line_length = (d_out - w) - (k // 2) * p
        if line_length <= w:
            break
        dx, dy = directions[k % 4]
        curr_x += dx * line_length
        curr_y += dy * line_length
        points.append((curr_x, curr_y))

    # Inner tap connecting into center via contact
    points.append((0.0, 0.0))
    return points


def build_inductor_mask(d_out=DEFAULT_D_OUT,
                        w=DEFAULT_W,
                        s=DEFAULT_S,
                        n_turns=DEFAULT_TURNS,
                        pad_size=DEFAULT_PAD_SIZE,
                        pad_pitch=DEFAULT_PITCH,
                        margin=DEFAULT_MARGIN,
                        output_file=None):
    """
    Builds the two-layer stacked GDSII layout with the 9 SProcess layers
    and applies positive (AZ1512) and negative (AZ nLOF 2035) resist polarities.
    """
    if output_file is None:
        output_file = f"Inductors_GDSII/{d_out}um_rectangular_inductor.gds"

    scale = 1000  # Database unit conversion (1 um = 1000 dbu)

    layout = pya.Layout()
    layout.dbu = 0.001
    top_cell = layout.create_cell("SCRO_INDUCTOR")

    # Define the 9 explicit SProcess layers
    l_si_sub    = layout.layer(pya.LayerInfo(1, 0, "SI_SUB"))
    l_si_etch   = layout.layer(pya.LayerInfo(2, 0, "SI_ETCH"))
    l_n_ox1     = layout.layer(pya.LayerInfo(3, 0, "N_OX1"))
    l_nplus_sog = layout.layer(pya.LayerInfo(4, 0, "NPLUS_SOG"))
    l_thin_ox   = layout.layer(pya.LayerInfo(5, 0, "THIN_OX"))
    l_ox2       = layout.layer(pya.LayerInfo(6, 0, "OX2"))
    l_metal1    = layout.layer(pya.LayerInfo(7, 0, "METAL1"))
    l_via       = layout.layer(pya.LayerInfo(8, 0, "VIA"))
    l_metal2    = layout.layer(pya.LayerInfo(9, 0, "METAL2"))

    # Center coordinates
    cx, cy = 0.0, 0.0

    # Probe pad coordinates (placed below the inductor)
    p1_cx = cx - pad_pitch / 2.0
    p2_cx = cx + pad_pitch / 2.0
    pad_cy = cy - d_out / 2.0 - margin - pad_size / 2.0

    # Die substrate boundaries
    die_xmin = min(cx - d_out / 2.0, p1_cx - pad_size / 2.0) - margin
    die_xmax = max(cx + d_out / 2.0, p2_cx + pad_size / 2.0) + margin
    die_ymin = pad_cy - pad_size / 2.0 - margin
    die_ymax = cy + d_out / 2.0 + margin

    die_box = pya.Box(int(round(die_xmin * scale)), int(round(die_ymin * scale)),
                      int(round(die_xmax * scale)), int(round(die_ymax * scale)))

    # 1. SI_SUB: Silicon substrate boundary
    top_cell.shapes(l_si_sub).insert(die_box)

    # 2–6. FEOL Positive Photoresist Masks (AZ1512):
    # In SProcess positive polarity, drawn polygons define where AZ1512 photoresist
    # remains on the wafer to block RIE/BOE etching. Full die coverage protects the
    # silicon substrate and the 400 nm thermal field oxide beneath the inductor.
    for pos_feol_layer in (l_si_etch, l_n_ox1, l_nplus_sog, l_thin_ox, l_ox2):
        top_cell.shapes(pos_feol_layer).insert(die_box)

    # Generate spiral coordinates using the loop
    m2_pts = generate_spiral_points(d_out, w, s, n_turns)
    m1_pts = [(-x, y) for x, y in m2_pts]  # Matching bottom spiral

    # 7. METAL1 (Mask 6: M6_M1 — AZ nLOF 2035 Negative Photoresist Liftoff):
    # Drawn polygons define the liftoff trenches where Metal 1 remains.
    pya_m1_pts = [pya.Point(int(round(x * scale)), int(round(y * scale))) for x, y in m1_pts]
    top_cell.shapes(l_metal1).insert(pya.Path(pya_m1_pts, int(round(w * scale))).polygon())

    # 9. METAL2 (Mask 8: M8_M2 — AZ nLOF 2035 Negative Photoresist Liftoff):
    # Drawn polygons define the liftoff trenches where Metal 2 remains.
    pya_m2_pts = [pya.Point(int(round(x * scale)), int(round(y * scale))) for x, y in m2_pts]
    top_cell.shapes(l_metal2).insert(pya.Path(pya_m2_pts, int(round(w * scale))).polygon())

    # Center landing pads on both metal layers
    center_pad_w = max(30, w * 2.5)
    center_box = pya.Box(int(round((cx - center_pad_w / 2.0) * scale)), int(round((cy - center_pad_w / 2.0) * scale)),
                         int(round((cx + center_pad_w / 2.0) * scale)), int(round((cy + center_pad_w / 2.0) * scale)))
    top_cell.shapes(l_metal1).insert(center_box)
    top_cell.shapes(l_metal2).insert(center_box)

    # Probe Pad 1: Connected to the outer terminal of the top spiral (METAL2)
    # Probe wire extended left by w / 2 to overlap the full width of the top spiral
    p1_box = pya.Box(int(round((p1_cx - pad_size / 2.0) * scale)), int(round((pad_cy - pad_size / 2.0) * scale)),
                     int(round((p1_cx + pad_size / 2.0) * scale)), int(round((pad_cy + pad_size / 2.0) * scale)))
    top_cell.shapes(l_metal2).insert(p1_box)

    top_outer_x = m2_pts[0][0]
    top_outer_y = m2_pts[0][1] + (w / 2.0)
    lead1 = [
        pya.Point(int(round(p1_cx * scale)), int(round((pad_cy + pad_size / 2.0) * scale))),
        pya.Point(int(round(p1_cx * scale)), int(round(top_outer_y * scale))),
        pya.Point(int(round((top_outer_x - (w / 2.0)) * scale)), int(round(top_outer_y * scale)))
    ]
    top_cell.shapes(l_metal2).insert(pya.Path(lead1, int(round(w * scale))).polygon())

    # Probe Pad 2: Connected to the outer terminal of the bottom spiral (METAL1)
    # Probe wire extended right by w / 2 to overlap the full width of the bottom spiral
    p2_box = pya.Box(int(round((p2_cx - pad_size / 2.0) * scale)), int(round((pad_cy - pad_size / 2.0) * scale)),
                     int(round((p2_cx + pad_size / 2.0) * scale)), int(round((pad_cy + pad_size / 2.0) * scale)))
    top_cell.shapes(l_metal1).insert(p2_box)
    top_cell.shapes(l_metal2).insert(p2_box)  # Surface pad for probe needle contact

    bot_outer_x = m1_pts[0][0]
    bot_outer_y = m1_pts[0][1] + (w / 2.0)
    lead2 = [
        pya.Point(int(round(p2_cx * scale)), int(round((pad_cy + pad_size / 2.0) * scale))),
        pya.Point(int(round(p2_cx * scale)), int(round(bot_outer_y * scale))),
        pya.Point(int(round((bot_outer_x + (w / 2.0)) * scale)), int(round(bot_outer_y * scale)))
    ]
    top_cell.shapes(l_metal1).insert(pya.Path(lead2, int(round(w * scale))).polygon())

    # 8. VIA (Mask 7: M7_Vias — AZ1512 Positive Photoresist):
    # Because AZ1512 is positive resist, drawn polygons keep photoresist on the wafer
    # and cutout holes open windows for BOE to etch through the 1 um PVD SiO2 ILD.
    via_w = 10.0
    center_via = pya.Box(int(round((cx - via_w / 2.0) * scale)), int(round((cy - via_w / 2.0) * scale)),
                         int(round((cx + via_w / 2.0) * scale)), int(round((cy + via_w / 2.0) * scale)))

    pad2_via_w = pad_size - 20.0
    pad2_via = pya.Box(int(round((p2_cx - pad2_via_w / 2.0) * scale)), int(round((pad_cy - pad2_via_w / 2.0) * scale)),
                       int(round((p2_cx + pad2_via_w / 2.0) * scale)), int(round((pad_cy + pad2_via_w / 2.0) * scale)))

    via_resist_region = pya.Region(die_box) - pya.Region(center_via) - pya.Region(pad2_via)
    top_cell.shapes(l_via).insert(via_resist_region)

    # Write GDSII
    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    layout.write(output_file)
    print(f"GDSII layout mask written: {output_file}")
    print(f"  Configuration: Two-layer stacked square inductor")
    print(f"  Parameters: d_out={d_out} um, w={w} um, s={s} um, turns={n_turns}")
    print(f"  Layers: 1:SI_SUB, 2:SI_ETCH, 3:N_OX1, 4:NPLUS_SOG, 5:THIN_OX, 6:OX2, 7:METAL1, 8:VIA, 9:METAL2")
    return output_file


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SCRO Two-Layer Stacked Inductor Mask Generator")
    parser.add_argument("--d_out", type=float, default=DEFAULT_D_OUT, help="Outer diameter (um)")
    parser.add_argument("--w", type=float, default=DEFAULT_W, help="Line width (um)")
    parser.add_argument("--s", type=float, default=DEFAULT_S, help="Spacing (um)")
    parser.add_argument("--turns", "-n", type=float, default=DEFAULT_TURNS, help="Turn count")
    parser.add_argument("--output", "-o", default=None, help="Output GDS file")

    args = parser.parse_args()
    build_inductor_mask(d_out=args.d_out, w=args.w, s=args.s, n_turns=args.turns, output_file=args.output)
