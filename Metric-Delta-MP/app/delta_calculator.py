"""Pure delta logic, independent of the SDK so it can be unit tested."""
import math
import time
from typing import Dict, List, Optional


def compute_delta(
    timestamps: List[int],
    values: List[float],
    max_sample_age_minutes: Optional[int] = None,
    now_ms: Optional[int] = None,
) -> Optional[float]:
    """Returns last - (last-1), or None when no valid delta exists.

    None (never 0) is returned when:
      * fewer than two samples are available
      * the samples are not numeric / NaN
      * the newest sample is older than max_sample_age_minutes
    """
    if not timestamps or not values or len(timestamps) != len(values):
        return None

    samples = []
    for ts, v in zip(timestamps, values):
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if math.isnan(fv) or math.isinf(fv):
            continue
        samples.append((int(ts), fv))

    # Deduplicate timestamps and sort ascending
    samples = sorted(dict(samples).items())
    if len(samples) < 2:
        return None

    (_, previous), (last_ts, last) = samples[-2], samples[-1]

    if max_sample_age_minutes is not None:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        if now_ms - last_ts > max_sample_age_minutes * 60_000:
            return None

    return last - previous


def parse_latest_stats_response(payload: dict) -> Dict[str, Dict[str, dict]]:
    """Converts /api/resources/stats/latest/query output to
    {resourceId: {statKey: {"timestamps": [...], "data": [...]}}}."""
    out: Dict[str, Dict[str, dict]] = {}
    for entry in payload.get("values", []):
        resource_id = entry.get("resourceId")
        stats = entry.get("stat-list", {}).get("stat", [])
        for stat in stats:
            key = stat.get("statKey", {}).get("key")
            if resource_id and key:
                out.setdefault(resource_id, {})[key] = {
                    "timestamps": stat.get("timestamps", []),
                    "data": stat.get("data", []),
                }
    return out
