#!/usr/bin/env python3
"""
SCRO Two-Layer Stacked Rectangular Inductor — Parametric Mask Generator
========================================================================
Generates the GDSII layout mask for the SCRO two-layer stacked square inductor
using the official NRF Tapeout #2 layer stack defined in:
`SCRO/NRF_Tapeout2_Layer_Guidelines/NRF_Tapeout2_Reference_Example.py`.

Both metal layers contain matching spiral coils created by a loop of progressively
shorter lines. The spirals connect at the center via (VIA1), and both probe pads
connect to the outer terminals of the inductor.

NRF Tapeout #2 Mandatory Layers (1/0 through 8/0):
  1. SI_ETCH (1/0) : Silicon etch / alignment / mesa
  2. NPLUS   (2/0) : n+ source/drain doping
  3. NWELL   (3/0) : n-well doping
  4. THINOX  (4/0) : Gate / channel thin oxide
  5. CONT    (5/0) : Contact cuts through dielectric to silicon
  6. M1      (6/0) : Metal 1 (bottom spiral coil & lead to Pad 2)
  7. VIA1    (7/0) : Via 1 (center spiral interconnect via & Pad 2 surface via)
  8. M2      (8/0) : Metal 2 (top spiral coil, Pad 1, Pad 2 surface probe pad)
"""

import os

try:
    import pya
except ImportError:
    import klayout.db as pya

# =============================================================================
# PARAMETERS (in microns)
# =============================================================================
DEFAULT_D_OUT    = 400.0    # Outer dimension of inductor (um)
DEFAULT_W        = 10.0     # Line width / trace thickness (um)
DEFAULT_S        = 10.0     # Line spacing between turns (um)
DEFAULT_TURNS    = 9.0      # Number of turns
DEFAULT_PAD_SIZE = 150.0    # Probe pad dimension (um)
DEFAULT_PITCH    = 200.0    # Pad pitch center-to-center (um) — 150 um pad + 50 um spacing
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


def verify_gds(gds_filename):
    """Reads the GDS back and reports shapes per layer, so an empty file is caught immediately."""
    check = pya.Layout()
    check.read(gds_filename)
    top_cell = check.top_cell()
    total = 0
    print(f"[CHECK] Top cell: {top_cell.name}   bbox (um): {top_cell.dbbox()}")
    for li in check.layer_indexes():
        n = top_cell.shapes(li).size()
        total += n
        print(f"        layer {check.get_info(li)}: {n} shape(s)")
    if total == 0:
        print("[WARN] GDS contains NO shapes!")


def build_inductor_mask(d_out=DEFAULT_D_OUT,
                        w=DEFAULT_W,
                        s=DEFAULT_S,
                        n_turns=DEFAULT_TURNS,
                        pad_size=DEFAULT_PAD_SIZE,
                        pad_pitch=DEFAULT_PITCH,
                        margin=DEFAULT_MARGIN,
                        output_file=None):
    """
    Builds the two-layer stacked GDSII layout using the official NRF Tapeout #2
    8-layer stack: M1 (6/0), VIA1 (7/0), and M2 (8/0).
    All 8 mandatory layers are registered and preserved via SaveLayoutOptions.
    """
    if output_file is None:
        output_file = f"Inductors_GDSII/{d_out}um_rectangular_inductor.gds"

    # =========================================================================
    # STEP 1: LAYOUT & LAYER SETUP (NRF Tapeout #2 Standard)
    # =========================================================================
    layout = pya.Layout()
    layout.dbu = 0.001  # 1 nm database unit (DBox / DPath coordinates in um)
    top_cell = layout.create_cell("SCRO_INDUCTOR")

    # All 8 mandatory layers registered in exact order (1/0 through 8/0)
    l_sietch = layout.layer(1, 0, "SI_ETCH")
    l_nplus  = layout.layer(2, 0, "NPLUS")
    l_nwell  = layout.layer(3, 0, "NWELL")
    l_thinox = layout.layer(4, 0, "THINOX")
    l_cont   = layout.layer(5, 0, "CONT")
    l_m1     = layout.layer(6, 0, "M1")
    l_via1   = layout.layer(7, 0, "VIA1")
    l_m2     = layout.layer(8, 0, "M2")

    # Center coordinates
    cx, cy = 0.0, 0.0

    # Probe pad coordinates (placed below the inductor)
    p1_cx = cx - pad_pitch / 2.0
    p2_cx = cx + pad_pitch / 2.0
    pad_cy = cy - d_out / 2.0 - margin - pad_size / 2.0

    # =========================================================================
    # STEP 2: GENERATE SPIRALS & INTERCONNECTS
    # =========================================================================
    # Generate spiral coordinates using the progressive length loop
    m2_pts = generate_spiral_points(d_out, w, s, n_turns)
    m1_pts = [(-x, y) for x, y in m2_pts]  # Matching bottom spiral

    # Layer 6: M1 (6/0) — Bottom spiral coil
    pya_m1_pts = [pya.DPoint(x, y) for x, y in m1_pts]
    top_cell.shapes(l_m1).insert(pya.DPath(pya_m1_pts, w).polygon())

    # Layer 8: M2 (8/0) — Top spiral coil
    pya_m2_pts = [pya.DPoint(x, y) for x, y in m2_pts]
    top_cell.shapes(l_m2).insert(pya.DPath(pya_m2_pts, w).polygon())

    # Center landing pads on both metal layers
    center_pad_w = max(30.0, w * 2.5)
    center_box = pya.DBox(cx - center_pad_w / 2.0, cy - center_pad_w / 2.0,
                          cx + center_pad_w / 2.0, cy + center_pad_w / 2.0)
    top_cell.shapes(l_m1).insert(center_box)
    top_cell.shapes(l_m2).insert(center_box)

    # Probe Pad 1: Connected to the outer terminal of the top spiral (M2)
    p1_box = pya.DBox(p1_cx - pad_size / 2.0, pad_cy - pad_size / 2.0,
                      p1_cx + pad_size / 2.0, pad_cy + pad_size / 2.0)
    top_cell.shapes(l_m2).insert(p1_box)

    top_outer_x = m2_pts[0][0]
    top_outer_y = m2_pts[0][1] + (w / 2.0)
    lead1 = [
        pya.DPoint(p1_cx, pad_cy + pad_size / 2.0),
        pya.DPoint(p1_cx, top_outer_y),
        pya.DPoint(top_outer_x - (w / 2.0), top_outer_y)
    ]
    top_cell.shapes(l_m2).insert(pya.DPath(lead1, w).polygon())

    # Probe Pad 2: Connected to the outer terminal of the bottom spiral (M1)
    p2_box = pya.DBox(p2_cx - pad_size / 2.0, pad_cy - pad_size / 2.0,
                      p2_cx + pad_size / 2.0, pad_cy + pad_size / 2.0)
    top_cell.shapes(l_m1).insert(p2_box)
    top_cell.shapes(l_m2).insert(p2_box)  # Surface pad for probe needle landing

    bot_outer_x = m1_pts[0][0]
    bot_outer_y = m1_pts[0][1] + (w / 2.0)
    lead2 = [
        pya.DPoint(p2_cx, pad_cy + pad_size / 2.0),
        pya.DPoint(p2_cx, bot_outer_y),
        pya.DPoint(bot_outer_x + (w / 2.0), bot_outer_y)
    ]
    top_cell.shapes(l_m1).insert(pya.DPath(lead2, w).polygon())

    # Layer 7: VIA1 (7/0) — Vias through inter-metal dielectric (ILD)
    # 1) Center via connecting bottom (M1) and top (M2) spiral coils
    via_w = 10.0
    center_via = pya.DBox(cx - via_w / 2.0, cy - via_w / 2.0,
                          cx + via_w / 2.0, cy + via_w / 2.0)
    top_cell.shapes(l_via1).insert(center_via)

    # 2) Pad 2 via connecting M1 base to M2 surface pad for probe needle contact
    pad2_via_w = pad_size - 20.0
    pad2_via = pya.DBox(p2_cx - pad2_via_w / 2.0, pad_cy - pad2_via_w / 2.0,
                        p2_cx + pad2_via_w / 2.0, pad_cy + pad2_via_w / 2.0)
    top_cell.shapes(l_via1).insert(pad2_via)

    # =========================================================================
    # STEP 3: WRITE GDSII WITH CONTEXT INFO (Preserves all 8 NRF layers)
    # =========================================================================
    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    save_opts = pya.SaveLayoutOptions()
    save_opts.write_context_info = True
    layout.write(output_file, save_opts)

    print(f"[OK] Wrote GDSII layout mask: {output_file}")
    print(f"  Configuration: Two-layer stacked square inductor (NRF Tapeout #2)")
    print(f"  Parameters: d_out={d_out} um, w={w} um, s={s} um, turns={n_turns}, pad_size={pad_size} um, pitch={pad_pitch} um")
    print(f"  Layers: 1:SI_ETCH, 2:NPLUS, 3:NWELL, 4:THINOX, 5:CONT, 6:M1, 7:VIA1, 8:M2")
    verify_gds(output_file)
    return output_file


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SCRO Two-Layer Stacked Inductor Mask Generator (NRF Tapeout #2)")
    parser.add_argument("--d_out", type=float, default=DEFAULT_D_OUT, help="Outer diameter (um)")
    parser.add_argument("--w", type=float, default=DEFAULT_W, help="Line width (um)")
    parser.add_argument("--s", type=float, default=DEFAULT_S, help="Spacing (um)")
    parser.add_argument("--turns", "-n", type=float, default=DEFAULT_TURNS, help="Turn count")
    parser.add_argument("--output", "-o", default=None, help="Output GDS file")

    args = parser.parse_args()
    build_inductor_mask(d_out=args.d_out, w=args.w, s=args.s, n_turns=args.turns, output_file=args.output)
