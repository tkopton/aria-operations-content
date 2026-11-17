#  Copyright 2026 Thomas Kopton
#  SPDX-License-Identifier: Apache-2.0
"""vSphere Tags Management Pack.

Reads the single-string ``summary|tag`` property ("Summary | vSphere Tag") that the
VCF Operations vCenter adapter collects, splits it into ``Category -> Tag`` pairs and
writes one property per tag category back onto the same vCenter objects, e.g.::

    summary|tag            = [<Environment-Production>, <Backup-Gold>, <Owner-Ops>]
    summary|tag|Environment = Production
    summary|tag|Backup      = Gold
    summary|tag|Owner       = Ops

The adapter does not talk to vCenter at all. Everything goes through the VCF
Operations Suite API, which the collector provides to the adapter automatically.
"""
import html
import json
import sys
from xml.etree import ElementTree
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

import aria.ops.adapter_logging as logging
import constants
from aria.ops.adapter_instance import AdapterInstance
from aria.ops.definition.adapter_definition import AdapterDefinition
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.result import EndpointResult
from aria.ops.result import TestResult
from aria.ops.suite_api_client import key_to_object
from aria.ops.suite_api_client import SuiteApiClient
from aria.ops.timer import Timer
from constants import ADAPTER_KIND
from constants import ADAPTER_NAME
from tag_parser import is_unparseable
from tag_parser import parse_list_parameter
from tag_parser import parse_tags
from tag_parser import sanitize_key_segment
from tag_parser import SPLIT_FIRST
from tag_parser import SPLIT_LAST

logger = logging.getLogger(__name__)


def get_adapter_definition() -> AdapterDefinition:
    with Timer(logger, "Get Adapter Definition"):
        definition = AdapterDefinition(ADAPTER_KIND, ADAPTER_NAME)

        definition.define_string_parameter(
            constants.CFG_RESOURCE_KINDS,
            label="Object Types",
            description="Comma-separated list of vCenter adapter object types "
            "(resource kind keys) whose vSphere tags are split, e.g. "
            "VirtualMachine,HostSystem,ClusterComputeResource,Datastore.",
            default=constants.DEFAULT_RESOURCE_KINDS,
            max_length=1024,
        )
        definition.define_string_parameter(
            constants.CFG_PROPERTY_PREFIX,
            label="Property Prefix",
            description="Property key under which one property per tag category is "
            "created. 'summary|tag' places them in the Summary | vSphere Tag group.",
            default=constants.DEFAULT_PROPERTY_PREFIX,
            advanced=True,
        )
        definition.define_enum_parameter(
            constants.CFG_SPLIT_MODE,
            values=[SPLIT_FIRST, SPLIT_LAST],
            label="Split Category and Tag At",
            description="The tag string uses '-' between category and tag. If names "
            "contain '-', choose whether to split at the first or the last '-'. "
            "Categories listed in 'Known Categories' always take precedence.",
            default=constants.DEFAULT_SPLIT_MODE,
            advanced=True,
        )
        definition.define_string_parameter(
            constants.CFG_KNOWN_CATEGORIES,
            label="Known Categories",
            description="Optional comma-separated list of tag category names. Use it "
            "for categories that contain '-' so they are split correctly. Listed "
            "categories are also always written (with the 'Value for Unset "
            "Categories') on objects that have no tag in them.",
            required=False,
            max_length=2048,
        )
        definition.define_string_parameter(
            constants.CFG_MULTI_VALUE_SEPARATOR,
            label="Multi-Value Separator",
            description="Separator used when an object has several tags of the same "
            "category.",
            default=constants.DEFAULT_MULTI_VALUE_SEPARATOR,
            required=False,
            advanced=True,
        )
        definition.define_string_parameter(
            constants.CFG_UNSET_VALUE,
            label="Value for Unset Categories",
            description="Value written for a category an object has no tag in (for "
            "example after a tag was removed). Leave empty to write nothing.",
            default=constants.DEFAULT_UNSET_VALUE,
            required=False,
            advanced=True,
        )
        definition.define_string_parameter(
            constants.CFG_SOURCE_ADAPTER_KIND,
            label="Source Adapter Kind",
            description="Adapter kind key of the adapter that collects the vSphere "
            "tags. Normally 'VMWARE' (vCenter adapter).",
            default=constants.DEFAULT_SOURCE_ADAPTER_KIND,
            advanced=True,
        )

        # Special key read by the VCF Operations collector to size the container.
        definition.define_int_parameter(
            "container_memory_limit",
            label="Adapter Memory Limit (MB)",
            description="Sets the maximum amount of memory VCF Operations can "
            "allocate to the container running this adapter instance.",
            required=True,
            advanced=True,
            default=1024,
        )

        # No object types are defined: this adapter only adds properties to objects
        # owned by the vCenter adapter (adapter kind VMWARE).

        logger.debug(f"Returning adapter definition: {definition.to_json()}")
        return definition


class Settings:
    def __init__(self, adapter_instance: AdapterInstance) -> None:
        def value(key: str, default: str = "") -> str:
            v = adapter_instance.get_identifier_value(key, default)
            return default if v is None else str(v)

        self.resource_kinds = parse_list_parameter(
            value(constants.CFG_RESOURCE_KINDS, constants.DEFAULT_RESOURCE_KINDS)
        )
        self.prefix = value(
            constants.CFG_PROPERTY_PREFIX, constants.DEFAULT_PROPERTY_PREFIX
        ).strip().rstrip("|") or constants.DEFAULT_PROPERTY_PREFIX
        self.split_mode = value(constants.CFG_SPLIT_MODE, constants.DEFAULT_SPLIT_MODE)
        if self.split_mode not in (SPLIT_FIRST, SPLIT_LAST):
            self.split_mode = SPLIT_FIRST
        self.known_categories = parse_list_parameter(
            value(constants.CFG_KNOWN_CATEGORIES)
        )
        self.separator = value(
            constants.CFG_MULTI_VALUE_SEPARATOR,
            constants.DEFAULT_MULTI_VALUE_SEPARATOR,
        )
        self.unset_value = value(constants.CFG_UNSET_VALUE, constants.DEFAULT_UNSET_VALUE)
        self.source_adapter_kind = value(
            constants.CFG_SOURCE_ADAPTER_KIND, constants.DEFAULT_SOURCE_ADAPTER_KIND
        )

    def property_key(self, category: str) -> str:
        return f"{self.prefix}|{sanitize_key_segment(category)}"


def test(adapter_instance: AdapterInstance) -> TestResult:
    with Timer(logger, "Test"):
        result = TestResult()
        try:
            settings = Settings(adapter_instance)
            if not settings.resource_kinds:
                result.with_error("At least one object type must be configured.")
                return result
            if adapter_instance.suite_api_client is None:
                # VCF Operations does not pass Suite API credentials when testing an
                # account that has not been saved yet. The settings are valid, so
                # let the test pass; collect() reports any Suite API problem.
                logger.info(
                    "No Suite API connection available during test; skipping the "
                    "object query."
                )
                return result
            with adapter_instance.suite_api_client as client:
                resources = query_resources(
                    client, settings.source_adapter_kind, settings.resource_kinds
                )
                if not resources:
                    result.with_error(
                        f"No objects of type {', '.join(settings.resource_kinds)} found "
                        f"for adapter kind '{settings.source_adapter_kind}'. Check "
                        "that the vCenter adapter is configured and collecting."
                    )
                    return result
                sample = list(resources.keys())[:50]
                tags = get_property_values(client, sample, constants.SOURCE_TAG_PROPERTY)
                logger.info(
                    f"Found {len(resources)} objects; {len(tags)} of the first "
                    f"{len(sample)} have a '{constants.SOURCE_TAG_PROPERTY}' property."
                )
        except Exception as e:
            logger.error("Unexpected connection test error")
            logger.exception(e)
            result.with_error("Unexpected connection test error: " + repr(e))
        finally:
            logger.debug(f"Returning test result: {result.get_json()}")
            return result


def collect(adapter_instance: AdapterInstance) -> CollectResult:
    with Timer(logger, "Collection"):
        result = CollectResult()
        try:
            settings = Settings(adapter_instance)
            if adapter_instance.suite_api_client is None:
                result.with_error(
                    "No Suite API connection information was provided to the adapter."
                )
                return result
            with adapter_instance.suite_api_client as client:
                resources = query_resources(
                    client, settings.source_adapter_kind, settings.resource_kinds
                )
                logger.info(f"Found {len(resources)} objects in scope")
                raw_tags = get_property_values(
                    client, list(resources.keys()), constants.SOURCE_TAG_PROPERTY
                )
            for obj in build_objects(resources, raw_tags, settings):
                result.add_object(obj)
            logger.info(f"Returning tag properties for {len(result.objects)} objects")
        except Exception as e:
            logger.error("Unexpected collection error")
            logger.exception(e)
            result.with_error("Unexpected collection error: " + repr(e))
        finally:
            logger.debug(f"Returning collection result {result.get_json()}")
            return result


def build_objects(
    resources: Dict[str, Object],
    raw_tags: Dict[str, str],
    settings: Settings,
) -> List[Object]:
    """Create the result objects with one property per tag category.

    Every category seen on any object in this collection (plus the configured known
    categories) is written on every in-scope object, using the 'unset' value where
    the object has no tag in it. That way a removed tag is overwritten instead of
    keeping its last value forever.
    """
    unparseable = {rid for rid, raw in raw_tags.items() if is_unparseable(raw)}
    if unparseable:
        logger.warning(
            f"{len(unparseable)} objects have a tag value that cannot be parsed, e.g. "
            f"{raw_tags[next(iter(unparseable))]!r}. These objects are "
            "skipped."
        )
    parsed: Dict[str, Dict[str, List[str]]] = {
        resource_id: parse_tags(raw, settings.known_categories, settings.split_mode)
        for resource_id, raw in raw_tags.items()
    }
    all_categories: Set[str] = set(settings.known_categories)
    for categories in parsed.values():
        all_categories.update(categories.keys())

    objects: List[Object] = []
    for resource_id, obj in resources.items():
        if resource_id in unparseable:
            continue
        categories = parsed.get(resource_id, {})
        written = False
        for category in sorted(all_categories):
            tags = categories.get(category)
            if tags:
                obj.with_property(
                    settings.property_key(category), settings.separator.join(tags)
                )
                written = True
            elif settings.unset_value:
                obj.with_property(settings.property_key(category), settings.unset_value)
                written = True
        if written:
            objects.append(obj)
    return objects


def query_resources(
    client: SuiteApiClient, adapter_kind: str, resource_kinds: Iterable[str]
) -> Dict[str, Object]:
    """Return ``{resource_id: Object}`` for all objects of the given kinds."""
    response = client.paged_post(
        "/api/resources/query",
        "resourceList",
        json={"adapterKind": [adapter_kind], "resourceKind": list(resource_kinds)},
    )
    resources: Dict[str, Object] = {}
    for resource in response.get("resourceList", []):
        resource_id = resource.get("identifier")
        key = resource.get("resourceKey")
        if resource_id and key:
            resources[resource_id] = key_to_object(key)
    return resources


def get_property_values(
    client: SuiteApiClient, resource_ids: List[str], property_key: str
) -> Dict[str, str]:
    """Return ``{resource_id: current value}`` of one property for many resources.

    Uses ``GET /api/resources/properties?resourceId=..`` (all properties of several
    resources per call) and falls back to ``GET /api/resources/{id}/properties`` for
    resources missing from the bulk answer. The ``properties/latest/query`` endpoint is
    not used: it strips everything between ``<`` and ``>`` from values, which removes
    the tag names from ``summary|tag``.
    """
    values: Dict[str, str] = {}
    batch_size = constants.PROPERTY_QUERY_BATCH_SIZE
    for start in range(0, len(resource_ids), batch_size):
        batch = resource_ids[start : start + batch_size]
        with client.get(
            "/api/resources/properties", params={"resourceId": batch}
        ) as response:
            if response.ok:
                body = json.loads(response.text)
                for resource_id, name, value in iter_resource_properties(body):
                    if name == property_key and value is not None:
                        values[resource_id] = value
            else:
                logger.warning(
                    f"Bulk property request failed ({response.status_code}); "
                    "falling back to one request per object."
                )
        for resource_id in batch:
            if resource_id in values:
                continue
            with client.get(f"/api/resources/{resource_id}/properties") as response:
                if not response.ok:
                    logger.warning(
                        f"Property request for {resource_id} failed "
                        f"({response.status_code})"
                    )
                    continue
                body = json.loads(response.text)
            for _, name, value in iter_resource_properties(body, resource_id):
                if name == property_key and value is not None:
                    values[resource_id] = value
    values = {rid: html.unescape(v) for rid, v in values.items()}

    # The JSON output of the Suite API strips "<...>" from property values, which
    # leaves e.g. "[, ]" for summary|tag. The XML output keeps them (escaped), so
    # re-read stripped values as XML.
    stripped = [rid for rid, v in values.items() if is_unparseable(v)]
    for index, resource_id in enumerate(stripped):
        xml_value = get_property_value_xml(client, resource_id, property_key)
        if index == 0:
            logger.info(
                f"{resource_id}: JSON value {values[resource_id]!r}, "
                f"XML value {xml_value!r}"
            )
        if xml_value is not None and "<" in xml_value:
            values[resource_id] = xml_value
    return values


def get_property_value_xml(
    client: SuiteApiClient, resource_id: str, property_key: str
) -> Optional[str]:
    """Read one property of one resource from the XML output of the Suite API."""
    with client.get(
        f"/api/resources/{resource_id}/properties",
        headers={"Accept": "application/xml"},
    ) as response:
        if not response.ok:
            logger.warning(
                f"XML property request for {resource_id} failed ({response.status_code})"
            )
            return None
        text = response.text
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as e:
        logger.warning(f"Cannot parse XML properties of {resource_id}: {e}")
        return None
    for element in root.iter():
        if element.tag.endswith("property") and element.get("name") == property_key:
            return element.text or ""
    return None


def iter_resource_properties(
    body: Any, default_resource_id: Optional[str] = None
) -> Iterable[Tuple[str, str, Optional[str]]]:
    """Yield ``(resource_id, property_name, value)`` from a resource-properties answer.

    Handles a single ``{"resourceId": .., "property": [{"name": .., "value": ..}]}``
    object as well as any wrapper object holding a list of them.
    """
    if isinstance(body, dict):
        if isinstance(body.get("property"), list):
            resource_id = body.get("resourceId") or default_resource_id
            for prop in body["property"]:
                if isinstance(prop, dict):
                    yield resource_id, prop.get("name"), prop.get("value")
            return
        for value in body.values():
            if isinstance(value, (list, dict)):
                yield from iter_resource_properties(value, default_resource_id)
    elif isinstance(body, list):
        for item in body:
            yield from iter_resource_properties(item, default_resource_id)


def get_endpoints(adapter_instance: AdapterInstance) -> EndpointResult:
    with Timer(logger, "Get Endpoints"):
        # Only the local Suite API is used, so there are no endpoints to verify.
        result = EndpointResult()
        logger.debug(f"Returning endpoints: {result.get_json()}")
        return result


# Main entry point of the adapter. You should not need to modify anything below this line.
def main(argv: List[str]) -> None:
    logging.setup_logging("adapter.log")
    # Start a new log file by calling 'rotate'. By default, the last five calls will be
    # retained.
    logging.rotate()
    logger.info(f"Running adapter code with arguments: {argv}")
    if len(argv) != 3:
        # `inputfile` and `outputfile` are always automatically appended to the
        # argument list by the server
        logger.error("Arguments must be <method> <inputfile> <ouputfile>")
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
            result = get_adapter_definition()
            if type(result) is AdapterDefinition:
                result.send_results()
            else:
                logger.info(
                    "get_adapter_definition method did not return an AdapterDefinition"
                )
                sys.exit(1)
        else:
            logger.error(f"Command {method} not found")
            sys.exit(1)
    finally:
        logger.info(Timer.graph())
        sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
