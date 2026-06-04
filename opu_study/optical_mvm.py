#!/usr/bin/env python3
"""Optical-MVM error model for the Tritone OPU feasibility study.

The hardware Tritone array computes an INTEGER ternary matrix-multiply
``psum = a @ W`` with ``W in {-1,0,+1}`` and INT8 activations ``a`` (see
``host/tpu_driver.py``). An Optical Processing Unit would do the same matmul in
the analog optical domain, which injects noise. This module provides:

  * ``mac_baseline``  -- the bit-exact integer reference (what the FPGA does).
  * ``OpticalMVM``    -- the same matmul corrupted by a physically-motivated,
                          term-by-term switchable optical error model.

Modeling distinction that matters (QA finding F1):
  STATIC errors  (weight/phase, extinction-ratio leakage) are device fabrication/
    calibration imperfections -- fixed once the chip exists. They are sampled
    ONCE per device and cached per layer, so a finite-difference Jacobian sees a
    consistent device on the +eps and -eps evaluations.
  DYNAMIC errors (readout shot/thermal/ADC noise) are per-measurement -- sampled
    fresh on every matmul call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np

_TERNARY = (-1, 0, 1)
_RMS_FLOOR = 1e-9  # F3: guard rms->0 on all-zero layers/samples


def _as2d(a: np.ndarray) -> Tuple[np.ndarray, bool]:
    """Return (a_2d, was_1d). Matmul helpers operate on (batch, in)."""
    a = np.asarray(a)
    if a.ndim == 1:
        return a[None, :], True
    return a, False


def mac_baseline(a: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Bit-exact integer ternary MAC: ``psum = a @ W`` in pure int64.

    This is the deterministic reference every optical run is compared against.
    ``a`` is INT8 activations (..., in); ``W`` is ternary (in, out).
    """
    W = np.asarray(W)
    if not np.isin(W, _TERNARY).all():
        raise ValueError("W must be ternary {-1,0,+1}")
    a2, was1d = _as2d(a)
    psum = a2.astype(np.int64) @ W.astype(np.int64)
    return psum[0] if was1d else psum


def _rms(x: np.ndarray, axis: int = -1, keepdims: bool = True) -> np.ndarray:
    return np.sqrt(np.mean(x.astype(np.float64) ** 2, axis=axis, keepdims=keepdims))


@dataclass
class OpticalParams:
    """Optical-MVM error knobs. Defaults = a moderately good photonic MVM."""
    snr_db: float = 25.0          # readout SNR referred to the output (primary swept axis)
    sigma_w: float = 0.0          # rel. std of static weight/phase error on +/-1 states
    er_db: float = np.inf         # extinction ratio of the "0" state (dB); inf = perfect off
    crosstalk: float = 0.0        # nearest-neighbour channel mixing coefficient
    noise_mode: str = "additive"  # "additive" (fixed-sigma) | "shot" (var ∝ |psum|)  (F2)
    # master switches so unit tests can isolate each effect
    enable_readout: bool = True
    enable_weight_err: bool = True
    enable_leak: bool = True


class OpticalMVM:
    """An analog optical matrix-vector multiplier with a fixed device identity.

    One instance == one fabricated device. Static imperfections are sampled once
    (lazily, per layer key) and reused; readout noise is fresh per call.
    """

    def __init__(self, params: OpticalParams, rng: np.random.Generator):
        self.p = params
        self.rng = rng
        self._W_eff: Dict[str, np.ndarray] = {}  # cached static device per layer

    # -- static device imperfections (sampled once per layer) ---------------
    def _effective_weights(self, W: np.ndarray, key: str) -> np.ndarray:
        cached = self._W_eff.get(key)
        if cached is not None:
            return cached
        W = np.asarray(W).astype(np.float64)
        nz = W != 0.0
        W_eff = W.copy()
        # (b) multiplicative weight/phase error on the +/-1 states
        if self.p.enable_weight_err and self.p.sigma_w > 0:
            mult = 1.0 + self.rng.normal(0.0, self.p.sigma_w, size=W.shape)
            W_eff = np.where(nz, W_eff * mult, W_eff)
        # (c) finite extinction ratio: the "0" (off) path leaks light
        if self.p.enable_leak and np.isfinite(self.p.er_db):
            leak_amp = 10.0 ** (-self.p.er_db / 20.0)
            leak = leak_amp * self.rng.normal(0.0, 1.0, size=W.shape)
            W_eff = np.where(nz, W_eff, leak)
        self._W_eff[key] = W_eff
        return W_eff

    # -- the optical matmul -------------------------------------------------
    def matmul(self, a: np.ndarray, W: np.ndarray, key: str) -> np.ndarray:
        """Analog ``a @ W`` with this device's static + dynamic optical errors."""
        a2, was1d = _as2d(a)
        W_eff = self._effective_weights(W, key)
        psum = a2.astype(np.float64) @ W_eff  # analog product (static errors baked in)

        # (d) optical crosstalk: neighbouring output channels mix before detection
        if self.p.crosstalk > 0 and psum.shape[-1] >= 3:
            c = self.p.crosstalk
            mixed = psum.copy()
            mixed[..., 1:] += c * psum[..., :-1]
            mixed[..., :-1] += c * psum[..., 1:]
            psum = mixed

        # (a) readout noise: shot + thermal + ADC, sampled fresh per measurement
        if self.p.enable_readout and np.isfinite(self.p.snr_db):
            rms = np.maximum(_rms(psum, axis=-1, keepdims=True), _RMS_FLOOR)
            if self.p.noise_mode == "shot":
                # signal-dependent: var ∝ |psum|, total power matched to additive @ same SNR
                tgt_power = (rms ** 2) * 10.0 ** (-self.p.snr_db / 10.0)
                absval = np.abs(psum)
                denom = np.maximum(np.mean(absval, axis=-1, keepdims=True), _RMS_FLOOR)
                var = tgt_power * absval / denom
                psum = psum + self.rng.normal(0.0, 1.0, size=psum.shape) * np.sqrt(var)
            else:  # "additive"
                sigma = rms * 10.0 ** (-self.p.snr_db / 20.0)
                psum = psum + self.rng.normal(0.0, 1.0, size=psum.shape) * sigma

        return psum[0] if was1d else psum
