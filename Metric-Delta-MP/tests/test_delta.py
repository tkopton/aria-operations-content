import sys, pathlib, types
import logging as _l

# Stub the SDK logging module so the modules import without the SDK installed
aria = types.ModuleType("aria"); ops = types.ModuleType("aria.ops")
log = types.ModuleType("aria.ops.adapter_logging"); log.getLogger = _l.getLogger
sys.modules.setdefault("aria", aria); sys.modules.setdefault("aria.ops", ops)
sys.modules.setdefault("aria.ops.adapter_logging", log)
sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "app"))

import pytest
from delta_calculator import compute_delta, parse_latest_stats_response
from config_loader import parse_config, ConfigError, config_file_path


def test_normal_delta():
    assert compute_delta([1000, 2000], [10.0, 13.5]) == 3.5

def test_unsorted_samples():
    assert compute_delta([2000, 1000], [13.5, 10.0]) == 3.5

def test_zero_is_valid():
    assert compute_delta([1000, 2000], [5, 5]) == 0.0

def test_single_sample_returns_none():
    assert compute_delta([1000], [5]) is None

def test_no_samples_returns_none():
    assert compute_delta([], []) is None

def test_nan_ignored():
    assert compute_delta([1000, 2000], [float("nan"), 3]) is None

def test_stale_sample():
    assert compute_delta([0, 60_000], [1, 2], max_sample_age_minutes=5, now_ms=600_000) is None
    assert compute_delta([0, 60_000], [1, 2], max_sample_age_minutes=5, now_ms=180_000) == 1

def test_parse_response():
    payload = {"values": [{"resourceId": "r1", "stat-list": {"stat": [
        {"statKey": {"key": "cpu|usage_average"}, "timestamps": [1, 2], "data": [1, 4]}]}}]}
    assert parse_latest_stats_response(payload)["r1"]["cpu|usage_average"]["data"] == [1, 4]

REFERENCE = pathlib.Path(__file__).parents[1] / "content/files/solutionconfig/metric_delta_config.json"

def test_reference_file_parses():
    cfg = parse_config(REFERENCE.read_text())
    assert len(cfg.metric_sets) == 1          # HostSystem set is disabled
    ms = cfg.metric_sets[0]
    assert (ms.adapter_kind, ms.resource_kind, ms.max_sample_age_minutes) == ("VMWARE", "VirtualMachine", 15)
    assert ms.metrics == ["disk|usage_average", "net|usage_average"]

def test_duplicates_and_blanks_removed():
    cfg = parse_config('{"metricSets":[{"adapterKind":"A","resourceKind":"B","metrics":["y"," y ",""]}]}')
    assert cfg.metric_sets[0].metrics == ["y"]

def test_config_invalid_missing_kind():
    with pytest.raises(ConfigError):
        parse_config('{"metricSets":[{"adapterKind":"A","metrics":["x"]}]}')

def test_config_invalid_max_age():
    with pytest.raises(ConfigError):
        parse_config('{"metricSets":[{"adapterKind":"A","resourceKind":"B","metrics":["x"],"maxSampleAgeMinutes":"15"}]}')

def test_config_not_json():
    with pytest.raises(ConfigError):
        parse_config('<xml/>')

def test_config_path():
    assert config_file_path("my_clone") == "SolutionConfig/my_clone.json"
    assert config_file_path("my_clone.json") == "SolutionConfig/my_clone.json"
