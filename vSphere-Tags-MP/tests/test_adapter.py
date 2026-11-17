"""Tests for the collect logic using a fake Suite API client.

Requires the SDK library (vmware-aria-operations-integration-sdk-lib), which is
installed in the project's virtual environment.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
# aria.ops.adapter_instance reads sys.argv[-2] at import time
sys.argv = sys.argv + ["in", "out"] if len(sys.argv) < 2 else sys.argv

pytest.importorskip("aria.ops")

import adapter  # noqa: E402


def resource(resource_id, name, kind="VirtualMachine"):
    return {
        "identifier": resource_id,
        "resourceKey": {
            "name": name,
            "adapterKindKey": "VMWARE",
            "resourceKindKey": kind,
            "resourceIdentifiers": [
                {
                    "identifierType": {"name": "VMEntityObjectID", "isPartOfUniqueness": True},
                    "value": f"vm-{resource_id}",
                }
            ],
        },
    }


class FakeResponse:
    def __init__(self, body, status=200):
        self.text = json.dumps(body)
        self.status_code = status
        self.ok = status < 300

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeClient:
    """Mimics the Suite API. ``bulk_ok=False`` makes the bulk endpoint fail."""

    def __init__(self, resources, tags, bulk_ok=True):
        self.resources = resources
        self.tags = tags
        self.bulk_ok = bulk_ok
        self.calls = []

    def paged_post(self, url, key, **kwargs):
        return {"resourceList": self.resources}

    def _props(self, rid):
        props = [{"name": "summary|runtime|powerState", "value": "Powered On"}]
        if rid in self.tags:
            props.append({"name": "summary|tag", "value": self.tags[rid]})
        return {"resourceId": rid, "property": props}

    def get(self, url, **kwargs):
        self.calls.append(url)
        if url == "/api/resources/properties":
            if not self.bulk_ok:
                return FakeResponse({}, status=404)
            ids = kwargs["params"]["resourceId"]
            return FakeResponse(
                {"resourcePropertiesList": [self._props(rid) for rid in ids]}
            )
        rid = url.split("/")[3]
        return FakeResponse(self._props(rid))


class FakeAdapterInstance:
    def __init__(self, settings=None):
        self.settings = settings or {}

    def get_identifier_value(self, key, default=None):
        return self.settings.get(key, default)


def properties(obj):
    return {p["key"]: p["stringValue"] for p in obj.get_json()["properties"]}


def run(tags, settings=None, bulk_ok=True):
    resources = [resource(rid, f"vm{rid}") for rid in ["1", "2", "3"]]
    client = FakeClient(resources, tags, bulk_ok)
    s = adapter.Settings(FakeAdapterInstance(settings))
    res = adapter.query_resources(client, s.source_adapter_kind, s.resource_kinds)
    raw = adapter.get_property_values(client, list(res.keys()), "summary|tag")
    return {o.get_key().name: properties(o) for o in adapter.build_objects(res, raw, s)}


def test_collect_splits_tags_and_fills_unset():
    out = run(
        {
            "1": "[<Environment-Production>, <Backup-Gold>, <App-Web>, <App-DB>]",
            "2": "[<Environment-Test>]",
        }
    )
    assert out["vm1"] == {
        "summary|tag|App": "DB, Web",
        "summary|tag|Backup": "Gold",
        "summary|tag|Environment": "Production",
    }
    assert out["vm2"] == {
        "summary|tag|App": "none",
        "summary|tag|Backup": "none",
        "summary|tag|Environment": "Test",
    }
    assert out["vm3"]["summary|tag|Environment"] == "none"


def test_empty_unset_value_writes_only_real_tags():
    out = run(
        {"1": "[<Environment-Production>]", "2": "[]"},
        {"unset_value": "", "property_prefix": "summary|vSphere Tags|"},
    )
    assert out == {"vm1": {"summary|vSphere Tags|Environment": "Production"}}


def test_known_categories():
    out = run(
        {"1": "[<Backup-Policy-Gold>]"},
        {"known_categories": "Backup-Policy, Owner", "unset_value": "n/a"},
    )
    assert out["vm1"] == {
        "summary|tag|Backup-Policy": "Gold",
        "summary|tag|Owner": "n/a",
    }
    assert out["vm2"] == {
        "summary|tag|Backup-Policy": "n/a",
        "summary|tag|Owner": "n/a",
    }


def test_test_passes_without_suite_api_client():
    instance = FakeAdapterInstance()
    instance.suite_api_client = None
    assert adapter.test(instance).get_json() == {}


def test_collect_errors_without_suite_api_client():
    instance = FakeAdapterInstance()
    instance.suite_api_client = None
    assert "Suite API" in adapter.collect(instance).get_json()["errorMessage"]


def test_fallback_to_per_object_requests_and_html_escaped_values():
    out = run(
        {"1": "[&lt;owner-cferber&gt;, &lt;supporttier-gold&gt;]"},
        {"unset_value": ""},
        bulk_ok=False,
    )
    assert out == {
        "vm1": {"summary|tag|owner": "cferber", "summary|tag|supporttier": "gold"}
    }


def test_stripped_values_are_skipped():
    out = run({"1": "[, ]", "2": "[<owner-cferber>]"})
    assert "vm1" not in out
    assert out["vm2"] == {"summary|tag|owner": "cferber"}
