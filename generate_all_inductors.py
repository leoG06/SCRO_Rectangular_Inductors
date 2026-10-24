#!/usr/bin/env python3
"""
Batch GDSII Generator for SCRO Rectangular Inductors
====================================================
Automatically generates the 400, 800, and 1200 um two-layer stacked rectangular
inductor GDSII masks with their optimal turn counts (9, 17.5, and 26.5 turns)
using scro_rectangular_inductor.py.
"""

from scro_rectangular_inductor import build_inductor_mask
#todo make the amount of turns and the rest of the parameters parametric, from jupyter notebook

INDUCTOR_CONFIGS = [
    {"d_out": 400.0,  "w": 10.0, "s": 10.0, "n_turns": 9.0},
    {"d_out": 800.0,  "w": 10.0, "s": 10.0, "n_turns": 17.5},
    {"d_out": 1200.0, "w": 10.0, "s": 10.0, "n_turns": 26.5},
]


def main():
    for cfg in INDUCTOR_CONFIGS:
        build_inductor_mask(
            d_out=cfg["d_out"],
            w=cfg["w"],
            s=cfg["s"],
            n_turns=cfg["n_turns"],
        )


if __name__ == "__main__":
    main()
