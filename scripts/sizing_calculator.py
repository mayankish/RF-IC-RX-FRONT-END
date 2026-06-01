"""
sizing_calculator.py
--------------------
RF Block Transistor & Component Sizing Calculator
For: 2.4 GHz LNA, Gilbert Cell Mixer, Gm-C IF Filter
Process: Generic 180nm CMOS (TSMC-like parameters)

Computes:
  - LNA: W, Ls, Lg, Ld, bias point
  - Mixer: W_RF, W_LO, tail current, load resistance
  - Filter: Gm values, capacitor values, Q-factor sizing

Usage:
  python sizing_calculator.py
"""

import numpy as np

# ─────────────────────────────────────────────────────────────
# 180nm CMOS PROCESS PARAMETERS (TSMC-like, room temperature)
# Replace with your actual PDK values from datasheet
# ─────────────────────────────────────────────────────────────
class Process180nm:
    # NMOS
    un_Cox  = 270e-6    # μn·Cox (A/V²)
    Vth_n   = 0.50      # NMOS threshold voltage (V)
    Lmin    = 180e-9    # Minimum channel length (m)
    Cox     = 8.6e-15   # Gate oxide capacitance per unit area (F/μm²) → 8.6 fF/μm²
    Cgso    = 0.5e-15   # Gate-source overlap cap per unit width (F/μm)

    # PMOS
    up_Cox  = 70e-6     # μp·Cox (A/V²)
    Vth_p   = -0.50     # PMOS threshold voltage (V)

    # RF parameters
    fT_max  = 60e9      # Peak fT for NMOS at optimal bias (~60 GHz for 180nm)

    # Supply
    VDD     = 1.8       # (V)

proc = Process180nm()


def gm_from_ID_W_L(ID, W, L, proc=proc):
    """Compute gm = sqrt(2 * un_Cox * W/L * ID)  [A/V]"""
    return np.sqrt(2 * proc.un_Cox * (W/L) * ID)

def ID_from_Vov_W_L(Vov, W, L, proc=proc):
    """Compute ID = 0.5 * un_Cox * W/L * Vov²  [A]"""
    return 0.5 * proc.un_Cox * (W/L) * Vov**2

def Cgs_approx(W, L, Cgso=proc.Cgso, Cox=proc.Cox):
    """Approximate Cgs = (2/3)*Cox*W*L + Cgso*W  [F]  (W,L in meters)"""
    W_um = W * 1e6  # convert to μm for Cox formula
    L_um = L * 1e6
    return (2/3) * Cox * W_um * L_um * 1e-12 + Cgso * W_um * 1e-12
    # Note: Cox is in fF/μm², so Cox*W*L is in fF → ×1e-15 for Farads

def Cgs_approx_SI(W, L):
    """Cgs in Farads, W and L in meters.
    proc.Cox  = 8.6e-15 F/μm²  → convert to F/m²: × (1e6)² = × 1e12
    proc.Cgso = 0.5e-15 F/μm   → convert to F/m:  × 1e6
    """
    # Cox: 8.6e-15 F/μm² × 1e12 (μm²/m²) = 8.6e-3 F/m²
    Cox_Fm2 = proc.Cox * 1e12
    Cgs_intrinsic = (2/3) * Cox_Fm2 * W * L

    # Cgso: 0.5e-15 F/μm × 1e6 (μm/m) = 0.5e-9 F/m
    Cgso_Fm = proc.Cgso * 1e6
    Cgs_overlap = Cgso_Fm * W

    return Cgs_intrinsic + Cgs_overlap

def fT_transistor(W, L, ID):
    """Compute fT = gm / (2π*Cgs)  [Hz]"""
    gm   = gm_from_ID_W_L(ID, W, L)
    Cgs  = Cgs_approx_SI(W, L)
    if Cgs <= 0:
        return 0
    return gm / (2 * np.pi * Cgs)

# ─────────────────────────────────────────────────────────────
# LNA SIZING
# ─────────────────────────────────────────────────────────────
def lna_sizing():
    print("\n" + "═"*60)
    print("  LNA SIZING — 2.4 GHz Cascode with Inductive Source Degen.")
    print("═"*60)

    f0   = 2.4e9     # Center frequency (Hz)
    w0   = 2*np.pi*f0
    Zin  = 50.0      # Target input impedance (Ω)
    VDD  = proc.VDD
    PDC_budget = 10e-3   # 10 mW power budget

    ID_max = PDC_budget / VDD
    print(f"\nPower budget: {PDC_budget*1e3:.0f} mW → ID_max = {ID_max*1e3:.1f} mA at VDD={VDD}V")

    # Choose ID = 5 mA (leaves headroom)
    ID = 5e-3
    # For optimal NF in 180nm: Vov ≈ 0.15-0.25V
    Vov = 0.20    # V
    # W/L from Vov and ID: ID = 0.5*un_Cox*(W/L)*Vov² → W/L = 2*ID/(un_Cox*Vov²)
    WL_ratio = 2 * ID / (proc.un_Cox * Vov**2)
    L = proc.Lmin  # Use minimum L for maximum fT
    W = WL_ratio * L

    print(f"\n[M1/M2 Transistor Sizing]")
    print(f"  Target ID  = {ID*1e3:.1f} mA")
    print(f"  Target Vov = {Vov*1e3:.0f} mV")
    print(f"  W/L ratio  = {WL_ratio:.1f}")
    print(f"  L          = {L*1e9:.0f} nm")
    print(f"  W (total)  = {W*1e6:.1f} μm  → use {int(W*1e6/5)+1} fingers × 5 μm each")

    # Verify gm and fT
    gm  = gm_from_ID_W_L(ID, W, L)
    Cgs = Cgs_approx_SI(W, L)
    fT  = gm / (2*np.pi*Cgs)
    wT  = 2*np.pi*fT

    print(f"\n[Transistor Parameters at Bias Point]")
    print(f"  gm         = {gm*1e3:.2f} mA/V")
    print(f"  Cgs        = {Cgs*1e15:.1f} fF")
    print(f"  fT         = {fT/1e9:.1f} GHz   (target > 5×f0 = 12 GHz)")
    print(f"  Vgs_bias   ≈ Vth + Vov = {proc.Vth_n + Vov:.2f} V")

    # Source degeneration inductor Ls: Re[Zin] = gm*Ls/Cgs = wT*Ls = 50Ω
    Ls = Zin / wT  # from wT*Ls = Re[Zin]
    print(f"\n[Inductor Sizing]")
    print(f"  Ls (source degen) = {Ls*1e9:.3f} nH")
    print(f"    Condition: wT × Ls = {wT:.2e} × {Ls:.2e} = {wT*Ls:.1f} Ω ≈ 50 Ω ✓")

    # Gate inductor for resonance: w0²*(Lg+Ls)*Cgs = 1
    Lg_plus_Ls = 1 / (w0**2 * Cgs)
    Lg = Lg_plus_Ls - Ls
    print(f"  Lg (gate matching) = {Lg*1e9:.2f} nH")
    print(f"    Resonance: (Lg+Ls)={Lg_plus_Ls*1e9:.2f} nH, Cgs={Cgs*1e15:.1f} fF @ {f0/1e9:.1f} GHz")
    print(f"    Note: If Lg > 10 nH, use bond wire or off-chip inductor")
    print(f"    On-chip spirals in 180nm: typically 1-10 nH range")

    # Drain load inductor: resonate with drain parasitic + load cap at 2.4 GHz
    # Assume Cload ≈ 200 fF (mixer input + routing)
    Cload = 200e-15
    Ld = 1 / (w0**2 * Cload)
    print(f"  Ld (drain load)   = {Ld*1e9:.2f} nH  (for Cload={Cload*1e15:.0f} fF)")

    # Stability (Rollett K-factor) — approximate check
    # For cascode: K >> 1 typically due to reduced S12
    print(f"\n[Stability]")
    print(f"  Cascode topology inherently provides K > 1 for most bias points.")
    print(f"  Verify in Spectre: K-factor from S-parameters must be > 1 at all freqs.")
    print(f"  If unstable: add small resistor (10-50Ω) at gate of M2 (cascode)")

    # Power dissipation
    PDC = VDD * ID
    print(f"\n[Power Budget]")
    print(f"  ID = {ID*1e3:.1f} mA, VDD = {VDD}V → PDC = {PDC*1e3:.1f} mW  (budget: {PDC_budget*1e3:.0f} mW)")

    # NF estimate (Friis for FET noise)
    # NF_min ≈ 1 + 2*γ*δ*gm/gdo × (f/fT)   (simplified Pospieszalski model)
    # For 180nm at 2.4 GHz/60GHz: NF_min ≈ 0.5-1.5 dB achievable
    gamma = 2.0/3.0   # channel noise coefficient (long-channel)
    delta = 4.0/3.0   # gate noise coefficient
    NF_min_approx_linear = 1 + 2 * gamma * delta * f0/fT
    NF_min_approx_dB = 10*np.log10(NF_min_approx_linear)
    print(f"\n[NF Estimate]")
    print(f"  NF_min (simplified) ≈ {NF_min_approx_dB:.2f} dB at {f0/1e9:.1f} GHz")
    print(f"  Practical NF with matching: 1.5-2.5 dB (tune Lg/Ls for minimum)")

    return {"W": W, "L": L, "ID": ID, "gm": gm, "Cgs": Cgs, "fT": fT,
            "Ls": Ls, "Lg": Lg, "Ld": Ld}


# ─────────────────────────────────────────────────────────────
# MIXER SIZING (Gilbert Cell)
# ─────────────────────────────────────────────────────────────
def mixer_sizing():
    print("\n" + "═"*60)
    print("  MIXER SIZING — Double-Balanced Gilbert Cell")
    print("═"*60)

    VDD = proc.VDD
    PDC_budget = 15e-3   # 15 mW
    ISS = 4e-3           # Tail current (total): 4 mA → each RF branch: 2 mA
    ID_rf = ISS / 2      # Each M1/M2 carries ISS/2

    print(f"\nTail current ISS = {ISS*1e3:.0f} mA → each RF transistor: {ID_rf*1e3:.0f} mA")

    # RF pair (M1, M2): maximize gm for conversion gain
    # Gm of mixer ≈ (2/π) × gm1  (for ideal switching, square-wave LO)
    Vov_rf = 0.20   # V overdrive for RF pair
    WL_rf = 2 * ID_rf / (proc.un_Cox * Vov_rf**2)
    L_rf  = proc.Lmin
    W_rf  = WL_rf * L_rf
    gm_rf = gm_from_ID_W_L(ID_rf, W_rf, L_rf)

    print(f"\n[RF Transconductor Pair M1,M2]")
    print(f"  ID per device = {ID_rf*1e3:.1f} mA")
    print(f"  Vov           = {Vov_rf*1e3:.0f} mV")
    print(f"  W/L           = {WL_rf:.0f}")
    print(f"  W (total)     = {W_rf*1e6:.0f} μm  ({int(W_rf*1e6/5)} fingers × 5 μm)")
    print(f"  gm_rf         = {gm_rf*1e3:.1f} mA/V")

    # Conversion gain ≈ (2/π) × gm × RL  (for square-wave LO)
    conv_gain_target_lin = 10 ** (6/20)   # 6 dB → 2.0 linear
    RL_needed = conv_gain_target_lin / ((2/np.pi) * gm_rf)
    print(f"\n[Load Resistor]")
    print(f"  Target CG = 6 dB ({conv_gain_target_lin:.2f} V/V)")
    print(f"  CG ≈ (2/π) × gm × RL → RL = {RL_needed:.0f} Ω")
    print(f"  Use RL = 300 Ω (round number, adjust in simulation)")
    RL = 300
    CG_actual_dB = 20*np.log10((2/np.pi)*gm_rf*RL)
    print(f"  Actual CG estimate = {CG_actual_dB:.1f} dB")

    # IF bandwidth: BW_IF = 1/(2π*RL*Cload)
    # Need BW_IF >> 20 MHz (OFDM channel)
    Cload_mix = 100e-15  # Mixer output parasitic + IF filter input
    BW_IF = 1 / (2*np.pi * RL * Cload_mix)
    print(f"  IF bandwidth ≈ {BW_IF/1e6:.0f} MHz  (with Cload={Cload_mix*1e15:.0f} fF)")
    print(f"  Must be >> 20 MHz ({'✓' if BW_IF > 100e6 else '✗ — reduce RL or add buffer'})")

    # LO switching quad (M3-M6): should switch fast → minimize Vov
    # Overdrive < 100mV so LO can fully switch with small swing
    Vov_lo = 0.10
    ID_lo  = ID_rf   # each LO device carries same current as RF
    WL_lo  = 2 * ID_lo / (proc.un_Cox * Vov_lo**2)
    W_lo   = WL_lo * proc.Lmin
    print(f"\n[LO Switching Quad M3-M6]")
    print(f"  Vov_lo = {Vov_lo*1e3:.0f} mV (smaller → faster switching, less 1/f noise)")
    print(f"  W/L    = {WL_lo:.0f}")
    print(f"  W      = {W_lo*1e6:.0f} μm  ({int(W_lo*1e6/4)} fingers × 4 μm)")

    # LO drive requirement: LO must fully switch quad
    # Minimum LO amplitude ≈ 2×Vov of switching devices
    VLO_min = 2 * Vov_lo
    print(f"  Min LO amplitude ≈ 2×Vov = {VLO_min*1e3:.0f} mV → use 400 mVpeak (20 dBm safety margin)")

    # IIP3 of Gilbert cell (approximate)
    # IIP3 ≈ 2*√2 × Vov_rf   (from 3rd-order Taylor expansion of differential pair)
    IIP3_V = 2*np.sqrt(2) * Vov_rf   # Vpeak at input
    # Convert to dBm (50Ω): P = V²/(2×50)×1000 mW
    IIP3_W = (IIP3_V**2) / (2*50) * 1e-3   # mW ... no, power in W
    IIP3_W_correct = (IIP3_V**2) / (2*50)   # V²/Ω = W (peak power)
    IIP3_dBm = 10*np.log10(IIP3_W_correct / 1e-3)
    print(f"\n[IIP3 Estimate]")
    print(f"  IIP3 (input) ≈ 2√2 × Vov = {IIP3_V*1e3:.0f} mVpeak ≈ {IIP3_dBm:.1f} dBm")
    print(f"  Target: > +5 dBm — increase Vov or add source degen. resistors")

    # Power check
    PDC = VDD * ISS
    print(f"\n[Power Budget]")
    print(f"  PDC = VDD × ISS = {VDD} × {ISS*1e3:.0f}mA = {PDC*1e3:.0f} mW  (budget: {PDC_budget*1e3:.0f} mW) ✓")

    return {"W_rf": W_rf, "W_lo": W_lo, "ISS": ISS, "RL": RL, "gm_rf": gm_rf}


# ─────────────────────────────────────────────────────────────
# IF FILTER SIZING (Gm-C Bandpass)
# ─────────────────────────────────────────────────────────────
def if_filter_sizing():
    print("\n" + "═"*60)
    print("  IF FILTER SIZING — 4th-Order Gm-C Bandpass, 200 MHz / 20 MHz BW")
    print("═"*60)

    f0   = 200e6     # Center frequency
    BW   = 20e6      # 3-dB bandwidth
    w0   = 2*np.pi*f0

    # 4th-order Butterworth bandpass: two 2nd-order sections
    # Q factors from prototype table:
    #   4th-order BPF from 2nd-order lowpass prototype ω=1, Q=1/√2 (Butterworth)
    #   Bandpass Q: Q_BPF = f0/BW × Q_LP_prototype for each section
    #   For Butterworth: Q_LP = [0.7071, 0.7071] for 2nd-order
    #   For 4th-order: use pairs with Q = [0.5412, 1.3066] (Butterworth bandpass)
    Q1 = f0/BW * 0.5412   # Lower Q section
    Q2 = f0/BW * 1.3066   # Higher Q section (narrower, sharper skirts)

    print(f"\nBandpass design: f0={f0/1e6:.0f} MHz, BW={BW/1e6:.0f} MHz, f0/BW={f0/BW:.1f}")
    print(f"  Biquad Q values: Q1={Q1:.2f}, Q2={Q2:.2f}")
    print(f"  (From 4th-order Butterworth BPF prototype)")

    # Choose capacitor value
    C = 500e-15   # 500 fF — practical on-chip MIM/MOM cap size

    # Gm values for each section
    Gm_int = w0 * C          # Integration Gm (sets ω0)
    Gm_Q1  = w0 * C / Q1     # Q-control Gm for section 1
    Gm_Q2  = w0 * C / Q2     # Q-control Gm for section 2

    print(f"\n[Gm-C Biquad Component Values] (C = {C*1e15:.0f} fF)")
    print(f"  Gm_int  = ω0 × C = {w0:.3e} × {C:.2e} = {Gm_int*1e6:.1f} μA/V  (both sections)")
    print(f"  Gm_Q1   = ω0 × C / Q1 = {Gm_Q1*1e6:.1f} μA/V  (Q1={Q1:.2f})")
    print(f"  Gm_Q2   = ω0 × C / Q2 = {Gm_Q2*1e6:.1f} μA/V  (Q2={Q2:.2f})")

    # Gm cell sizing: use simple diff pair, ID for each Gm cell
    # gm ≈ √(2 × un_Cox × W/L × ID)  → ID = gm²/(2 × un_Cox × W/L)
    # For W=5μm, L=500nm: un_Cox × W/L = 270μ × 10 = 2.7 mA/V²
    W_gm = 5e-6
    L_gm = 500e-9
    kn_Wl = proc.un_Cox * (W_gm/L_gm)   # ≈ 2.7 mA/V²
    ID_int = Gm_int**2 / (2 * kn_Wl)
    ID_Q1  = Gm_Q1**2  / (2 * kn_Wl)
    ID_Q2  = Gm_Q2**2  / (2 * kn_Wl)

    print(f"\n[OTA (Gm Cell) Bias Currents] (W={W_gm*1e6:.0f}μm, L={L_gm*1e9:.0f}nm)")
    print(f"  ID per Gm_int cell = {ID_int*1e6:.1f} μA   (each diff-pair tail)")
    print(f"  ID per Gm_Q1  cell = {ID_Q1*1e6:.1f} μA")
    print(f"  ID per Gm_Q2  cell = {ID_Q2*1e6:.1f} μA")
    print(f"  Note: If ID < 10 μA, upscale W or use larger L for stability")

    # Total number of Gm cells: each biquad uses 4 Gm cells (Gm1,Gm2,Gm3,Gm4)
    # 2 biquads → 8 Gm cells total
    # Section 1: 2×Gm_int + 2×Gm_Q1 (approx)
    # Section 2: 2×Gm_int + 2×Gm_Q2
    total_ID = 2*(2*ID_int + 2*ID_Q1) + 2*(2*ID_int + 2*ID_Q2)  # rough estimate
    PDC_filter = proc.VDD * total_ID
    print(f"\n[Power Estimate]")
    print(f"  Approx total bias current: {total_ID*1e6:.0f} μA")
    print(f"  PDC estimate: {PDC_filter*1e3:.1f} mW  (target < 20 mW)")

    # Tuning range needed for process variation
    # f0 varies by ±20% in 180nm → Gm must be tunable ±20%
    # Achieved by adjusting tail current in OTA (Gm ∝ √ID)
    # For 20% Gm change: ΔID/ID ≈ 44% → need ~2:1 tuning range in current DAC
    print(f"\n[Process Variation / Tuning]")
    print(f"  f0 variation in 180nm: ±20% (Gm and C mismatch)")
    print(f"  Required Gm tuning range: 0.8× to 1.2× nominal")
    print(f"  ID tuning range: 0.64× to 1.44× nominal (since Gm ∝ √ID)")
    print(f"  Implement: 5-bit binary-weighted current DAC for Gm bias")

    # Stopband verification
    # For 4th-order BPF, attenuation at Δf from center:
    # At Δf = ±40 MHz from 200 MHz (i.e., 160 MHz and 240 MHz):
    # Normalized frequency: Ω = (f - f0) × (f0/BW) / f0 = Δf/BW × f0/f = ...
    # For BPF: use lowpass prototype mapping
    # At 2 × BW (40 MHz from center), 4th-order Butterworth attenuates ~24 dB
    # Need > 40 dB → consider 6th-order or add shaping
    print(f"\n[Stopband Check]")
    print(f"  At ±40 MHz from center (2×BW):")
    print(f"  4th-order Butterworth BPF attenuation ≈ 24 dB")
    print(f"  Target: > 40 dB → consider 6th-order filter (3 biquads)")
    print(f"  Alternative: add elliptic response (adds notches at stopband)")
    print(f"  For project: if 4th order gives ~24 dB, note trade-off in report")

    return {"C": C, "Gm_int": Gm_int, "Gm_Q1": Gm_Q1, "Gm_Q2": Gm_Q2, "Q1": Q1, "Q2": Q2}


# ─────────────────────────────────────────────────────────────
# SUMMARY TABLE
# ─────────────────────────────────────────────────────────────
def print_summary(lna, mix, filt):
    print("\n" + "╔" + "═"*68 + "╗")
    print("║  COMPONENT VALUE SUMMARY — Enter in Virtuoso Schematic        ║")
    print("╚" + "═"*68 + "╝")

    print(f"""
┌─────────────────────────────────────────────────────────────────┐
│ LNA (Cascode NMOS, 2.4 GHz)                                     │
│   M1/M2: W = {lna['W']*1e6:>7.1f} μm   L = 180 nm  ID = {lna['ID']*1e3:.1f} mA       │
│   Ls   = {lna['Ls']*1e9:>7.3f} nH  (source degeneration — bond wire)      │
│   Lg   = {lna['Lg']*1e9:>7.2f} nH  (gate matching — off-chip or bond wire) │
│   Ld   = {lna['Ld']*1e9:>7.2f} nH  (drain load — on-chip spiral)          │
│   gm   = {lna['gm']*1e3:>7.2f} mA/V   fT = {lna['fT']/1e9:.1f} GHz                 │
├─────────────────────────────────────────────────────────────────┤
│ MIXER (Gilbert Cell, RF=2.4G, LO=2.2G, IF=200M)                │
│   M1/M2 (RF): W = {mix['W_rf']*1e6:>5.0f} μm  L = 180 nm  ISS = {mix['ISS']*1e3:.0f} mA    │
│   M3-M6 (LO): W = {mix['W_lo']*1e6:>5.0f} μm  L = 180 nm                     │
│   RL = {mix['RL']:>5.0f} Ω  (IF load)                                 │
│   Conversion Gain ≈ {20*np.log10((2/np.pi)*mix['gm_rf']*mix['RL']):.1f} dB                       │
├─────────────────────────────────────────────────────────────────┤
│ IF FILTER (4th-order Gm-C BPF, f0=200MHz, BW=20MHz)            │
│   C (integration cap) = {filt['C']*1e15:>5.0f} fF (MIM or MOM capacitor)    │
│   Gm_int  = {filt['Gm_int']*1e6:>6.1f} μA/V  (ω0 setting, both sections)  │
│   Gm_Q1   = {filt['Gm_Q1']*1e6:>6.1f} μA/V  (Q1 = {filt['Q1']:.2f}, lower Q section)  │
│   Gm_Q2   = {filt['Gm_Q2']*1e6:>6.1f} μA/V  (Q2 = {filt['Q2']:.2f}, higher Q section) │
└─────────────────────────────────────────────────────────────────┘
""")


if __name__ == "__main__":
    lna_params  = lna_sizing()
    mix_params  = mixer_sizing()
    filt_params = if_filter_sizing()
    print_summary(lna_params, mix_params, filt_params)

    print("\n  NOTE: These values are analytical starting points.")
    print("  Always verify and tune in Spectre simulation.")
    print("  Process variation: use Monte Carlo / corner sims.\n")
