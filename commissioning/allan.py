"""
Overlapping Allan deviation (OADEV) for rate time series.

The overlapping AVAR is computed from the phase sequence (integral of rate):

    AVAR(tau) = 1 / (2 * tau^2) * mean( (x[j+2m] - 2*x[j+m] + x[j])^2 )

where tau = m * tau0 and x is the cumulative sum of the rate samples.

For white noise with std sigma, ADEV(tau) = sigma * sqrt(tau0 / tau), which
has slope -1/2 on a log-log plot — the angle/velocity random walk region.

Tau points are spaced logarithmically (each step at least 20% larger than
the previous, minimum +1) to keep the number of points tractable.
"""
from __future__ import annotations

import numpy as np


def oadev(y: np.ndarray, tau0: float) -> tuple[np.ndarray, np.ndarray]:
    """
    Overlapping Allan deviation for a rate time series.

    y:    1-D array of rate measurements (gyro dps, accel g, etc.)
    tau0: mean sample interval in seconds (= 1 / ODR)

    Returns (taus, adev) with the same unit as y at each tau.
    Tau range: [tau0, ~N/3 * tau0].
    """
    N = len(y)
    x = np.zeros(N + 1, dtype=np.float64)
    x[1:] = np.cumsum(y) * tau0  # phase sequence

    taus: list[float] = []
    adevs: list[float] = []

    m = 1
    while 2 * m < N:
        tau  = m * tau0
        j    = np.arange(N - 2 * m)
        d    = x[j + 2*m] - 2.0*x[j + m] + x[j]
        avar = float(np.mean(d * d)) / (2.0 * tau * tau)
        taus.append(tau)
        adevs.append(float(np.sqrt(max(avar, 0.0))))
        m = max(m + 1, int(m * 1.2))

    return np.array(taus, dtype=np.float64), np.array(adevs, dtype=np.float64)


def eval_at(
    taus: np.ndarray,
    adev: np.ndarray,
    tau_targets: list[float],
) -> list[float]:
    """
    Log-linear interpolation of an ADEV curve at requested tau points.
    Clamps to the available range rather than extrapolating.
    """
    log_t = np.log(taus)
    log_a = np.log(np.where(adev > 0, adev, 1e-30))
    return [
        float(np.exp(np.interp(np.log(t), log_t, log_a)))
        for t in tau_targets
    ]
