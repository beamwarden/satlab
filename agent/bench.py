from __future__ import annotations

import logging
import os
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)

# KPP thresholds from EXPAND.3.S26B §2.1
_KPP_12_THRESHOLD  = 80.0   # % of one core
_KPP_12_OBJECTIVE  = 60.0
_KPP_13_THRESHOLD  = 128.0  # MB RSS
_KPP_13_OBJECTIVE  = 64.0

# KPP-14 (power increment < 2.0 W / objective < 1.0 W) requires an external
# USB power meter between the wall supply and the RPi. CPU frequency is logged
# here as a thermal proxy only — it is not a substitute for measured draw.
_CPU_FREQ_PATH = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")


def _read_cpu_freq_mhz() -> float | None:
    try:
        return int(_CPU_FREQ_PATH.read_text().strip()) / 1000.0
    except (OSError, ValueError):
        return None


class Benchmarker:
    """
    Samples agent resource consumption for KPP-12 (CPU), KPP-13 (RAM), and
    KPP-14 proxy (CPU frequency) on each call to sample().

    cpu_percent() returns the fraction of one core consumed by this process,
    matching the KPP-12 definition ("< 80% core"). psutil's first call always
    returns 0.0 — the initial warm-up sample is recorded but excluded from
    threshold evaluation until at least two samples exist.
    """

    def __init__(self) -> None:
        self._proc = psutil.Process(os.getpid())
        self._proc.cpu_percent(interval=None)  # prime the counter
        self._samples: list[dict] = []

    def sample(self) -> dict:
        """Take one measurement snapshot and return it."""
        cpu_pct = self._proc.cpu_percent(interval=None)
        mem = self._proc.memory_info()
        rss_mb = mem.rss / (1024 * 1024)
        freq_mhz = _read_cpu_freq_mhz()

        reading: dict = {
            "kpp_12_cpu_core_pct": round(cpu_pct, 2),
            "kpp_13_rss_mb":       round(rss_mb, 2),
        }
        if freq_mhz is not None:
            reading["cpu_freq_mhz"] = round(freq_mhz, 1)

        self._samples.append(reading)

        exceeded = []
        if len(self._samples) > 1:
            if cpu_pct >= _KPP_12_THRESHOLD:
                exceeded.append(f"KPP-12 EXCEEDED cpu={cpu_pct:.1f}% (threshold={_KPP_12_THRESHOLD}%)")
            if rss_mb >= _KPP_13_THRESHOLD:
                exceeded.append(f"KPP-13 EXCEEDED rss={rss_mb:.1f}MB (threshold={_KPP_13_THRESHOLD}MB)")

        if exceeded:
            for msg in exceeded:
                logger.warning("BENCH %s", msg)
        else:
            logger.info(
                "BENCH kpp12=%.1f%% kpp13=%.1fMB%s",
                cpu_pct,
                rss_mb,
                f" freq={freq_mhz:.0f}MHz" if freq_mhz is not None else "",
            )

        return reading

    def summary(self) -> dict:
        """Return per-KPP statistics over all samples taken this session."""
        samples = self._samples[1:] if len(self._samples) > 1 else self._samples
        if not samples:
            return {}

        cpu_vals = [s["kpp_12_cpu_core_pct"] for s in samples]
        rss_vals = [s["kpp_13_rss_mb"] for s in samples]

        def _stats(vals: list[float], threshold: float, objective: float) -> dict:
            return {
                "min":       round(min(vals), 2),
                "max":       round(max(vals), 2),
                "mean":      round(sum(vals) / len(vals), 2),
                "threshold": threshold,
                "objective": objective,
                "pass":      max(vals) < threshold,
                "samples":   len(vals),
            }

        return {
            "kpp_12_cpu_core_pct": _stats(cpu_vals, _KPP_12_THRESHOLD, _KPP_12_OBJECTIVE),
            "kpp_13_rss_mb":       _stats(rss_vals, _KPP_13_THRESHOLD, _KPP_13_OBJECTIVE),
            "kpp_14_note":         "external USB power meter required for measured draw",
        }

    def log_summary(self) -> None:
        s = self.summary()
        if not s:
            return
        cpu = s["kpp_12_cpu_core_pct"]
        ram = s["kpp_13_rss_mb"]
        logger.info(
            "BENCH SESSION SUMMARY  samples=%d"
            "  KPP-12 cpu: min=%.1f max=%.1f mean=%.1f%% [%s threshold=%.0f%%]"
            "  KPP-13 rss: min=%.1f max=%.1f mean=%.1f MB [%s threshold=%.0f MB]",
            cpu["samples"],
            cpu["min"], cpu["max"], cpu["mean"],
            "PASS" if cpu["pass"] else "FAIL", cpu["threshold"],
            ram["min"], ram["max"], ram["mean"],
            "PASS" if ram["pass"] else "FAIL", ram["threshold"],
        )
