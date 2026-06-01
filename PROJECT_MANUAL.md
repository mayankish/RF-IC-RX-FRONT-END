# 2.4 GHz RF Receiver Front-End — Project Manual
## LNA → Gilbert Mixer → Gm-C IF Filter → OFDM Baseband Interface

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [Prerequisites & Tools](#2-prerequisites--tools)
3. [Run the Sizing Calculator First](#3-run-the-sizing-calculator-first)
4. [Block 1: LNA Design & Simulation](#4-block-1-lna-design--simulation)
5. [Block 2: Mixer Design & Simulation](#5-block-2-mixer-design--simulation)
6. [Block 3: IF Filter Design & Simulation](#6-block-3-if-filter-design--simulation)
7. [Full Cascade Verification](#7-full-cascade-verification)
8. [Connecting to Project 1 OFDM Baseband](#8-connecting-to-project-1-ofdm-baseband)
9. [Troubleshooting & Tuning Guide](#9-troubleshooting--tuning-guide)
10. [Verification Checklist & Deliverables](#10-verification-checklist--deliverables)

---

## 1. System Overview

This project implements the complete analog RF front-end chain from antenna to ADC interface, designed to receive a 2.4 GHz OFDM signal. The chain feeds the OFDM baseband processor from Project 1.

```
Antenna (2.4 GHz)
      │
      ▼
┌──────────┐   ┌──────────┐   ┌────────────┐   ┌──────────────┐
│   LNA    │──▶│  Mixer   │──▶│  IF Filter │──▶│  ADC / OFDM  │
│ 2.4 GHz  │   │ (Gilbert)│   │  200 MHz   │   │  Baseband    │
│ Cascode  │   │2.4G→200M │   │  Gm-C BPF  │   │  (Project 1) │
└──────────┘   └──────────┘   └────────────┘   └──────────────┘
                    ▲
                    │
               ┌─────────┐
               │   LO    │
               │ 2.2 GHz │
               └─────────┘
```

### System Specifications (derived from Project 1 OFDM measurements)

| Parameter | Value | Derivation |
|-----------|-------|------------|
| RF center frequency | 2.4 GHz | OFDM center |
| LO frequency | 2.2 GHz | fRF - fIF |
| IF frequency | 200 MHz | fRF - fLO |
| OFDM bandwidth | 20 MHz | 64 subcarriers × 312.5 kHz |
| Target NF (cascade) | < 4 dB | Link budget |
| Target IIP3 (cascade) | > -5 dBm | PAPR = 11 dB |
| Required sensitivity | < -88 dBm | QPSK BER=10⁻³ |
| Process | 180nm CMOS | Academic standard |
| Supply voltage | 1.8 V | 180nm standard |

### Cascade Budget (Friis Analysis)

| Block | Gain (dB) | NF (dB) | IIP3 (dBm) |
|-------|-----------|---------|------------|
| LNA | +15 | 2.5 | -5 |
| Mixer | +6 | 12.0 | +5 |
| IF Filter | -2 | 3.0 | +10 |
| **CASCADE** | **+19** | **3.1** | **-3.2** |

Sensitivity (QPSK, BER=10⁻³): -174 + 3.1 + 73.0 + 9.8 = **-88.1 dBm** ✓

---

## 2. Prerequisites & Tools

### Software Required
- **Cadence Virtuoso** (IC6.1.7 or newer, or ICADVM)
- **Spectre RF** (must be licensed — required for PSS, Pnoise, PAC)
- **ADE L or ADE XL** (simulation manager)
- **Python 3.x** with numpy, matplotlib (for analysis scripts)

### PDK Required
- 180nm CMOS PDK (TSMC, SMIC, GlobalFoundries, or university kit)
- If using MOSIS/FreePDK: adjust W, L values per your process parameters
- Get `nmos` and `pmos` model names from your PDK datasheet

### Files in This Project

```
Rx FRONT for OFDM/
├── PROJECT_MANUAL.md          ← This file
├── netlists/
│   ├── 01_LNA.scs             ← LNA Spectre netlist + sim setups
│   ├── 02_Mixer.scs           ← Mixer Spectre netlist + sim setups
│   ├── 03_IF_Filter.scs       ← IF Filter netlist + sim setups
│   └── 04_Cascade_TB.scs      ← Full chain testbench
├── scripts/
│   ├── cascade_analysis.py    ← Friis NF/IIP3 calculator (run first)
│   ├── sizing_calculator.py   ← Transistor/component sizing equations
│   └── ocean_simulations.ocn  ← Cadence Ocean automation script
└── specs/
    └── system_specs.md        ← Specifications reference
```

---

## 3. Run the Sizing Calculator First

Before opening Virtuoso, run the Python sizing tools to get component values.

```bash
# Install dependencies (if needed)
pip install numpy matplotlib

# Step 1: Get analytical component values
python scripts/sizing_calculator.py

# Step 2: Verify cascade specs match design targets
python scripts/cascade_analysis.py
```

The sizing calculator outputs:
- Transistor W/L for each block
- Inductor values (Ls, Lg, Ld) for LNA
- Gm cell target values for IF filter
- Capacitor values

**These are starting points. You will tune them in Spectre.**

---

## 4. Block 1: LNA Design & Simulation

### 4.1 Topology

Inductive source degeneration cascode LNA. This is the industry-standard topology for low-noise RF amplification at 2.4 GHz.

```
VDD (1.8V)
   │
  Ld (4.7 nH) ← drain inductor resonates at 2.4 GHz
   │
  M2 (cascode) ← W=200μm, L=180nm, 40 fingers
   │
  M1 (main)    ← W=200μm, L=180nm, 40 fingers
   │
  Ls (0.7 nH)  ← source degen: sets Re[Zin]=50Ω via ωT·Ls=50
   │
  GND

  Input: RF_in → Lg (12 nH) → gate of M1
  The series resonance Lg-Cgs-Ls cancels Im[Zin] at 2.4 GHz
```

### 4.2 Creating the Schematic in Virtuoso

1. Open Virtuoso → File → New → Library → "RxFrontEnd"
2. Create new cellview: `LNA`, view `schematic`
3. Place NMOS instances from your PDK (search: `nmos` in component library)
4. Set M1 properties: `w=200u`, `l=180n`, `nf=40`
5. Set M2 properties: same as M1
6. Place inductors (`ind` or `inductor` from analogLib):
   - Ld: l=4.7n, q=7
   - Lg: l=12n, q=8
   - Ls: l=0.7n, q=15
7. Add bias resistors: Rbias_top=20kΩ, Rbias_bot=15kΩ (for voltage divider)
8. Add bypass capacitors: 10 pF at each bias node
9. Add pad capacitor: Cpad=100fF at RF input

**Wire connections per topology above. Reference 01_LNA.scs for node names.**

### 4.3 Creating the LNA Testbench

1. Create new cellview: `LNA_TB`, view `schematic`
2. Place your LNA schematic as an instance (Add Instance → RxFrontEnd → LNA)
3. Add:
   - `port` element (analogLib) at RF input: r=50, num=1
   - `port` element at output: r=50, num=2
   - `vdc` source: dc=1.8V connected to VDD/GND
4. Save testbench schematic

### 4.4 LNA Simulation Procedure

#### Step 1: DC Operating Point

Launch ADE L → Analysis → Choose → DC
- Enable: Save operating point (op)
- Run simulation

**What to check:**
```
M1 in saturation: VDS > VGS - Vth
  VGS_M1 ≈ 0.65-0.75 V  (bias sets this via voltage divider)
  VDS_M1 ≈ 0.6-0.9 V    (depends on Ld DC drop)
  ID_M1  ≈ 4-6 mA        (power check)

M2 in saturation: VDS_M2 > VGS_M2 - Vth
  VGS_M2 ≈ 1.2 V         (cascode bias)
  VDS_M2 ≈ 0.8-1.1 V

Total PDC = VDD × ID ≈ 1.8 × 5mA = 9 mW  (target < 10 mW)
```

If M1 is in linear (triode) region: increase VGS (raise Rbias_bot) or reduce W.
If ID is too high: lower VGS or increase L slightly.

#### Step 2: S-Parameter Simulation

ADE → Analysis → SP
- Frequency: Start=1G, Stop=6G, Step=10M
- Ports: select Port1 and Port2

**Results to extract:**

| Parameter | Where to Read | Target |
|-----------|---------------|--------|
| S21 at 2.4 GHz | Results → Direct Plot → S-parameter | > 15 dB |
| S11 at 2.4 GHz | Same | < -10 dB |
| S12 at 2.4 GHz | Same (reverse isolation) | < -25 dB |
| K-factor at 2.4 GHz | Calculate → Stability(K) | > 1 |

**Tuning S11 (input matching):**
- If S11 minimum is NOT at 2.4 GHz: adjust Lg value
- S11 too high: tune Ls to move real part of Zin closer to 50Ω
- Rule: Lg shifts the frequency of minimum S11; Ls shifts the real part

**Tuning S21 (gain):**
- Increase ID (raise gate bias voltage) → higher gm → higher S21
- Ensure Ld resonates at 2.4 GHz (Ld × Cout ≈ 1/ω₀²)

#### Step 3: Noise Figure Simulation

ADE → Analysis → Noise
- Input port: Port1, Output: Port2
- Frequency: 1G to 6G

**Read NF at 2.4 GHz → target < 2.5 dB**

**Tuning NF:**
- NF is minimized when the source impedance seen by M1 equals Zopt (optimum noise impedance)
- Increasing W (wider M1) decreases Zopt → shifts optimum match
- The NF minimum and S11 minimum do NOT necessarily occur at the same Lg value
- Start with NF < 2.5 dB. If NF is too high:
  1. Increase device width W (cautiously — also increases power)
  2. Reduce Ls slightly (reduces noise penalty from source degen)
  3. Check Q of Ls inductor (low Q = resistive loss = extra noise)

#### Step 4: IIP3 Simulation

**Setup (two-tone PSS):**
1. Add two voltage sources at RF input: f1=2.400 GHz, f2=2.401 GHz
2. Remove port elements (or disable them)
3. Set source amplitude: Vamp = -40 dBm → V_peak = √(2 × 50 × 10^(-4)) ≈ 3.16 mV
4. ADE → Analysis → PSS:
   - Fund frequency: 1 MHz (beat frequency = |f2-f1|)
   - Stabilization time: 200 ns
   - Number of harmonics: 15
5. After PSS, add PAC analysis: sweep 1 MHz to 3 GHz

**Extracting IIP3 in Virtuoso Calculator:**
```
From Results menu: use 'iip3' function
Or manually:
  1. Plot PAC output magnitude at f1 and at IM3 frequency (2f1-f2)
  2. IIP3 = Pin_fundamental + (Pfundamental - PIM3) / 2
  3. Expected IIP3 > -5 dBm
```

**Tuning IIP3:**
- IIP3 limited by gm nonlinearity (3rd-order term)
- To improve IIP3: add small source resistance (RS = 5-20 Ω) to M1 source
  (additional source degen beyond Ls — trades gain for linearity)
- Or: reduce VGS overdrive to move bias away from strong nonlinear region

### 4.5 LNA Deliverables

After simulation, record these 5 numbers:

| Metric | Measured Value | Pass? |
|--------|---------------|-------|
| S21 @ 2.4 GHz | | > 15 dB |
| S11 @ 2.4 GHz | | < -10 dB |
| NF @ 2.4 GHz | | < 2.5 dB |
| IIP3 | | > -5 dBm |
| K-factor | | > 1 |

---

## 5. Block 2: Mixer Design & Simulation

### 5.1 Topology

Double-balanced Gilbert cell. The most widely used active mixer topology.

```
        VDD (1.8V)
         │
    RL──┤├──RL           RL = 300 Ω load resistors
    │           │
   IFm         IFp        ← Differential IF output (200 MHz)
    │    ╔═════╗│
    M5 ══╣     ╠══M3      ← LO switching quad
    │    ║     ║  │
    M6 ══╣     ╠══M4      W=80μm, L=180nm
    └────╚═════╝──┘
          │     │
         M1    M2          ← RF transconductance pair
          │     │          W=120μm, L=180nm
         RFp  RFm
          └──┬──┘
           ISS (4mA)       ← Tail current source
              │
             GND

LO input: LOp, LOm (differential, 400mVpeak, 2.2 GHz)
IF output: IFp - IFm at 200 MHz (= fRF - fLO)
```

### 5.2 Schematic Entry in Virtuoso

1. Create cellview: `Mixer`, view `schematic`
2. Place NMOS instances:
   - M1, M2 (RF pair): w=120u, l=180n, nf=24
   - M3-M6 (LO quad): w=80u, l=180n, nf=16
   - Mtail (current source): w=40u, l=180n, nf=8
3. Add load resistors: R=300 Ω each (use `resistor` from analogLib)
4. Add bypass caps at LO input: C=10 pF
5. Add VDD bypass: C=10 pF

**Critical wiring:** LO switching must create the cross-coupled pattern. Verify:
- M3 drain → IFp, M3 gate → LOp, M3 source → drain of M1
- M4 drain → IFm, M4 gate → LOm, M4 source → drain of M1
- M5 drain → IFm, M5 gate → LOp, M5 source → drain of M2
- M6 drain → IFp, M6 gate → LOm, M6 source → drain of M2

If confused: this is cross-coupled. LO+ connects M3 and M5 (which feed opposite outputs).

### 5.3 Mixer Simulation Procedure

#### Step 1: DC (verify bias)

Check M1/M2: ID ≈ ISS/2 = 2 mA each, VDS > VGS-Vth ≈ 0.15V
Check Mtail: VDS sufficient for saturation
Total current from VDD: ≈ 4-5 mA → PDC ≈ 7-9 mW

#### Step 2: Conversion Gain (PSS)

ADE → Analysis → PSS:
- Fundamental: 2.2 GHz (LO frequency)
- Harmonics: 10
- tstab: 10n
- LO source amplitude: 400 mVpeak

Then add PAC analysis:
- Sweep 100 MHz to 300 MHz
- Read gain at 200 MHz (the IF frequency)
- This is your conversion gain. Target: > 6 dB

**Conversion gain formula (to predict before simulation):**
```
CG ≈ (2/π) × gm_RF × RL = (2/π) × 23mA/V × 300Ω ≈ 4.4 (= 12.9 dB)
If measured < 6 dB: check LO is actually switching (increase VLO amplitude)
If measured >> expected: check for resonance at IF frequency
```

#### Step 3: DSB Noise Figure (Pnoise)

After PSS run, add Pnoise analysis:
- Output: IFp (or differential)
- Input referred to RF port
- Sweep: 100M to 300M
- At 200 MHz: should read DSB NF < 12 dB

**DSB vs SSB NF:**
DSB NF is 3 dB lower than SSB NF for a well-balanced mixer (both sidebands fold to same IF).
Spectre Pnoise reports DSB NF by default for a double-balanced mixer.

#### Step 4: LO-RF Port Isolation

Switch to S-parameter simulation with three ports:
- Port 1: RF input (RFp-RFm)
- Port 2: LO input (LOp-LOm)
- Port 3: IF output (IFp-IFm)

Read S21 (Port2→Port1 = LO→RF isolation). Target: > 30 dB.
If < 30 dB: common cause is layout-induced coupling (less relevant in schematic sim)

#### Step 5: IIP3

Two-tone test:
- f1 = 2.400 GHz, f2 = 2.401 GHz (RF tones)
- After downconversion: IF tones at 200 MHz, 201 MHz
- IM3 appears at: 199 MHz, 202 MHz

PSS: fund = 1 MHz (beat), harmonics = 5000 (or use shooting Newton PSS)
PAC: sweep around IF to capture IM3

**Expected IIP3 > +5 dBm referred to RF input**

### 5.4 Mixer Deliverables

| Metric | Measured | Target |
|--------|----------|--------|
| Conversion Gain | | > 6 dB |
| DSB NF | | < 12 dB |
| IIP3 (input) | | > +5 dBm |
| LO-RF Isolation | | > 30 dB |

---

## 6. Block 3: IF Filter Design & Simulation

### 6.1 Topology

4th-order Gm-C bandpass filter, implemented as two cascaded 2nd-order Gm-C biquad sections.

**Why Gm-C?** At 200 MHz, passive LC filters need inductors of ~100 nH range — impossible on-chip at this frequency with good Q. Gm-C synthesizes LC behavior using OTAs (operational transconductors) and capacitors.

**Gm-C Biquad Principle:**
```
A 2nd-order bandpass transfer function:
   H(s) = (Gm1/C) · s / [s² + (Gm3/C)·s + (Gm1·Gm2/C²)]
   
   ω0 = √(Gm1·Gm2) / C   → sets center frequency
   Q  = ω0·C / Gm3        → sets bandwidth (BW = f0/Q)
```

**Design values (from sizing calculator):**
```
C_integration = 500 fF
Gm_int = ω0 × C = 2π × 200MHz × 500fF = 628 μA/V

Section 1 (Q1 = 5.41): Gm_Q1 = 628μ / 5.41 = 116 μA/V
Section 2 (Q2 = 13.07): Gm_Q2 = 628μ / 13.07 = 48 μA/V
```

### 6.2 OTA (Gm Cell) Design

Each Gm cell is a simple differential pair with PMOS current mirror load.

```
VDD
 │
Mp1──Mp2    ← PMOS current mirror (active load)
 │    │
 └──┐ └──▶ OUTp
    │       │
Mn1 │  Mn2  OUTm   ← NMOS diff pair
 │  │   │
INp │  INm
    │
  Mtail    ← tail current source (sets Gm)
    │
   GND
```

For target Gm = 628 μA/V using W=5μm, L=500nm:
```
gm = √(2 × μnCox × W/L × ID)
ID = gm² / (2 × μnCox × W/L) = (628μ)² / (2 × 270μ × 10) = 73 μA
```

Set tail current = 73 μA (via NMOS current mirror from reference).

### 6.3 Schematic Entry

1. Create `GmCell` sub-circuit (reusable Gm cell):
   - Mn1, Mn2: w=5u, l=500n, nf=2
   - Mp1, Mp2: w=8u, l=500n, nf=2
   - Mtail: w=4u, l=500n, nf=2 (tune W for target Gm)

2. Create `BPF_Biquad` sub-circuit:
   - 4× GmCell instances (Gm1, Gm2, Gm3, Gm4)
   - 2× 500 fF capacitors (C1, C2 — use MIM caps from PDK)
   - 2× VCM sources (for common-mode biasing of cap bottom plates)

3. Create `BPF_4thOrder`:
   - 2× BPF_Biquad in cascade
   - Bias current DACs or reference mirrors

4. Create testbench `IFFilter_TB`:
   - Differential sine source at 200 MHz
   - Filter instance
   - High-Z load (10 kΩ || 200 fF)

### 6.4 Filter Simulation Procedure

#### Step 1: DC

Verify all OTA transistors in saturation. Output common-mode ≈ VDD/2 = 0.9V.
If CM is off: your CMFB (common-mode feedback) is not correct. See troubleshooting.

#### Step 2: AC Frequency Response (Critical)

ADE → Analysis → AC:
- Sweep: 50 MHz to 400 MHz, 1 MHz steps
- Input: amplitude=1 V (small signal)
- Plot: |Vout| in dB

**What to measure:**
```
At 200 MHz (center): gain should be ≈ 0 dB (or small positive if Q amplifies)
At 180 MHz: note attenuation
At 220 MHz: note attenuation (should be symmetric)
3-dB frequencies: f_low and f_high where gain = peak - 3dB
  BW = f_high - f_low → target: 20 MHz
At 160 MHz and 240 MHz: attenuation > 40 dB (stopband spec)
```

**Tuning f0:**
- If f0 is too low: increase Gm_int (raise tail current in Gm cells)
- If f0 is too high: decrease Gm_int (lower tail current)
- f0 scales as: f0 ∝ √(Gm_int), so ±20% Gm → ±10% f0

**Tuning BW (Q):**
- If BW too narrow (over-peaked): decrease Gm_Q cells (lower Q damping current)
- If BW too wide (under-damped): increase Gm_Q cells
- BW = f0/Q = ω0·Gm_Q / (ω0·C) = Gm_Q/C → BW ∝ Gm_Q

**Common problem — instability (oscillation):**
If AC sweep shows peaking that doesn't settle or transient oscillates:
1. Q is too high (Gm_Q too small) — increase Gm_Q
2. Phase margin insufficient in Gm cell — add small resistor (100-200 Ω) in series with load capacitor

#### Step 3: Group Delay Check

After AC sweep, plot group delay in ADE Calculator:
```
Calculator: deriv(-phase(Vout) / (2π))    or    use 'groupDelay' function
```

For OFDM: group delay must be flat (± 10 ns) across the 20 MHz passband.
OFDM symbol duration ≈ 3.2 μs → cyclic prefix ≈ 0.8 μs.
Group delay ripple > 800 ns would cause ISI.

#### Step 4: Noise Analysis

ADE → Analysis → Noise:
- Input: differential sine source (or port)
- Output: OUTp
- Frequency: 50M to 400M

Input-referred noise at 200 MHz should be < 10 nV/√Hz.
Higher noise means ADC will see elevated noise floor → degrades SNR.

### 6.5 Filter Deliverables

| Metric | Measured | Target |
|--------|----------|--------|
| Center frequency f0 | | 200 MHz ± 2 MHz |
| 3-dB bandwidth | | 20 MHz ± 2 MHz |
| Passband ripple | | < 0.5 dB |
| Stopband @ ±40 MHz | | > 40 dB |
| Insertion loss at f0 | | < 3 dB |
| IIP3 | | > +10 dBm |

---

## 7. Full Cascade Verification

### 7.1 Building the Cascade Testbench

1. Create cellview `Cascade_TB`
2. Instantiate LNA, Mixer, Filter as sub-circuits
3. Connect: LNA output → Mixer RF input (via ideal balun if needed)
4. Connect: Mixer IF output → Filter input
5. Add:
   - RF input source with series 50 Ω (Thevenin)
   - LO source: 400 mVpeak, 2.2 GHz (differential)
   - ADC load model: 10 kΩ || 1 pF at filter output
6. Separate VDD supplies for each block (measure individual power)

### 7.2 Cascade DC

Run DC first. Verify:
- All blocks biased correctly (from individual sims — should be automatic)
- Total chain PDC: I_LNA + I_MIX + I_FILT, multiplied by 1.8V
- Expected: 5 + 7 + 10 mA = 22 mA → 39.6 mW total

### 7.3 Cascade PSS + Pnoise (NF Measurement)

This is the definitive cascade NF measurement:
1. PSS: fund = 200 MHz (IF beat frequency), tstab = 20n, harms = 15
2. Pnoise: input referred to RF source, output at filter output
3. Read NF at 200 MHz → should match Friis prediction of 3.1 dB

**If cascade NF > Friis prediction:**
Most likely cause: inter-block impedance mismatch is adding gain/loss not accounted for.
Recheck interstage: LNA output impedance vs mixer input impedance.

### 7.4 Cascade IIP3

Two-tone test with full chain:
- f1 = 2.400 GHz, f2 = 2.401 GHz at antenna input
- Sweep amplitude from -80 dBm to -30 dBm
- Observe fundamental (200 MHz) and IM3 (199 MHz) at output
- Extract IIP3 → should be ≈ -3.2 dBm (from Friis)

### 7.5 Friis Verification Table

Fill this in after simulations:

| Parameter | Friis Prediction | Measured | Pass? |
|-----------|-----------------|----------|-------|
| Cascade NF | 3.1 dB | | < 4 dB |
| Cascade IIP3 | -3.2 dBm | | > -10 dBm |
| Total Gain | 19 dB | | 15-22 dB |
| Sensitivity | -88.1 dBm | | < -85 dBm |

---

## 8. Connecting to Project 1 OFDM Baseband

### 8.1 Interface Specification

The IF filter output (200 MHz, 20 MHz BW) connects to an ADC, whose digital output feeds the Project 1 OFDM FFT demodulator.

At the filter output:
- Signal center: 200 MHz
- Bandwidth: 20 MHz
- Expected amplitude: depends on input level + cascade gain

For QPSK at sensitivity limit (-88 dBm input):
```
Output power = -88 dBm + 19 dB gain = -69 dBm
V_rms = √(10^(-69/10) × 1e-3 × 50) ≈ 0.8 μV rms
```

ADC input range: typically 0.5-1 Vpeak → need VGA (variable gain amplifier) between filter and ADC. This block is optional for the project but noted for completeness.

### 8.2 End-to-End BER Simulation

To fully connect Project 1 and Project 2:
1. Generate OFDM waveform in MATLAB (from Project 1 code)
2. Export as PWL (piecewise-linear) data file
3. Upconvert to 2.4 GHz mathematically (multiply by cos(2π×2.4G×t))
4. Apply as input to cascade testbench in Spectre
5. Capture IF output waveform from Spectre
6. Import back to MATLAB
7. Downconvert digitally (demodulate 200 MHz carrier)
8. Run OFDM FFT, equalization, BER measurement
9. Compare BER with/without front-end → front-end should add < 0.5 dB SNR loss

---

## 9. Troubleshooting & Tuning Guide

### LNA Won't Converge in DC

**Cause:** Initial bias point guess too far from solution.
**Fix:** Add initial conditions (Edit → Simulation → Initial Conditions) at key nodes:
```
V(net_gate1) = 0.7
V(VDD) = 1.8
V(net_d1) = 1.1
```

### S11 Not Minimized at 2.4 GHz

S11 minimum is at wrong frequency → Lg is wrong.
Lg shift needed = current_f0 / 2.4G × Lg_current
Tune Lg in 0.5 nH steps. Also: verify Cpad value (pad capacitance shifts resonance).

### NF Too High (> 3 dB)

1. Check Q of Ls and Lg inductors. If Q=5 (on-chip), NF penalty ≈ 1 dB over bond wire (Q=20).
2. Verify M1 is biased at minimum NF point (not necessarily maximum gain point).
3. Excess NF from M2 cascode: ensure M2 gate is properly bypassed at RF frequencies.

### Mixer DC Convergence Fails

1. Start with ideal tail current source (replace Mtail with isource dc=4m)
2. Run DC to verify RF pair biases correctly
3. Then replace with NMOS current mirror

### Mixer Conversion Gain Too Low

If CG < 4 dB:
1. Check LO amplitude is sufficient to fully switch quad (need > 2×Vov = 200 mVpeak)
2. Increase RL (careful: higher RL reduces IF bandwidth)
3. Verify LO frequency: must be 2.2 GHz, not 2.4 GHz
4. Check differential LO is truly 180° out of phase

### Filter Center Frequency Drifts

f0 depends on Gm/C ratio. In 180nm:
- Cox variation: ±10%
- Vth variation: ±50 mV → gm changes
- Temperature: +25°C → gm drops ~2% per °C

Add ±20% tuning range to Gm cells via programmable bias current.

### Filter Not Oscillating at DC but Oscillates in Transient

Common-mode feedback (CMFB) is unstable. Fix:
1. Add Miller capacitor in CMFB amp (increases PM)
2. Reduce CMFB gain (add resistor in feedback path)
3. In first-pass: replace with ideal CM voltage source at output

### PSS Convergence Issues (Long Runtime or No Convergence)

1. Reduce number of harmonics
2. Use shooting Newton method instead of harmonic balance
3. Increase `tstab` (stabilization time): try 50n or 100n
4. Set `errpreset=liberal` for first pass (faster, less accurate)
5. For two-tone IIP3: use PAC approach instead of direct two-tone PSS if possible

---

## 10. Verification Checklist & Deliverables

### 12 Metrics for Resume / Report

| # | Metric | Block | Target | Your Result |
|---|--------|-------|--------|-------------|
| 1 | S21 at 2.4 GHz | LNA | > 15 dB | |
| 2 | S11 at 2.4 GHz | LNA | < -10 dB | |
| 3 | NF at 2.4 GHz | LNA | < 2.5 dB | |
| 4 | IIP3 | LNA | > -5 dBm | |
| 5 | K-factor | LNA | > 1 | |
| 6 | Conversion Gain | Mixer | > 6 dB | |
| 7 | DSB NF | Mixer | < 12 dB | |
| 8 | IIP3 | Mixer | > +5 dBm | |
| 9 | 3-dB Bandwidth | IF Filter | 20 MHz ± 5% | |
| 10 | Stopband Rejection | IF Filter | > 40 dB | |
| 11 | Cascade NF | System | < 4 dB | |
| 12 | Receiver Sensitivity | System | < -85 dBm | |

### Documentation to Produce

1. Schematic screenshots for each block (LNA, Mixer, Filter)
2. Simulation waveforms:
   - LNA: S11/S21 vs frequency, NF vs frequency
   - Mixer: IF output spectrum, conversion gain vs IF frequency
   - Filter: |H(f)| AC response, group delay
   - Cascade: IIP3 extrapolation plot, system NF vs frequency
3. Cascade analysis table (from cascade_analysis.py)
4. Comparison with Project 1 BER measurements

### Project Timeline Reminder

```
Week 1:
  Days 1-2: LNA schematic + DC + S-parameters
  Day 3:    LNA NF + IIP3 + tuning
  Days 4-5: Mixer schematic + DC + PSS CG

Week 2:
  Days 1-2: Mixer NF + IIP3 + port isolation
  Days 3-4: IF Filter schematic + AC + tuning
  Day 5:    Filter noise + IIP3

Week 3:
  Days 1-2: Cascade testbench — connect all blocks
  Day 3:    Cascade Friis verification + OFDM transient
  Days 4-5: Documentation, plots, report
```

---

## Appendix A: Key Equations Reference

### Friis Noise Figure (cascade)
```
F_total = F1 + (F2-1)/G1 + (F3-1)/(G1×G2) + ...
NF_total = 10×log10(F_total)  [dB]
F = 10^(NF/10),  G = 10^(Gain_dB/10)
```

### Cascade IIP3
```
1/IIP3_cascade ≈ 1/IIP3_1 + G1/IIP3_2 + G1×G2/IIP3_3
(all values in linear power, Watts)
```

### Receiver Sensitivity
```
S = kTB + NF + SNR_required
kTB = -174 dBm/Hz + 10×log10(BW_Hz)  [dBm]
For BW=20MHz: kTB = -174 + 73.0 = -101 dBm
```

### SFDR (Spurious-Free Dynamic Range)
```
SFDR = (2/3) × (IIP3 - noise_floor)  [dB]
```

### LNA Input Impedance (inductive source degen)
```
Zin(jω) = jω(Lg + Ls) + 1/(jωCgs) + ωT×Ls
At resonance: Im[Zin] = 0,  Re[Zin] = ωT×Ls = 50 Ω
ωT = gm/Cgs = 2π×fT
```

### Gm-C Biquad BPF
```
H(s) = (Gm1/C)×s / [s² + (Gm3/C)×s + Gm1×Gm2/C²]
ω0 = √(Gm1×Gm2)/C    [rad/s]
Q  = ω0×C / Gm3
BW = ω0/Q = Gm3/C    [rad/s]
```

---

*End of Project Manual — Good luck with your simulations!*
