"""
cascade_analysis.py
-------------------
RF Receiver Front-End Cascade Analysis
Computes Friis cascade NF, IIP3, and receiver sensitivity.

Based on: Project 1 OFDM RX Front-End
  - 2.4 GHz RF, 200 MHz IF, 20 MHz OFDM channel
  - QPSK BER target: 10^-3 at Eb/N0 = 6.8 dB
  - 16-QAM BER target: 10^-3 at Eb/N0 = 10.5 dB

Usage:
  python cascade_analysis.py
  Prints all cascade metrics and plots gain/NF/IIP3 profile.
"""

import os
import numpy as np
import matplotlib.pyplot as plt

# Save plots relative to the project root (one level up from scripts/)
_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
_PLOTS_DIR   = os.path.join(_SCRIPT_DIR, "..", "plots")
os.makedirs(_PLOTS_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# BLOCK SPECIFICATIONS (from individual block simulations)
# Update these with your measured Spectre results
# ─────────────────────────────────────────────────────────────

blocks = [
    {
        "name": "LNA",
        "gain_dB":  15.0,   # S21 at 2.4 GHz (dB)
        "NF_dB":     2.5,   # Noise figure (dB)
        "IIP3_dBm": -5.0,   # Input-referred IIP3 (dBm)
    },
    {
        "name": "Mixer",
        "gain_dB":   6.0,   # Conversion gain (dB)
        "NF_dB":    12.0,   # DSB noise figure (dB)
        "IIP3_dBm": +5.0,   # Input-referred IIP3 (dBm)
    },
    {
        "name": "IF Filter",
        "gain_dB":  -2.0,   # Insertion loss (negative = loss)
        "NF_dB":     3.0,   # NF = insertion loss (passive) or OTA noise
        "IIP3_dBm": +10.0,  # IIP3 of Gm-C filter (very linear)
    },
]

# ─────────────────────────────────────────────────────────────
# SYSTEM PARAMETERS
# ─────────────────────────────────────────────────────────────
T_kelvin     = 290          # Room temperature (Kelvin)
BW_Hz        = 20e6         # OFDM channel bandwidth (20 MHz)
k_boltzmann  = 1.38e-23     # Boltzmann constant (J/K)
SNR_QPSK     = 9.8          # Required SNR for QPSK BER=10^-3 (dB)
SNR_16QAM    = 13.5         # Required SNR for 16-QAM BER=10^-3 (dB)
Eb_N0_QPSK   = 6.8          # Eb/N0 for QPSK (dB)
Eb_N0_16QAM  = 10.5         # Eb/N0 for 16-QAM (dB)
bits_per_sym_QPSK  = 2      # QPSK: 2 bits/symbol
bits_per_sym_16QAM = 4      # 16-QAM: 4 bits/symbol
PAPR_dB      = 11.0         # Measured OFDM PAPR (dB)


def dB_to_linear(x_dB):
    """Convert dB to linear power ratio."""
    return 10 ** (x_dB / 10)

def linear_to_dB(x_lin):
    """Convert linear power ratio to dB."""
    return 10 * np.log10(x_lin)

def dBm_to_watts(x_dBm):
    """Convert dBm to Watts."""
    return 1e-3 * 10 ** (x_dBm / 10)

def watts_to_dBm(x_W):
    """Convert Watts to dBm."""
    return 10 * np.log10(x_W / 1e-3)


# ─────────────────────────────────────────────────────────────
# FRIIS CASCADE NOISE FIGURE
# ─────────────────────────────────────────────────────────────
def friis_cascade_NF(blocks):
    """
    Compute cascade NF using Friis formula.
    NF_total = F1 + (F2-1)/G1 + (F3-1)/(G1*G2) + ...
    where F = linear noise factor = 10^(NF_dB/10)
          G = linear power gain   = 10^(gain_dB/10)
    """
    F_list = [dB_to_linear(b["NF_dB"]) for b in blocks]
    G_list = [dB_to_linear(b["gain_dB"]) for b in blocks]

    F_cascade = F_list[0]
    G_cumulative = G_list[0]

    for i in range(1, len(blocks)):
        F_cascade += (F_list[i] - 1) / G_cumulative
        G_cumulative *= G_list[i]

    NF_cascade_dB = linear_to_dB(F_cascade)
    return F_cascade, NF_cascade_dB, G_cumulative


# ─────────────────────────────────────────────────────────────
# CASCADE IIP3 (Cascaded Intercept Point)
# ─────────────────────────────────────────────────────────────
def cascade_IIP3(blocks):
    """
    Compute cascade input-referred IIP3.
    Assumes voltage-based approximation:
    1/IIP3_cascade = 1/IIP3_1 + G1/IIP3_2 + G1*G2/IIP3_3 + ...
    (IIP3 in linear voltage amplitude ratio relative to 1mW in 50Ω)

    More practically in power (dBm):
    A_IIP3_input = input power that would cause IM3 = signal at output
    Use: 1/P_IIP3_in ≈ Σ (cumulative_gain_before_stage / P_IIP3_stage)
    where P is in linear (mW)
    """
    IIP3_linear = [dBm_to_watts(b["IIP3_dBm"]) for b in blocks]
    G_list = [dB_to_linear(b["gain_dB"]) for b in blocks]

    inv_IIP3_cascade = 1.0 / IIP3_linear[0]
    G_cumulative = G_list[0]

    for i in range(1, len(blocks)):
        inv_IIP3_cascade += G_cumulative / IIP3_linear[i]
        G_cumulative *= G_list[i]

    IIP3_cascade_W = 1.0 / inv_IIP3_cascade
    IIP3_cascade_dBm = watts_to_dBm(IIP3_cascade_W)
    return IIP3_cascade_W, IIP3_cascade_dBm


# ─────────────────────────────────────────────────────────────
# RECEIVER SENSITIVITY
# ─────────────────────────────────────────────────────────────
def receiver_sensitivity(NF_dB, BW_Hz, SNR_req_dB, T=290):
    """
    Sensitivity = kTB + NF + SNR_required
    kTB = thermal noise power in bandwidth BW
    """
    kTB_W = k_boltzmann * T * BW_Hz
    kTB_dBm = watts_to_dBm(kTB_W)
    sensitivity_dBm = kTB_dBm + NF_dB + SNR_req_dB
    return kTB_dBm, sensitivity_dBm


# ─────────────────────────────────────────────────────────────
# SFDR (Spurious-Free Dynamic Range)
# ─────────────────────────────────────────────────────────────
def compute_SFDR(IIP3_dBm, NF_dB, BW_Hz, T=290):
    """
    SFDR = (2/3) × (IIP3 - P_noise)
    P_noise = kTB + NF (noise floor at input)
    """
    kTB_W = k_boltzmann * T * BW_Hz
    kTB_dBm = watts_to_dBm(kTB_W)
    noise_floor_dBm = kTB_dBm + NF_dB
    SFDR_dB = (2.0 / 3.0) * (IIP3_dBm - noise_floor_dBm)
    return SFDR_dB, noise_floor_dBm


# ─────────────────────────────────────────────────────────────
# STAGE-BY-STAGE ANALYSIS TABLE
# ─────────────────────────────────────────────────────────────
def stage_by_stage(blocks):
    """Print cumulative gain, NF, and IIP3 at each stage output."""
    cum_gain_dB = 0
    cum_NF_dB   = None
    F_cascade   = 0

    print("\n" + "="*72)
    print(f"{'Stage':<12} {'Gain(dB)':>10} {'CumGain(dB)':>12} "
          f"{'NF(dB)':>9} {'CumNF(dB)':>11} {'IIP3(dBm)':>11}")
    print("="*72)

    G_cumulative = 1.0
    F_cascade    = dB_to_linear(blocks[0]["NF_dB"])
    G_cumulative = dB_to_linear(blocks[0]["gain_dB"])
    cum_gain_dB  = blocks[0]["gain_dB"]
    cum_NF_dB    = blocks[0]["NF_dB"]
    IIP3_cum_dBm = blocks[0]["IIP3_dBm"]

    print(f"{'Antenna':<12} {'0':>10} {'0':>12} {'0':>9} {'0':>11} {'—':>11}")
    print(f"{blocks[0]['name']:<12} {blocks[0]['gain_dB']:>10.1f} "
          f"{cum_gain_dB:>12.1f} {blocks[0]['NF_dB']:>9.1f} "
          f"{cum_NF_dB:>11.2f} {IIP3_cum_dBm:>11.1f}")

    for i in range(1, len(blocks)):
        b = blocks[i]
        F_i = dB_to_linear(b["NF_dB"])
        G_i = dB_to_linear(b["gain_dB"])

        F_cascade += (F_i - 1) / G_cumulative
        G_cumulative *= G_i
        cum_gain_dB  += b["gain_dB"]
        cum_NF_dB     = linear_to_dB(F_cascade)

        # Cascade IIP3 through stage i
        _, IIP3_cum_dBm = cascade_IIP3(blocks[:i+1])

        print(f"{b['name']:<12} {b['gain_dB']:>10.1f} "
              f"{cum_gain_dB:>12.1f} {b['NF_dB']:>9.1f} "
              f"{cum_NF_dB:>11.2f} {IIP3_cum_dBm:>11.1f}")

    print("="*72)
    return cum_gain_dB, cum_NF_dB, IIP3_cum_dBm


# ─────────────────────────────────────────────────────────────
# PLOT: IIP3 LINE EXTRAPOLATION (Visual verification)
# ─────────────────────────────────────────────────────────────
def plot_iip3_extrapolation(IIP3_dBm, NF_dB, gain_dB, title="Cascade IIP3"):
    """Plot fundamental and IM3 output power vs input power."""
    Pin_dBm = np.linspace(-100, IIP3_dBm + 10, 500)

    # Fundamental output: Pout = Pin + gain (linear regime)
    Pout_fund = Pin_dBm + gain_dB

    # IM3 output: slope = 3 in linear → 3 dB/dB on log scale
    # Pout_IM3 = 3*Pin - 2*IIP3 + gain (extrapolated)
    Pout_IM3 = 3 * Pin_dBm - 2 * IIP3_dBm + gain_dB

    noise_floor_dBm = watts_to_dBm(k_boltzmann * T_kelvin * BW_Hz) + NF_dB

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(Pin_dBm, Pout_fund, 'b-', linewidth=2, label='Fundamental (1st order, slope=1)')
    ax.plot(Pin_dBm, Pout_IM3,  'r--', linewidth=2, label='IM3 product (3rd order, slope=3)')
    ax.axhline(noise_floor_dBm, color='gray', linestyle=':', label=f'Noise floor = {noise_floor_dBm:.1f} dBm')
    ax.axvline(IIP3_dBm, color='green', linestyle='-.', label=f'IIP3 = {IIP3_dBm:.1f} dBm')

    ax.set_xlabel('Input Power (dBm)', fontsize=12)
    ax.set_ylabel('Output Power (dBm)', fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.4)
    ax.set_xlim([-100, IIP3_dBm + 10])
    ax.set_ylim([-120, IIP3_dBm + gain_dB + 15])
    plt.tight_layout()
    plt.savefig(os.path.join(_PLOTS_DIR, 'cascade_iip3_extrapolation.png'), dpi=150)
    plt.show()
    print("Saved: cascade_iip3_extrapolation.png")


# ─────────────────────────────────────────────────────────────
# PLOT: NF CONTRIBUTION PER STAGE
# ─────────────────────────────────────────────────────────────
def plot_nf_contribution(blocks):
    """Show how each stage contributes to cascade NF."""
    F_list = [dB_to_linear(b["NF_dB"]) for b in blocks]
    G_list = [dB_to_linear(b["gain_dB"]) for b in blocks]

    contributions_linear = [F_list[0] - 1]  # Stage 1 contribution
    G_cum = G_list[0]
    for i in range(1, len(blocks)):
        contributions_linear.append((F_list[i] - 1) / G_cum)
        G_cum *= G_list[i]

    contributions_dB = [linear_to_dB(1 + c) for c in contributions_linear]
    names = [b["name"] for b in blocks]

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(names, contributions_dB, color=['#2196F3', '#FF9800', '#4CAF50'])
    ax.set_ylabel('NF Contribution (dB)', fontsize=12)
    ax.set_title('Cascade NF Contribution by Stage (Friis Analysis)', fontsize=12)
    for bar, val in zip(bars, contributions_dB):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f'{val:.2f} dB', ha='center', va='bottom', fontsize=11)
    ax.grid(axis='y', alpha=0.4)
    plt.tight_layout()
    plt.savefig(os.path.join(_PLOTS_DIR, 'cascade_nf_contribution.png'), dpi=150)
    plt.show()
    print("Saved: cascade_nf_contribution.png")


# ─────────────────────────────────────────────────────────────
# MAIN ANALYSIS
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "╔" + "═"*68 + "╗")
    print("║  2.4 GHz RF RX FRONT-END CASCADE ANALYSIS                        ║")
    print("║  LNA → Gilbert Mixer → 4th-Order Gm-C IF Filter                  ║")
    print("╚" + "═"*68 + "╝")

    # ── Stage-by-stage table ──
    cum_gain_dB, cum_NF_dB, IIP3_cascade_dBm = stage_by_stage(blocks)

    # ── Full cascade results ──
    F_casc, NF_casc_dB, G_casc_lin = friis_cascade_NF(blocks)
    _, IIP3_casc_dBm = cascade_IIP3(blocks)
    total_gain_dB = sum(b["gain_dB"] for b in blocks)

    print(f"\n{'─'*50}")
    print(f" CASCADE SUMMARY")
    print(f"{'─'*50}")
    print(f"  Total Gain      : {total_gain_dB:.1f} dB")
    print(f"  Cascade NF      : {NF_casc_dB:.2f} dB   (target: < 8 dB)")
    print(f"  Cascade IIP3    : {IIP3_casc_dBm:.2f} dBm  (target: > -70 dBm input)")
    print(f"  Cascade NF Ratio: {F_casc:.4f}")

    # ── Sensitivity ──
    kTB_dBm, sens_QPSK   = receiver_sensitivity(NF_casc_dB, BW_Hz, SNR_QPSK)
    _, sens_16QAM         = receiver_sensitivity(NF_casc_dB, BW_Hz, SNR_16QAM)

    print(f"\n{'─'*50}")
    print(f" RECEIVER SENSITIVITY")
    print(f"{'─'*50}")
    print(f"  Thermal noise floor (kTB):  {kTB_dBm:.1f} dBm  (20 MHz BW)")
    print(f"  + Cascade NF:               {NF_casc_dB:.2f} dB")
    print(f"  + SNR for QPSK BER=10⁻³:   {SNR_QPSK} dB")
    print(f"  = Sensitivity (QPSK):      {sens_QPSK:.1f} dBm")
    print(f"")
    print(f"  + SNR for 16-QAM BER=10⁻³: {SNR_16QAM} dB")
    print(f"  = Sensitivity (16-QAM):    {sens_16QAM:.1f} dBm")
    print(f"")
    print(f"  Project 1 BER target: < 10⁻³  ✓ (if sensitivity < -88 dBm)")

    # ── SFDR ──
    SFDR_dB, noise_floor_dBm = compute_SFDR(IIP3_casc_dBm, NF_casc_dB, BW_Hz)
    print(f"\n{'─'*50}")
    print(f" DYNAMIC RANGE")
    print(f"{'─'*50}")
    print(f"  Input noise floor:  {noise_floor_dBm:.1f} dBm")
    print(f"  Cascade IIP3:       {IIP3_casc_dBm:.2f} dBm")
    print(f"  SFDR:               {SFDR_dB:.1f} dB")
    print(f"  PAPR (from Proj.1): {PAPR_dB} dB → requires SFDR > {PAPR_dB} dB")
    if SFDR_dB > PAPR_dB:
        print(f"  SFDR check: PASS ✓  ({SFDR_dB:.1f} > {PAPR_dB} dB)")
    else:
        print(f"  SFDR check: FAIL ✗  ({SFDR_dB:.1f} < {PAPR_dB} dB) — improve IIP3!")

    # ── OFDM PAPR / Peak Power Check ──
    sensitivity_floor_dBm = sens_QPSK
    peak_input_dBm = sensitivity_floor_dBm + PAPR_dB
    print(f"\n{'─'*50}")
    print(f" PAPR / LINEARITY CHECK")
    print(f"{'─'*50}")
    print(f"  Sensitivity floor:    {sensitivity_floor_dBm:.1f} dBm")
    print(f"  OFDM PAPR:            {PAPR_dB} dB")
    print(f"  Peak input power:     {peak_input_dBm:.1f} dBm")
    print(f"  Cascade IIP3:         {IIP3_casc_dBm:.2f} dBm")
    margin = IIP3_casc_dBm - peak_input_dBm
    print(f"  IIP3 margin over peak:{margin:.1f} dB (target > 10 dB)")

    # ── Eb/N0 Verification ──
    # SNR = Eb/N0 + 10*log10(bits_per_sym) - 10*log10(subcarriers/BW·...)
    # For OFDM QPSK: SNR_req = Eb/N0 + 10*log10(R) where R = code rate
    # Simplified (uncoded): SNR_QPSK = Eb/N0 + 10*log10(bits/sym) = 6.8 + 3 = 9.8 dB
    print(f"\n{'─'*50}")
    print(f" Eb/N0 → SNR CONVERSION (Project 1 Link)")
    print(f"{'─'*50}")
    print(f"  QPSK:   Eb/N0 = {Eb_N0_QPSK} dB → SNR = {Eb_N0_QPSK + 10*np.log10(bits_per_sym_QPSK):.1f} dB")
    print(f"  16-QAM: Eb/N0 = {Eb_N0_16QAM} dB → SNR = {Eb_N0_16QAM + 10*np.log10(bits_per_sym_16QAM):.1f} dB")

    # ── Plots ──
    print(f"\n{'─'*50}")
    print(" Generating plots...")
    plot_iip3_extrapolation(IIP3_casc_dBm, NF_casc_dB, total_gain_dB,
                             title=f"Cascade IIP3 Extrapolation (IIP3={IIP3_casc_dBm:.1f} dBm)")
    plot_nf_contribution(blocks)

    print(f"\n{'='*50}")
    print(" Analysis complete. Update block specs with Spectre results.")
    print(f"{'='*50}\n")
