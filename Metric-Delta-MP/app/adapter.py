import sys
from typing import Any, Dict, Iterator, List

import aria.ops.adapter_logging as logging
from aria.ops.adapter_instance import AdapterInstance
from aria.ops.definition.adapter_definition import AdapterDefinition
from aria.ops.object import Object
from aria.ops.result import CollectResult, EndpointResult, TestResult
from aria.ops.suite_api_client import key_to_object
from aria.ops.timer import Timer

import constants as c
from config_loader import ConfigError, MetricSet, load_config
from delta_calculator import compute_delta, parse_latest_stats_response

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Definition
# --------------------------------------------------------------------------- #
def get_adapter_definition() -> AdapterDefinition:
    with Timer(logger, "Get Adapter Definition"):
        definition = AdapterDefinition(c.ADAPTER_KIND, c.ADAPTER_NAME)

        definition.define_string_parameter(
            c.PARAM_CONFIG_FILE,
            label="Configuration File",
            description="Name of the JSON file in Configurations > Management Packs Configuration",
            default=c.DEFAULT_CONFIG_FILE,
        )
        definition.define_string_parameter(
            c.PARAM_METRIC_PREFIX,
            label="Metric Group",
            description="Metric group under which the delta metrics are stored",
            default=c.DEFAULT_METRIC_PREFIX,
            advanced=True,
        )
        # No object types of our own: deltas are attached to existing
        # objects of other adapters (see 'Extending an Existing Management Pack').
        return definition


# --------------------------------------------------------------------------- #
# Suite API helpers
# --------------------------------------------------------------------------- #
def get_suite_api_client(adapter_instance: AdapterInstance):
    """Returns the Suite API client of the local VCF Operations.

    The platform provides Suite API credentials ONLY during collection
    (not during Test Connection or Get Endpoints); mp-test behaves the same.
    """
    client = adapter_instance.suite_api_client
    if client is None:
        raise ConfigError(
            "Suite API connection to VCF Operations is not available "
            "(it is only provided during collection)."
        )
    return client

def _chunks(items: List[Any], size: int) -> Iterator[List[Any]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def get_resources(client, adapter_kind: str, resource_kind: str) -> Dict[str, Object]:
    """Returns {resourceId: Object} for all resources of a kind."""
    resources: Dict[str, Object] = {}
    page = 0
    while True:
        response = client.get(
            f"api/resources?adapterKind={adapter_kind}&resourceKind={resource_kind}"
            f"&page={page}&pageSize={c.RESOURCE_PAGE_SIZE}"
        )
        response.raise_for_status()
        body = response.json()
        for res in body.get("resourceList", []):
            # Rebuilds the key of the existing object so our metrics are
            # merged into it instead of creating a new object.
            resources[res["identifier"]] = key_to_object(res["resourceKey"])

        total = body.get("pageInfo", {}).get("totalCount", 0)
        page += 1
        if page * c.RESOURCE_PAGE_SIZE >= total:
            break
    return resources


def get_last_two_samples(client, resource_ids: List[str], stat_keys: List[str]) -> dict:
    merged: dict = {}
    for batch in _chunks(resource_ids, c.STATS_BATCH_SIZE):
        response = client.post(
            "api/resources/stats/latest/query",
            json={"resourceId": batch, "statKey": stat_keys, "maxSamples": 2},
        )
        response.raise_for_status()
        merged.update(parse_latest_stats_response(response.json()))
    return merged


# --------------------------------------------------------------------------- #
# Test connection
# --------------------------------------------------------------------------- #
def test(adapter_instance: AdapterInstance) -> TestResult:
    """Validates only the adapter instance parameters.

    The Suite API is not available during Test Connection, so the
    configuration file itself is read and validated on the first
    collection; errors are then shown on the adapter instance.
    """
    with Timer(logger, "Test"):
        result = TestResult()
        try:
            file_name = (
                adapter_instance.get_identifier_value(c.PARAM_CONFIG_FILE) or ""
            ).strip()
            prefix = (
                adapter_instance.get_identifier_value(
                    c.PARAM_METRIC_PREFIX, c.DEFAULT_METRIC_PREFIX
                )
                or ""
            ).strip("| ")

            if not file_name:
                result.with_error("'Configuration File' must not be empty.")
            elif "/" in file_name or "\\" in file_name:
                result.with_error(
                    "'Configuration File' must be a file name only (no path); "
                    "the file is read from the SolutionConfig folder."
                )
            elif not prefix:
                result.with_error("'Metric Group' must not be empty.")
            else:
                logger.info(
                    f"Parameters OK. Configuration file '{file_name}' will be "
                    f"read during collection."
                )
        except Exception as e:
            logger.error("Unexpected test connection error")
            logger.exception(e)
            result.with_error("Unexpected test connection error: " + repr(e))
        return result


# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #
def process_metric_set(client, ms: MetricSet, prefix: str, result: CollectResult) -> int:
    resources = get_resources(client, ms.adapter_kind, ms.resource_kind)
    if not resources:
        logger.info(f"No resources for {ms.adapter_kind}/{ms.resource_kind}")
        return 0

    stats = get_last_two_samples(client, list(resources.keys()), ms.metrics)
    emitted = 0
    for resource_id, obj in resources.items():
        resource_stats = stats.get(resource_id)
        if not resource_stats:
            continue  # metric not available -> store nothing
        has_value = False
        for stat_key in ms.metrics:
            s = resource_stats.get(stat_key)
            if not s:
                continue
            delta = compute_delta(s["timestamps"], s["data"], ms.max_sample_age_minutes)
            if delta is None:
                continue  # never write 0 for "no data"
            obj.with_metric(f"{prefix}|{stat_key}", delta)
            has_value = True
            emitted += 1
        if has_value:
            result.add_object(obj)
    return emitted


def collect(adapter_instance: AdapterInstance) -> CollectResult:
    with Timer(logger, "Collection"):
        result = CollectResult()
        try:
            file_name = adapter_instance.get_identifier_value(
                c.PARAM_CONFIG_FILE, c.DEFAULT_CONFIG_FILE
            )
            prefix = adapter_instance.get_identifier_value(
                c.PARAM_METRIC_PREFIX, c.DEFAULT_METRIC_PREFIX
            ).strip("|")

            with get_suite_api_client(adapter_instance) as client:
                config = load_config(client, file_name)
                for ms in config.metric_sets:
                    with Timer(logger, f"{ms.adapter_kind}/{ms.resource_kind}"):
                        try:
                            n = process_metric_set(client, ms, prefix, result)
                            logger.info(
                                f"{ms.adapter_kind}/{ms.resource_kind}: {n} delta value(s)"
                            )
                        except Exception as e:
                            # One broken set must not stop the others
                            logger.error(f"Metric set {ms.adapter_kind}/{ms.resource_kind} failed")
                            logger.exception(e)
        except ConfigError as e:
            logger.error(str(e))
            result.with_error(str(e))
        except Exception as e:
            logger.error("Unexpected collection error")
            logger.exception(e)
            result.with_error("Unexpected collection error: " + repr(e))
        return result


def get_endpoints(adapter_instance: AdapterInstance) -> EndpointResult:
    with Timer(logger, "Get Endpoints"):
        # Only the local Suite API is used; no external certificates needed.
        return EndpointResult()


# --------------------------------------------------------------------------- #
# Entry point (same contract as the mp-init template)
# --------------------------------------------------------------------------- #
def main(argv: List[str]) -> None:
    logging.setup_logging("adapter.log")
    logging.rotate()
    logger.info(f"Running adapter code with arguments: {argv}")
    if len(argv) != 3:
        logger.error("Arguments must be <method> <inputfile> <outputfile>")
        sys.exit(1)

    method = argv[0]
    try:
        if method == "test":
            test(AdapterInstance.from_input()).send_results()
        elif method == "endpoint_urls":
            get_endpoints(AdapterInstance.from_input()).send_results()
        elif method == "collect":
            collect(AdapterInstance.from_input()).send_results()
        elif method == "adapter_definition":
            get_adapter_definition().send_results()
        else:
            logger.error(f"Command {method} not found")
            sys.exit(1)
    finally:
        logger.info(Timer.graph())
        sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
