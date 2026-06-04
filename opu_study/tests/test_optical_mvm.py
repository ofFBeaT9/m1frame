#!/usr/bin/env python3
"""Correctness gate for the OPU study. Run: python -m pytest opu_study/tests -q

Each test pins one behaviour the QA gate (F1-F5) requires.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optical_mvm import OpticalMVM, OpticalParams, mac_baseline       # noqa: E402
from pinn_opu_sim import TernaryPINN, evaluate, jacobian               # noqa: E402


# -- baseline MAC is bit-exact (Story S1) -----------------------------------
def test_mac_baseline_matches_integer_reference():
    rng = np.random.default_rng(0)
    a = rng.integers(-128, 128, size=(4, 16))
    W = rng.integers(-1, 2, size=(16, 8))
    assert np.array_equal(mac_baseline(a, W), a.astype(np.int64) @ W.astype(np.int64))


def test_mac_baseline_rejects_non_ternary():
    with pytest.raises(ValueError):
        mac_baseline(np.ones((1, 4), int), np.array([[2, 0, 0, -1]]).T)


# -- optical limits (Story S2) ----------------------------------------------
def _device(rng=None, **kw):
    return OpticalMVM(OpticalParams(**kw), np.random.default_rng(rng or 1))


def test_high_snr_no_static_err_recovers_baseline():
    rng = np.random.default_rng(1)
    a = rng.integers(-100, 100, size=(8, 32)).astype(float)
    W = rng.integers(-1, 2, size=(32, 16))
    dev = _device(snr_db=np.inf, sigma_w=0.0, er_db=np.inf)
    assert np.allclose(dev.matmul(a, W, "L"), a @ W)


def test_lower_snr_gives_more_error():
    rng = np.random.default_rng(2)
    a = rng.integers(-100, 100, size=(64, 32)).astype(float)
    W = rng.integers(-1, 2, size=(32, 16))
    ref = a @ W
    err_hi = np.mean(np.abs(_device(snr_db=40, sigma_w=0, er_db=np.inf).matmul(a, W, "L") - ref))
    err_lo = np.mean(np.abs(_device(snr_db=10, sigma_w=0, er_db=np.inf).matmul(a, W, "L") - ref))
    assert err_lo > err_hi > 0


def test_extinction_ratio_makes_zeros_leak():
    a = np.ones((1, 8))
    W = np.zeros((8, 4), dtype=np.int8)  # all-zero weights
    clean = _device(snr_db=np.inf, sigma_w=0, er_db=np.inf).matmul(a, W, "L")
    leaky = _device(snr_db=np.inf, sigma_w=0, er_db=20).matmul(a, W, "L")
    assert np.allclose(clean, 0.0)
    assert np.any(np.abs(leaky) > 0)


def test_weight_error_perturbs_nonzeros_only():
    rng = np.random.default_rng(3)
    a = rng.integers(-50, 50, size=(1, 8)).astype(float)
    W = np.array([[1, 0, -1, 0]] * 8, dtype=np.int8)  # mixed zeros/nonzeros
    dev = _device(snr_db=np.inf, sigma_w=0.1, er_db=np.inf)
    W_eff = dev._effective_weights(W, "L")
    assert np.allclose(W_eff[W == 0], 0.0)          # zeros untouched (ER perfect)
    assert not np.allclose(W_eff[W != 0], W[W != 0])  # nonzeros perturbed


# -- F1: static device is consistent across calls (so Jacobian is valid) ----
def test_static_device_cached_per_layer():
    rng = np.random.default_rng(4)
    a = rng.integers(-50, 50, size=(1, 8)).astype(float)
    W = rng.integers(-1, 2, size=(8, 4))
    dev = _device(snr_db=np.inf, sigma_w=0.2, er_db=20)   # static errors only, no readout
    first = dev.matmul(a, W, "L")
    second = dev.matmul(a, W, "L")
    assert np.allclose(first, second)   # same device every call


def test_shot_mode_runs_and_is_noisy():
    rng = np.random.default_rng(5)
    a = rng.integers(-100, 100, size=(32, 16)).astype(float)
    W = rng.integers(-1, 2, size=(16, 8))
    out = _device(snr_db=15, sigma_w=0, er_db=np.inf, noise_mode="shot").matmul(a, W, "L")
    assert not np.allclose(out, a @ W)


# -- PINN forward + metrics (Stories S3/S4) ---------------------------------
def test_pinn_baseline_deterministic_and_shaped():
    net = TernaryPINN(seed=0)
    X = np.random.default_rng(0).standard_normal((5, 110))
    net.calibrate(X)
    y1, y2 = net.forward(X, None), net.forward(X, None)
    assert y1.shape == (5, 5)
    assert np.array_equal(y1, y2)              # baseline path is deterministic
    assert np.all((y1 > 0) & (y1 < 1))         # valid sigmoid outputs
    assert 0.2 < net.sparsity < 0.95           # ternary network is meaningfully sparse


def test_clean_optical_matches_baseline_value_and_jacobian():
    net = TernaryPINN(seed=1)
    X = np.random.default_rng(1).standard_normal((6, 110))
    net.calibrate(X)
    eps = 0.05 * float(np.std(X))
    Y_base = net.forward(X, None)
    J_base = jacobian(net, X, None, eps)
    dev = _device(snr_db=np.inf, sigma_w=0.0, er_db=np.inf)  # perfect optics
    res = evaluate(net, X, Y_base, J_base, dev, eps)
    assert res.value_rel_mae < 1e-9            # perfect optics == baseline (values)
    assert res.jac_rel_mae < 1e-6              # ... and derivatives (common-mode quant cancels)


def test_noisy_optics_degrades_and_amplifies():
    net = TernaryPINN(seed=2)
    X = np.random.default_rng(2).standard_normal((8, 110))
    net.calibrate(X)
    eps = 0.05 * float(np.std(X))
    Y_base = net.forward(X, None)
    J_base = jacobian(net, X, None, eps)
    dev = _device(snr_db=15, sigma_w=0.02, er_db=25)
    res = evaluate(net, X, Y_base, J_base, dev, eps)
    assert res.value_rel_mae > 0
    assert res.jac_rel_mae > res.value_rel_mae   # the core hypothesis: derivatives worse
