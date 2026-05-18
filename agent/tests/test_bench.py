from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bench import Benchmarker, _KPP_12_THRESHOLD, _KPP_13_THRESHOLD


def _make_benchmarker(cpu_pct: float = 10.0, rss_mb: float = 48.0) -> Benchmarker:
    """Return a Benchmarker with psutil mocked to fixed values."""
    mock_proc = MagicMock()
    mock_proc.cpu_percent.return_value = cpu_pct
    mock_proc.memory_info.return_value = MagicMock(rss=int(rss_mb * 1024 * 1024))

    with patch("bench.psutil.Process", return_value=mock_proc):
        b = Benchmarker()
    b._proc = mock_proc
    return b


class TestBenchmarkerSample:
    def test_returns_required_keys(self):
        b = _make_benchmarker()
        reading = b.sample()
        assert "kpp_12_cpu_core_pct" in reading
        assert "kpp_13_rss_mb" in reading

    def test_cpu_value_matches_mock(self):
        b = _make_benchmarker(cpu_pct=25.0)
        reading = b.sample()
        assert reading["kpp_12_cpu_core_pct"] == 25.0

    def test_rss_converted_to_mb(self):
        b = _make_benchmarker(rss_mb=64.0)
        reading = b.sample()
        assert reading["kpp_13_rss_mb"] == 64.0

    def test_sample_appended_to_history(self):
        b = _make_benchmarker()
        assert len(b._samples) == 0
        b.sample()
        assert len(b._samples) == 1
        b.sample()
        assert len(b._samples) == 2

    def test_cpu_freq_included_when_available(self):
        b = _make_benchmarker()
        with patch("bench._read_cpu_freq_mhz", return_value=1500.0):
            reading = b.sample()
        assert "cpu_freq_mhz" in reading
        assert reading["cpu_freq_mhz"] == 1500.0

    def test_cpu_freq_absent_when_unavailable(self):
        b = _make_benchmarker()
        with patch("bench._read_cpu_freq_mhz", return_value=None):
            reading = b.sample()
        assert "cpu_freq_mhz" not in reading

    def test_kpp12_threshold_warning_logged(self, caplog):
        import logging
        b = _make_benchmarker(cpu_pct=_KPP_12_THRESHOLD + 1)
        b.sample()  # warm-up
        with caplog.at_level(logging.WARNING, logger="bench"):
            b.sample()
        assert "KPP-12 EXCEEDED" in caplog.text

    def test_kpp13_threshold_warning_logged(self, caplog):
        import logging
        b = _make_benchmarker(rss_mb=_KPP_13_THRESHOLD + 1)
        b.sample()  # warm-up
        with caplog.at_level(logging.WARNING, logger="bench"):
            b.sample()
        assert "KPP-13 EXCEEDED" in caplog.text

    def test_no_warning_within_threshold(self, caplog):
        import logging
        b = _make_benchmarker(cpu_pct=50.0, rss_mb=64.0)
        b.sample()
        with caplog.at_level(logging.WARNING, logger="bench"):
            b.sample()
        assert "EXCEEDED" not in caplog.text


class TestBenchmarkerSummary:
    def test_empty_returns_empty_dict(self):
        b = _make_benchmarker()
        assert b.summary() == {}

    def test_summary_after_one_sample(self):
        b = _make_benchmarker(cpu_pct=30.0, rss_mb=50.0)
        b.sample()
        s = b.summary()
        assert "kpp_12_cpu_core_pct" in s
        assert "kpp_13_rss_mb" in s

    def test_summary_keys(self):
        b = _make_benchmarker()
        b.sample()
        s = b.summary()
        for kpp in ("kpp_12_cpu_core_pct", "kpp_13_rss_mb"):
            assert set(s[kpp].keys()) == {"min", "max", "mean", "threshold", "objective", "pass", "samples"}

    def test_pass_flag_true_within_threshold(self):
        b = _make_benchmarker(cpu_pct=50.0, rss_mb=64.0)
        b.sample()
        b.sample()
        s = b.summary()
        assert s["kpp_12_cpu_core_pct"]["pass"] is True
        assert s["kpp_13_rss_mb"]["pass"] is True

    def test_pass_flag_false_when_exceeded(self):
        b = _make_benchmarker(cpu_pct=_KPP_12_THRESHOLD + 5, rss_mb=64.0)
        b.sample()
        b.sample()
        s = b.summary()
        assert s["kpp_12_cpu_core_pct"]["pass"] is False

    def test_min_max_mean_computed(self):
        b = _make_benchmarker()
        # Three sample() calls → values 20.0, 40.0, 60.0.
        # summary() excludes samples[0] (warm-up), so stats cover [40.0, 60.0].
        b._proc.cpu_percent.side_effect = [20.0, 40.0, 60.0]
        b._proc.memory_info.return_value = MagicMock(rss=int(64 * 1024 * 1024))
        b.sample()
        b.sample()
        b.sample()
        s = b.summary()
        cpu = s["kpp_12_cpu_core_pct"]
        assert cpu["min"] == 40.0
        assert cpu["max"] == 60.0
        assert abs(cpu["mean"] - 50.0) < 0.01

    def test_kpp14_note_present(self):
        b = _make_benchmarker()
        b.sample()
        s = b.summary()
        assert "kpp_14_note" in s
        assert "external" in s["kpp_14_note"]

    def test_warmup_sample_excluded_from_stats(self):
        # First sample is psutil warm-up (returns 0.0); summary should use
        # samples[1:] so a single non-warmup value drives the stats.
        b = _make_benchmarker()
        b._proc.cpu_percent.side_effect = [0.0, 35.0]
        b._proc.memory_info.return_value = MagicMock(rss=int(50 * 1024 * 1024))
        b.sample()  # warm-up (0.0)
        b.sample()  # real measurement (35.0)
        s = b.summary()
        cpu = s["kpp_12_cpu_core_pct"]
        assert cpu["min"] == 35.0
        assert cpu["samples"] == 1


class TestReadCpuFreq:
    def test_returns_mhz_from_sysfs(self, tmp_path):
        from bench import _read_cpu_freq_mhz
        freq_file = tmp_path / "scaling_cur_freq"
        freq_file.write_text("1500000\n")
        with patch("bench._CPU_FREQ_PATH", freq_file):
            result = _read_cpu_freq_mhz()
        assert result == 1500.0

    def test_returns_none_when_file_missing(self, tmp_path):
        from bench import _read_cpu_freq_mhz
        with patch("bench._CPU_FREQ_PATH", tmp_path / "nonexistent"):
            result = _read_cpu_freq_mhz()
        assert result is None
