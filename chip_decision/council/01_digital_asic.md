# Council 1 — Digital Ternary ASIC Architect

*Position paper. Verdict: tape out a digital ternary systolic array.*

## Should we tape out at all?
Yes, conditionally. The FPGA baseline (Tang Nano 9K, ~$20, 105 mW, 27 MHz) is fine for lab demo but a
ternary MAC = 2-bit mux + conditional add is among the most ASIC-friendly workloads possible. NRE is
amortized over every milliwatt saved per deployed device, not unit volume alone.

## Manufacturing path
| Path | NRE | Per-die | Area/slot | TAT | Verdict |
|---|---|---|---|---|---|
| **SKY130 MPW (Efabless/Google)** | ~$10–12k | ~$5–20 (samples) | ~10 mm² | 6–9 mo | **RECOMMENDED Phase 1** |
| TinyTapeout (SKY130) | ~$300/tile | ~$2–5 | ~0.016 mm²/tile | 4–6 mo | Too small for 64×64 |
| TSMC 28 nm MPW (EUROPRACTICE) | ~$70–130k | ~$3–8 @ volume | 4–5 mm² | 9–12 mo | Phase 2 if >10k units |

## Area / power / throughput (SKY130, ternary PE ≈ 20–30 cells ≈ ~50 µm²)
| Array | PEs | Array area | Est. die | Power | Throughput |
|---|---|---|---|---|---|
| 16×16 | 256 | ~0.013 mm² | ~1–2 mm² | ~5–15 mW | ~0.5 GOPS @ 200 MHz |
| **64×64** | 4,096 | ~0.21 mm² | **~3–5 mm²** | **~30–60 mW** | **~8 GOPS** |
| 128×128 | 16,384 | ~0.82 mm² | ~7–9 mm² | ~80–120 mW | ~32 GOPS |

Full GI-twin forward pass (~6.5M ternary MACs) completes in **<1 ms** at 8 GOPS.

## Advantage to protect
**Bit-exact determinism** — integer-only, reproducible bit-for-bit across every chip/temperature/run. No
analog accelerator can claim this; for a clinical digital twin it's an FDA/CE requirement, not a nicety.

## Risks
SKY130 is slow (~200 MHz realistic, not 500). Architecture changes need a respin (mitigate: weight-SRAM,
not hard-wired). Below ~500 units the FPGA is cheaper. TAT 6–9 months.

## Recommended chip & verdict
**SKY130, 64×64 ternary systolic array, ~5 mm², ~40 mW @ 200 MHz, ~8 GOPS, NRE $10–12k.**
**VERDICT:** tape out the 64×64 ternary array on SKY130 now — NRE is rounding error, power drops 3× vs FPGA,
and bit-exact determinism is structurally guaranteed.

*Sources:* SkyWater MPW programs; Cadence SKY130 MPW aggregation; EUROPRACTICE 2026 schedules; TSMC 28 nm MPW (VLSIShuttle); TinyTapeout FAQ.
