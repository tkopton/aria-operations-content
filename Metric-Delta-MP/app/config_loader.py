"""Loads and validates the metric-set configuration.

The configuration is a JSON file managed in the VCF Operations UI under
Configurations > Management Packs Configuration (folder SolutionConfig).
A reference file is shipped in content/files/solutionconfig/.
"""
import json
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import quote

import aria.ops.adapter_logging as logging

from constants import SOLUTION_CONFIG_FOLDER

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    pass


@dataclass
class MetricSet:
    adapter_kind: str
    resource_kind: str
    metrics: List[str]
    max_sample_age_minutes: Optional[int] = None


@dataclass
class DeltaConfig:
    metric_sets: List[MetricSet] = field(default_factory=list)


def parse_config(raw: str) -> DeltaConfig:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Configuration file is not valid JSON: {e}")

    sets = data.get("metricSets") if isinstance(data, dict) else None
    if not isinstance(sets, list):
        raise ConfigError("'metricSets' must be a list")

    result = DeltaConfig()
    for i, entry in enumerate(sets, start=1):
        if not isinstance(entry, dict):
            raise ConfigError(f"metricSets #{i} must be an object")
        adapter_kind = str(entry.get("adapterKind", "")).strip()
        resource_kind = str(entry.get("resourceKind", "")).strip()
        if not adapter_kind or not resource_kind:
            raise ConfigError(f"metricSets #{i} needs 'adapterKind' and 'resourceKind'")
        if entry.get("enabled", True) is False:
            continue

        metrics = entry.get("metrics")
        if not isinstance(metrics, list) or not all(isinstance(m, str) for m in metrics):
            raise ConfigError(f"{adapter_kind}/{resource_kind}: 'metrics' must be a list of stat keys")
        metrics = sorted({m.strip() for m in metrics} - {""})
        if not metrics:
            raise ConfigError(f"{adapter_kind}/{resource_kind}: 'metrics' is empty")

        max_age = entry.get("maxSampleAgeMinutes")
        if max_age is not None and (isinstance(max_age, bool) or not isinstance(max_age, int) or max_age <= 0):
            raise ConfigError(f"{adapter_kind}/{resource_kind}: 'maxSampleAgeMinutes' must be a positive integer")

        result.metric_sets.append(MetricSet(adapter_kind, resource_kind, metrics, max_age))

    if not result.metric_sets:
        raise ConfigError("Configuration contains no enabled metric set")
    return result


def config_file_path(file_name: str) -> str:
    name = file_name.strip()
    if "." not in name:
        name += ".json"
    return f"{SOLUTION_CONFIG_FOLDER}/{name}"


def load_config(client, file_name: str) -> DeltaConfig:
    """Reads the JSON configuration file through the Suite API."""
    path = config_file_path(file_name)
    response = client.get(url=f"api/configurations/files?path={quote(path)}")
    if not response.ok:
        raise ConfigError(
            f"Could not read configuration file '{path}': HTTP {response.status_code}"
        )
    logger.debug(f"Loaded configuration file '{path}'")
    return parse_config(response.text)
