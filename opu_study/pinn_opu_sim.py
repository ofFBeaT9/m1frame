#!/usr/bin/env python3
"""Faithful ternary PINN forward pass + optical-noise metrics.

Architecture mirrors the real Tritone PINN (project memory / paper):
    input_projection 110->512
    res_block_0: dense1 512->512, dense2 512->512, + residual skip
    res_block_2: dense1 512->128, dense2 128->128, projection 512->128 skip
    output 128->5 -> sigmoid           outputs: g_Na, g_K, g_Ca, omega, coupling

Weights are ternarized with the TWN scheme at tau=0.7 (matches the project).
Every Dense matmul is routed through either the bit-exact integer baseline or an
``OpticalMVM`` device. Activations are INT8-quantized per layer (per-sample max
scaling), mirroring the real per-layer INT8 activation scale.

Metrics per noise level:
  value error      -- how wrong the 5 outputs get  (the project's headline metric)
  derivative error -- how wrong d(outputs)/d(inputs) gets  (the PINN-critical metric)
The Jacobian uses central differences with the SAME step through the SAME INT8
path for baseline and optical, so the quantization staircase is common-mode and
cancels in the relative metric (QA finding F1).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from optical_mvm import OpticalMVM, mac_baseline

OUTPUT_NAMES = ["g_Na", "g_K", "g_Ca", "omega", "coupling"]
_EPS = 1e-3   # F3: relative-error denominator floor
_ACT_EPS = 1e-9


def _ternarize(W_real: np.ndarray, tau: float = 0.7) -> np.ndarray:
    """TWN ternarization: zero out |w| below tau * mean(|w|), else take the sign."""
    thresh = tau * np.mean(np.abs(W_real))
    W = np.zeros_like(W_real, dtype=np.int8)
    W[W_real > thresh] = 1
    W[W_real < -thresh] = -1
    return W


@dataclass
class _Layer:
    W: np.ndarray   # (in, out) ternary
    key: str


class TernaryPINN:
    """The fixed, 'trained' ternary network. Optical hardware varies; this does not."""

    def __init__(self, seed: int = 0, tau: float = 0.7):
        rng = np.random.default_rng(seed)
        dims = [
            (110, 512, "input_projection"),
            (512, 512, "res0_dense1"),
            (512, 512, "res0_dense2"),
            (512, 128, "res2_dense1"),
            (128, 128, "res2_dense2"),
            (512, 128, "res2_projection"),
            (128, 5,   "output"),
        ]
        self.layers: List[_Layer] = []
        for (din, dout, name) in dims:
            # Gaussian "trained" weights -> ternarized. Scale keeps thresholds sane.
            W_real = rng.standard_normal((din, dout)) / np.sqrt(din)
            self.layers.append(_Layer(W=_ternarize(W_real, tau), key=name))
        self.tau = tau
        # output-logit standardization (computed once, on the clean baseline) so all
        # 5 sigmoid outputs are active rather than saturated -- a fixed monotone map.
        self._logit_mean = np.zeros(5)
        self._logit_std = np.ones(5)

    @property
    def sparsity(self) -> float:
        z = sum(int((l.W == 0).sum()) for l in self.layers)
        n = sum(l.W.size for l in self.layers)
        return z / n

    # -- one Dense layer ----------------------------------------------------
    def _dense(self, a_float: np.ndarray, layer: _Layer,
               mvm: Optional[OpticalMVM], quantize: bool = True) -> np.ndarray:
        a2 = a_float if a_float.ndim == 2 else a_float[None, :]
        if quantize:
            # per-sample INT8 activation scaling (mirrors real per-layer INT8 scale)
            s = 127.0 / (np.max(np.abs(a2), axis=-1, keepdims=True) + _ACT_EPS)
            a_q = np.clip(np.round(a2 * s), -128, 127)
        else:
            # analog path: optics is continuous, no INT8 staircase (QA finding F1)
            s = np.ones((a2.shape[0], 1)); a_q = a2
        if mvm is None:
            if quantize:
                psum = mac_baseline(a_q.astype(np.int64), layer.W).astype(np.float64)
            else:
                psum = a_q @ layer.W.astype(np.float64)   # exact analog reference
        else:
            psum = mvm.matmul(a_q, layer.W, layer.key)
        out = psum / s   # dequantize back to the activation domain
        return out if a_float.ndim == 2 else out[0]

    # -- full forward -------------------------------------------------------
    def _forward_logits(self, x: np.ndarray, mvm: Optional[OpticalMVM],
                        quantize: bool = True) -> np.ndarray:
        relu = lambda z: np.maximum(z, 0.0)
        L = self.layers
        q = quantize
        h = relu(self._dense(x, L[0], mvm, q))         # 110->512
        # res_block_0
        r = relu(self._dense(h, L[1], mvm, q))         # 512->512
        r = self._dense(r, L[2], mvm, q)               # 512->512
        h = relu(h + r)                                # residual add
        # res_block_2
        r = relu(self._dense(h, L[3], mvm, q))         # 512->128
        r = self._dense(r, L[4], mvm, q)               # 128->128
        skip = self._dense(h, L[5], mvm, q)            # 512->128 projection
        h = relu(r + skip)
        logits = self._dense(h, L[6], mvm, q)          # 128->5
        return logits

    def forward(self, x: np.ndarray, mvm: Optional[OpticalMVM] = None,
                quantize: bool = True) -> np.ndarray:
        logits = self._forward_logits(x, mvm, quantize)
        logits = (logits - self._logit_mean) / self._logit_std
        return 1.0 / (1.0 + np.exp(-logits))           # sigmoid -> 5 outputs in (0,1)

    def calibrate(self, X: np.ndarray) -> None:
        """Set output-logit standardization from the clean baseline (run once)."""
        logits = self._forward_logits(X, None)
        self._logit_mean = logits.mean(axis=0)
        self._logit_std = logits.std(axis=0) + _ACT_EPS


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def jacobian(net: TernaryPINN, X: np.ndarray, mvm: Optional[OpticalMVM],
             eps: float, quantize: bool = True) -> np.ndarray:
    """Central-difference Jacobian d(outputs)/d(inputs), shape (M, 5, 110).

    All 2*D perturbed evaluations are run as ONE batch so a single optical device
    (static errors) is shared across them, while readout noise is fresh per row --
    physically: two separate measurements of neighbouring operating points.

    `quantize=False` runs the smooth analog path (no INT8 staircase), so the CLEAN
    baseline Jacobian is well-conditioned and optical degradation is cleanly
    attributable to the optics rather than to differencing a step function (F1).
    """
    M, D = X.shape
    # build the stacked perturbation batch: [x+eps e_k, x-eps e_k] for all k
    plus = np.repeat(X[:, None, :], D, axis=1)          # (M, D, D)
    minus = plus.copy()
    idx = np.arange(D)
    plus[:, idx, idx] += eps
    minus[:, idx, idx] -= eps
    big = np.concatenate([plus.reshape(M * D, D),
                          minus.reshape(M * D, D)], axis=0)   # (2*M*D, D)
    Y = net.forward(big, mvm, quantize=quantize)         # (2*M*D, 5)
    yp = Y[:M * D].reshape(M, D, 5)
    ym = Y[M * D:].reshape(M, D, 5)
    J = (yp - ym) / (2.0 * eps)                          # (M, D, 5)
    return np.transpose(J, (0, 2, 1))                    # (M, 5, D)


def _rel_l1(approx: np.ndarray, ref: np.ndarray) -> float:
    """Aggregate relative L1 error: robust to the many near-zero sparse entries."""
    return float(np.sum(np.abs(approx - ref)) / (np.sum(np.abs(ref)) + _EPS))


@dataclass
class TrialResult:
    value_rel_mae: float
    value_max_rel_err: float
    value_abs_mae: float
    jac_rel_mae: float
    amplification: float
    per_output_rel: np.ndarray   # (5,) added rel error per output


def evaluate(net: TernaryPINN, X: np.ndarray, Y_base: np.ndarray,
             J_base: np.ndarray, mvm: OpticalMVM, eps: float,
             jac_quantize: bool = True) -> TrialResult:
    Y = net.forward(X, mvm)                       # value error on hardware INT8 path
    J = jacobian(net, X, mvm, eps, quantize=jac_quantize)  # derivative on chosen path
    value_rel = _rel_l1(Y, Y_base)
    # per-element max relative error (F3-guarded denominator)
    max_rel = float(np.max(np.abs(Y - Y_base) / (np.abs(Y_base) + _EPS)))
    abs_mae = float(np.mean(np.abs(Y - Y_base)))
    jac_rel = _rel_l1(J, J_base)
    amp = jac_rel / max(value_rel, 1e-12)
    per_out = (np.sum(np.abs(Y - Y_base), axis=0)
               / (np.sum(np.abs(Y_base), axis=0) + _EPS))
    return TrialResult(value_rel, max_rel, abs_mae, jac_rel, amp, per_out)
