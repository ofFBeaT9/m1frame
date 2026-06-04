---
title: ENS-GI Digital Twin
tags: [workload, clinical, pinn, physics, ens]
related: ["[[Tritone]]", "[[FDA SaMD Determinism]]", "[[Bit-Exact Determinism]]"]
created: 2026-06-02
sources: ["chip-architecture-council"]
page_type: entity
confidence: high
---

# ENS-GI Digital Twin

The workload [[Tritone]] serves: a multiscale physics-based model of the **Enteric Nervous System** and GI
motility. The PINN is an **inverse model** — 110 features → 5 ion-channel conductances (g_Na, g_K, g_Ca,
omega, coupling) of a FitzHugh-Nagumo / Hodgkin-Huxley tissue model (`dv/dt = v − v³/3 − w`).

## Why it shapes the chip decision
- **Tiny compute** (~500k MACs/inference) and **intermittent** inference rate → the value of custom silicon is
  power/cost/integration, not throughput.
- **Clinical applications** (IBS diagnosis, virtual drug trials, patient-specific prediction) → an **edge**,
  low-power, and crucially **certifiable** deployment, invoking [[FDA SaMD Determinism]].
- Training needs exact gradients (the physics residual) → kept in the cloud; only frozen inference ships,
  reinforcing [[Bit-Exact Determinism]] on the edge device.
