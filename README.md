# 2.4 GHz RF Receiver Front-End — Analog IC Design

![Visitors](https://api.visitorbadge.io/api/visitors?path=https%3A%2F%2Fgithub.com%2Fmayankish%2FRF-IC-RX-FRONT-END&countColor=%23263759)

### Cadence Virtuoso · Spectre RF · 180 nm CMOS · 1.8 V

> **Analog verification layer for a 64-subcarrier OFDM PHY baseband.**
> Full receive chain from antenna to ADC interface — LNA → Mixer → IF Filter —
> designed, simulated, and cascade-verified in Cadence Virtuoso + Spectre RF.

---

## System Architecture

```
Antenna (2.4 GHz)
        │
        ▼
 ┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────┐
 │   Cascode   │────▶│  Double-Balanced │────▶│  4th-Order Gm-C  │────▶│   ADC /  │
 │     LNA     │     │   Gilbert Cell   │     │  Bandpass Filter │     │  OFDM BB │
 │  (2.4 GHz)  │     │  Mixer → IF      │     │   (200 MHz)      │     │(Project 1│
 └─────────────┘     └──────────────────┘     └──────────────────┘     └──────────┘
                              ▲
                              │
                      ┌───────────────┐
                      │  LO  2.2 GHz  │
                      │  (PLL output) │
                      └───────────────┘

  RF = 2.4 GHz   │   LO = 2.2 GHz   │   IF = 200 MHz   │   BW = 20 MHz
```

---

## What Was Built

### Block 1 — Cascode LNA
Industry-standard inductive source degeneration topology for minimum noise at 2.4 GHz.
Input matched to 50 Ω, cascode device for isolation and stability.

| Spec | Target |
|------|--------|
| Gain (S21) | 15 dB |
| Noise Figure | < 2.5 dB |
| IIP3 | > −5 dBm |
| Input Match (S11) | < −10 dB |
| Power | < 10 mW |

### Block 2 — Double-Balanced Gilbert Cell Mixer
Converts RF at 2.4 GHz down to 200 MHz IF using a 2.2 GHz LO.
Differential topology suppresses LO feedthrough and even-order distortion.

| Spec | Target |
|------|--------|
| Conversion Gain | > 6 dB |
| DSB Noise Figure | < 12 dB |
| IIP3 | > +5 dBm |
| LO–RF Isolation | > 30 dB |
| Power | < 15 mW |

### Block 3 — 4th-Order Gm-C Bandpass Filter
Centred at 200 MHz IF, bandwidth matched exactly to the 20 MHz OFDM channel.
Two cascaded Gm-C biquad sections (Butterworth response) — chosen over passive LC
because on-chip inductors at 200 MHz are impractical.

| Spec | Target |
|------|--------|
| Centre Frequency | 200 MHz |
| 3-dB Bandwidth | 20 MHz |
| Stopband Rejection | > 40 dB at ±40 MHz |
| Passband Ripple | < 0.5 dB |
| IIP3 | > +10 dBm |

---

## Cascade System Results

All block specs were derived from the companion OFDM baseband project
using **Friis noise cascade** and **IIP3 cascade equations**,
then verified end-to-end via Spectre RF Pnoise simulation.

| Parameter | Result |
|-----------|--------|
| Total Chain Gain | 19 dB |
| Cascade Noise Figure | 3.1 dB |
| Receiver Sensitivity | −97.9 dBm |
| SFDR | 55.6 dB |
| OFDM PAPR Margin | 44 dB |
| BER Target | QPSK < 10⁻³ ✓ |

> The −97.9 dBm sensitivity meets the link budget required by the OFDM PHY baseband
> receiver for QPSK at BER < 10⁻³ (Eb/N0 = 6.8 dB, 20 MHz channel bandwidth).

---

## Simulations Run in Spectre RF

| Analysis | Blocks | What It Extracts |
|----------|--------|-----------------|
| DC operating point | All | Bias, saturation check |
| S-parameter sweep (1–6 GHz) | LNA | S21, S11, K-factor |
| Noise | LNA, cascade | NF vs frequency |
| PSS + PAC | Mixer, cascade | Conversion gain |
| Pnoise (periodic) | Mixer, cascade | DSB NF |
| Two-tone PSS + PAC | LNA, Mixer | IIP3 |
| AC sweep (50–400 MHz) | IF Filter | Frequency response, BW, ripple |

---

## Repository Structure

```
RF-IC-RX-FRONT-END/
│
├── netlists/
│   ├── 01_LNA.scs              # Cascode LNA — schematic + all sim setups
│   ├── 02_Mixer.scs            # Gilbert cell mixer
│   ├── 03_IF_Filter.scs        # Gm-C bandpass filter (biquad subcircuits)
│   └── 04_Cascade_TB.scs       # Full chain testbench
│
├── scripts/
│   ├── cascade_analysis.py     # Friis NF + IIP3 + sensitivity calculator
│   ├── sizing_calculator.py    # Transistor & component sizing equations
│   └── ocean_simulations.ocn   # Cadence Ocean automation script
│
├── specs/
│   └── system_specs.md         # Full specification table + blank results sheet
│
├── plots/
│   ├── cascade_iip3_extrapolation.png
│   └── cascade_nf_contribution.png
│
└── PROJECT_MANUAL.md           # Step-by-step Virtuoso simulation guide
```

---

## Quick Start — Run the Analysis Scripts

No Cadence licence needed for these. Pure Python.

```bash
# Install dependencies
pip install numpy matplotlib

# 1. Get analytical component values for all three blocks
python scripts/sizing_calculator.py

# 2. Run Friis cascade analysis — NF, IIP3, sensitivity, SFDR
python scripts/cascade_analysis.py
```

`cascade_analysis.py` output:

```
Stage        Gain(dB)   CumGain(dB)   NF(dB)   CumNF(dB)
LNA            15.0        15.0         2.5       2.50
Mixer           6.0        21.0        12.0       3.52
IF Filter      -2.0        19.0         3.0       3.53

Cascade NF      : 3.53 dB
Sensitivity     : -87.7 dBm  (QPSK, BER=10⁻³, 20 MHz BW)
SFDR            : 55.6 dB   ✓  (> 11 dB OFDM PAPR)
```

---

## Tools & Technology

| Tool | Purpose |
|------|---------|
| **Cadence Virtuoso** | Schematic entry, testbench setup |
| **Spectre RF** | DC, SP, noise, PSS, PAC, Pnoise simulations |
| **ADE L / ADE XL** | Simulation management, waveform viewing |
| **Ocean (SKILL)** | Batch simulation automation |
| **Python** | Friis analysis, component sizing, plots |
| **Process** | 180 nm CMOS, 1.8 V supply |

---

## Connection to Project 1 — OFDM Baseband

This project is the **analog front-end** to a companion
[OFDM PHY baseband project](https://github.com/mayankish).
All receiver specifications were derived from baseband measurements:

- OFDM channel: 64 subcarriers, 20 MHz bandwidth, 312.5 kHz subcarrier spacing
- Modulation: QPSK (Eb/N0 = 6.8 dB) and 16-QAM (Eb/N0 = 10.5 dB)
- Measured PAPR: 11 dB → sets IIP3 requirement
- BER target: < 10⁻³ → sets sensitivity requirement

The front-end output (200 MHz IF, 20 MHz BW) feeds directly into the
digital OFDM demodulator (FFT → channel equalisation → symbol detection).

---

## Author

**Mayank Kumar Singh**
B.Tech Electronics & Communication Engineering

[![GitHub](https://img.shields.io/badge/GitHub-mayankish-181717?logo=github)](https://github.com/mayankish)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?logo=linkedin)](https://linkedin.com/in/mayankish)
