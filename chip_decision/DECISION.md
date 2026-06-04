# Tritone — Chip Manufacturing Decision (BMAD cycle 2)

**Question asked:** *What chip should we manufacture? What is the ultimate situation for the best computing system?*
**Method:** BMAD continued — a 3-member agent **council** + a **red-team QA gate**, grounded in the prior
OPU study, miras memory, and a knowledge-graph wiki (`../wiki/`).
**Status:** Gate PASS (with the red-team's corrections folded in). Decision is final and actionable.

---

## TL;DR — the answer in five lines
1. **Manufacture a *fully-digital* ternary ASIC** (bit-exact). Not analog. Not photonic. Not charge-domain CIM.
2. **Two phases:** SKY130 open-MPW *prototype* (functional/golden-vector vehicle) → TSMC **22/28 nm** *production* (digital ternary CIM or scaled systolic array) + Cortex-M33 host.
3. **Don't tape out yet.** The trigger is **clinical volume (>~500 units), a sub-5 mW envelope the FPGA can't meet, or a regulatory submission needing certified silicon.** Until one fires, the $20 FPGA + an MCU is the right vehicle.
4. **The ultimate system is a lifecycle, not a chip:** *cloud-train (exact gradients) → freeze + certify (golden vectors, SHA-256 weight lock, SBOM) → edge bit-exact digital-ternary inference.*
5. **Why digital wins here:** for a *regulated medical* workload, **determinism dominates efficiency.** Bit-exactness is an FDA prerequisite, and analog (optical / charge-domain / ReRAM) forfeits it.

---

## How the council voted

| Council member | Recommendation | One-line verdict |
|---|---|---|
| **Digital ASIC architect** | 64×64 digital ternary systolic array, SkyWater **SKY130** open MPW (~$10–12k NRE, ~5 mm², ~40 mW @ 200 MHz, ~8 GOPS, bit-exact) | Tape out — NRE is rounding error vs a clinical-study budget; determinism is structural. |
| **Analog / photonic / in-memory architect** | Reject photonics (7.8 % static floor; ~262 W tuning for a 512×512 MZI mesh; E/O–O/E overhead kills the win below N≈4096) and ReRAM (immature). Proposed charge-domain ternary SRAM CIM. | Analog photonics fails on physics; only an in-memory ternary macro is worth a look. |
| **Systems / regulatory architect** | Small digital ternary ASIC (28 nm) + cloud training + Cortex-M33 host; FPGA as dev vehicle | Bit-exact determinism is an **FDA SaMD prerequisite**; analog non-determinism fails 510(k). |
| **Red-team (QA gate)** | PASS w/ concerns: charge-domain CIM is **not** bit-exact (drop it); gate the tape-out behind explicit triggers; SKY130 = validation vehicle only; SHA-256 weight lock | The only analog "win" the council found is self-disqualified by its own determinism rule. |

**Convergence:** three independent lenses (silicon, physics, regulation) all point to the **same** answer —
a deterministic digital ternary chip for frozen-model edge inference. The one dissent (analog CIM) was an
internal contradiction the red-team removed.

---

## The decision in detail

### What to build
A **fully-digital, multiplier-free ternary inference ASIC** that preserves Tritone's bit-exact integer datapath
(weights ∈ {−1,0,+1} → mux + conditional add; 42 % zeros skipped). Determinism is the product, not a side effect.

### Manufacturing path (phased, trigger-gated)
| Phase | Chip | Node / fab | Cost / NRE | Purpose | Honest caveat |
|---|---|---|---|---|---|
| **0 (now)** | none — **stay on FPGA + Cortex-M33** | Tang Nano 9K | $20 + MCU | Dev, clinical-study instrument, OTA weight validation | Correct until a tape-out trigger fires |
| **1 (de-risk)** | 64×64 digital ternary systolic array | **SkyWater SKY130** open MPW | ~$10–12k, ~July 2026 | Validate datapath, **bit-exact MAC chain, golden-vector test rig** | 130 nm @ ~200 MHz is **not** a power/area/timing proxy — don't extrapolate 40 mW/8 GOPS |
| **2 (production)** | **Fully-digital** ternary CIM or scaled systolic array + Cortex-M33 host | **TSMC 22/28 nm** | ~$70–130k MPW NRE | Certifiable, low-power edge product | Realistic **30–150 TOPS/W** (the 1000–2941 figure is *analog* CIM — disqualified) |

### Tape-out trigger (do NOT spend NRE before one is true)
- (a) confirmed clinical deployment **> ~500 units**, **or**
- (b) a power envelope **< 5 mW** the FPGA cannot meet (wearable/implant), **or**
- (c) a regulatory submission that **requires a certified silicon BOM**.

### The ultimate computing system (the architecture)
```
   CLOUD (train)                 CERTIFY (freeze + lock)              EDGE (infer)
 ┌────────────────┐          ┌──────────────────────────┐      ┌─────────────────────┐
 │ GPU/FPGA, exact│  weights │ golden test vectors       │ load │ Cortex-M33 host     │
 │ gradients,     ├─────────►│ SHA-256 weight blob (OTP/  ├─────►│  + DIGITAL ternary  │
 │ PINN + physics │          │ verified flash), SBOM,    │      │  ASIC: bit-exact,   │
 │ (FHN residual) │          │ 510(k) locked algorithm   │      │  sub-10 mW, <1 ms    │
 └────────────────┘          └──────────────────────────┘      └─────────────────────┘
   gradients live here          determinism enforced here        reproducibility here
```
Training (which *needs* exact derivatives — see the OPU study) stays in the cloud. The edge does only
frozen, bit-exact inference. This split is exactly what the OPU study's "values survive, derivatives die"
result dictates.

### What we reject, and why
- **Silicon photonics (MZI / microring):** 7.8 % irreducible static-defect floor; a 512×512 mesh needs ~262 W
  of thermo-optic tuning; conversion overhead negates the energy win below N≈4096. Wrong scale, wrong physics.
- **Analog charge-domain SRAM CIM:** the headline ~2941 TOPS/W is *analog* (charge + ADC) → **not bit-exact**
  → fails the same FDA reproducibility bar that kills optics. Only **digital** CIM qualifies.
- **ReRAM / memristor crossbar:** physically elegant for ternary (3 conductance levels, free sparsity) but
  3–5 years from production yield at 512×512. Revisit ~2028.
- **Analog wins only** in a *hypothetical* non-regulated, inference-only, **N≫4096** pivot with stochastic
  output tolerated — i.e. not this product.

### The deep insight
The "best computing system" is **not** the highest TOPS/W. For a regulated, edge, small-N medical workload,
the objective function is *(determinism × certifiability × $ × mW)*, and on that objective a **multiplier-free
digital ternary ASIC sits at the global optimum.** Tritone's ternary design — chosen originally for being
multiplier-free — turns out to be the right substrate for the regulatory reality too.

---

## Next steps (cheap → expensive)
1. **Hold at Phase 0.** Run the real `.keras` weights through the OPU sim's `--weights` hook to close the
   feasibility loop; keep the FPGA as the clinical instrument.
2. **Define the trigger metric** with the clinical team (expected unit volume, power envelope, submission date).
3. **When a trigger fires:** commission the Phase-1 SKY130 prototype purely to harden the datapath + build the
   golden-vector test rig; in parallel, scope the Phase-2 28 nm digital-ternary-CIM macro.
4. **Lock the weight-load chain** (SHA-256 OTP/verified-flash) as part of the 510(k) PCCP from day one.

---
*Inputs: `council/` (3 position papers + red-team gate). Knowledge graph: `../wiki/`. Prior study: `../opu_study/`.*
