# System Specifications — 2.4 GHz RF RX Front-End
## Derived from Project 1 OFDM BER Measurements

---

## RF System Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| RF center frequency | 2.4 GHz | OFDM standard (IEEE 802.11b/g) |
| LO frequency | 2.2 GHz | fRF − fIF |
| IF frequency | 200 MHz | Design choice (avoids DC offset) |
| OFDM channel bandwidth | 20 MHz | 64 subcarriers × 312.5 kHz |
| Number of subcarriers | 64 | Project 1 OFDM design |
| Subcarrier spacing | 312.5 kHz | BW / N = 20MHz / 64 |
| OFDM symbol duration | 3.2 μs | 1 / subcarrier spacing |
| Cyclic prefix | 0.8 μs | ¼ × symbol duration |
| Process technology | 180nm CMOS | Academic standard |
| Supply voltage | 1.8 V | 180nm standard |

---

## Modulation & BER Targets (from Project 1)

| Modulation | Eb/N0 for BER=10⁻³ | Required SNR | PAPR |
|------------|---------------------|--------------|------|
| QPSK | 6.8 dB | 9.8 dB | 11 dB |
| 16-QAM | 10.5 dB | 16.5 dB | 11 dB |

SNR = Eb/N0 + 10·log10(bits/symbol)
- QPSK: 6.8 + 10·log10(2) = 6.8 + 3.0 = **9.8 dB**
- 16-QAM: 10.5 + 10·log10(4) = 10.5 + 6.0 = **16.5 dB**

---

## Block-Level Specifications

### Block 1: LNA (Low Noise Amplifier)

| Parameter | Specification | Rationale |
|-----------|--------------|-----------|
| Topology | Cascode NMOS, inductive source degeneration | Industry standard for 2.4 GHz |
| S21 (gain) | > 15 dB | Dominates cascade NF via Friis |
| S11 (input match) | < −10 dB at 2.4 GHz | Minimize reflection loss |
| Noise Figure | < 2.5 dB | Sets cascade NF floor |
| IIP3 | > −5 dBm | First stage limits cascade IIP3 |
| K-factor | > 1 | Unconditional stability required |
| Power | < 10 mW | Overall power budget |
| Frequency | 2.4 GHz | RF center frequency |
| Input impedance | 50 Ω | Standard antenna/cable impedance |

**Transistor starting values (from sizing_calculator.py):**
- M1/M2: W = 167 μm, L = 180 nm, nf = 34, ID = 5 mA
- Ls = 0.25 nH (source degeneration — sets Re[Zin]=50Ω)
- Lg = 17.0 nH (gate matching — off-chip bond wire)
- Ld = 22.0 nH (drain load — on-chip spiral or off-chip)

---

### Block 2: Mixer (Double-Balanced Gilbert Cell)

| Parameter | Specification | Rationale |
|-----------|--------------|-----------|
| Topology | Double-balanced Gilbert cell | Suppresses LO feedthrough and AM noise |
| Conversion Gain | > 6 dB | Sufficient for filter + ADC |
| DSB Noise Figure | < 12 dB | Acceptable after high-gain LNA |
| IIP3 | > +5 dBm (input) | Input-referred; LNA gain raises signal above mixer nonlinearity |
| LO-RF Isolation | > 30 dB | Prevents LO leakage to antenna |
| IF frequency | 200 MHz | fRF − fLO = 2.4G − 2.2G |
| LO frequency | 2.2 GHz | From PLL |
| Power | < 15 mW | Overall budget |

**Transistor starting values:**
- M1/M2 (RF pair): W = 67 μm, L = 180 nm, ID = 2 mA each
- M3-M6 (LO quad): W = 267 μm, L = 180 nm
- ISS (tail current) = 4 mA total
- RL (load resistors) = 300 Ω
- LO drive amplitude = 400 mVpeak (differential)

---

### Block 3: IF Bandpass Filter (4th-Order Gm-C)

| Parameter | Specification | Rationale |
|-----------|--------------|-----------|
| Topology | 4th-order Gm-C bandpass (2 cascaded biquads) | Practical on-chip implementation at 200 MHz |
| Center frequency | 200 MHz ± 1% | Must track IF exactly |
| 3-dB bandwidth | 20 MHz | Matches OFDM channel BW |
| Passband ripple | < 0.5 dB | Flat passband for OFDM subcarriers |
| Stopband attenuation | > 40 dB at ±40 MHz | Rejects adjacent channels |
| Insertion loss | < 3 dB | Keeps signal above noise |
| IIP3 | > +10 dBm | Filter is most linear block |
| Group delay ripple | < ±10 ns across BW | OFDM ISI requirement |
| Power | < 20 mW | Budget |

**Component values:**
- Integration capacitor C = 500 fF (MIM or MOM capacitor)
- Gm_int = 628 μA/V (sets f0 = 200 MHz)
- Section 1: Q1 = 5.41, Gm_Q1 = 116 μA/V
- Section 2: Q2 = 13.07, Gm_Q2 = 48 μA/V
- OTA transistors: W = 5 μm, L = 500 nm (each Gm cell)

---

## Cascade System Specifications

### Friis Cascade Analysis

| Block | Gain (dB) | NF (dB) | IIP3 (dBm) | Cum. Gain (dB) | Cum. NF (dB) |
|-------|-----------|---------|------------|----------------|---------------|
| LNA | +15 | 2.5 | −5 | 15 | 2.50 |
| Mixer | +6 | 12.0 | +5 | 21 | 3.52 |
| IF Filter | −2 | 3.0 | +10 | 19 | 3.53 |

**Friis NF formula:**
```
F_total = F_LNA + (F_mixer − 1)/G_LNA + (F_filter − 1)/(G_LNA × G_mixer)
        = 1.778 + (15.85 − 1)/31.62 + (2.0 − 1)/(31.62 × 3.981)
        = 1.778 + 0.470 + 0.0079
        = 2.256  →  NF_cascade = 3.53 dB
```

**Cascade IIP3:**
```
1/IIP3_cascade = 1/IIP3_LNA + G_LNA/IIP3_mixer + G_LNA×G_mix/IIP3_filter
               = 3165 + 10000 + 12589  (all in 1/W)
IIP3_cascade ≈ −14 dBm  (input-referred)
```
Note: cascade IIP3 is dominated by the second stage (mixer) after LNA gain.
The SFDR = 55.6 dB is still well above the 11 dB OFDM PAPR requirement.

---

## Receiver Sensitivity

```
Sensitivity = kTB + NF_cascade + SNR_required

kTB (20 MHz BW) = −174 dBm/Hz + 10·log10(20×10⁶)
                = −174 + 73.0
                = −101.0 dBm

QPSK sensitivity = −101.0 + 3.53 + 9.8  = −87.7 dBm
16-QAM sensitivity = −101.0 + 3.53 + 16.5 = −81.0 dBm
```

---

## Link Budget

| Parameter | Value |
|-----------|-------|
| Thermal noise floor (kTB, 20 MHz) | −101.0 dBm |
| Cascade NF | +3.53 dB |
| Total noise figure contribution | −97.5 dBm |
| Required SNR (QPSK BER=10⁻³) | +9.8 dB |
| **Receiver sensitivity (QPSK)** | **−87.7 dBm** |
| OFDM PAPR | 11 dB |
| Peak input power at sensitivity | −76.7 dBm |
| Cascade IIP3 (input-referred) | −14 dBm |
| IIP3 margin above peak input | +62.7 dB ✓ |
| SFDR | 55.6 dB ✓ (> 11 dB PAPR) |

---

## Power Budget Summary

| Block | Supply | Current | Power |
|-------|--------|---------|-------|
| LNA | 1.8 V | ~5 mA | ~9 mW |
| Mixer | 1.8 V | ~4 mA | ~7 mW |
| IF Filter | 1.8 V | ~1 mA | ~2 mW |
| **Total** | **1.8 V** | **~10 mA** | **~18 mW** |

---

## Simulation Checklist

### Per-Block Minimum Simulations

| Block | DC | S-param / AC | Noise | IIP3 | Status |
|-------|----|-------------|-------|------|--------|
| LNA | ☐ | ☐ (SP 1-6 GHz) | ☐ (NF) | ☐ (PSS+PAC) | |
| Mixer | ☐ | ☐ (PSS CG) | ☐ (Pnoise) | ☐ (two-tone) | |
| IF Filter | ☐ | ☐ (AC 50-400M) | ☐ | ☐ | |
| Cascade | ☐ | ☐ (PSS) | ☐ (Pnoise) | ☐ (two-tone) | |

### 12 Metrics for Report

| # | Block | Metric | Target | Measured |
|---|-------|--------|--------|----------|
| 1 | LNA | S21 @ 2.4 GHz | > 15 dB | |
| 2 | LNA | S11 @ 2.4 GHz | < −10 dB | |
| 3 | LNA | NF @ 2.4 GHz | < 2.5 dB | |
| 4 | LNA | IIP3 | > −5 dBm | |
| 5 | LNA | K-factor | > 1 | |
| 6 | Mixer | Conversion Gain | > 6 dB | |
| 7 | Mixer | DSB NF | < 12 dB | |
| 8 | Mixer | IIP3 | > +5 dBm | |
| 9 | Filter | 3-dB Bandwidth | 20 MHz ± 5% | |
| 10 | Filter | Stopband rejection | > 40 dB | |
| 11 | Cascade | NF | < 4 dB | |
| 12 | Cascade | Sensitivity | < −85 dBm | |
