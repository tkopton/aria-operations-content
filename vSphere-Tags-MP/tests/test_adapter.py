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
    def __init__(self, resources, tags):
        self.resources = resources
        self.tags = tags

    def paged_post(self, url, key, **kwargs):
        return {"resourceList": self.resources}

    def post(self, url, **kwargs):
        ids = kwargs["json"]["resourceIds"]
        return FakeResponse(
            {
                "values": [
                    {
                        "resourceId": rid,
                        "property-contents": {
                            "property-content": [
                                {
                                    "statKey": "summary|tag",
                                    "timestamps": [1],
                                    "values": [self.tags[rid]],
                                }
                            ]
                        },
                    }
                    for rid in ids
                    if rid in self.tags
                ]
            }
        )


class FakeAdapterInstance:
    def __init__(self, settings=None):
        self.settings = settings or {}

    def get_identifier_value(self, key, default=None):
        return self.settings.get(key, default)


def properties(obj):
    return {p["key"]: p["stringValue"] for p in obj.get_json()["properties"]}


def run(tags, settings=None):
    resources = [resource(rid, f"vm{rid}") for rid in ["1", "2", "3"]]
    client = FakeClient(resources, tags)
    s = adapter.Settings(FakeAdapterInstance(settings))
    res = adapter.query_resources(client, s.source_adapter_kind, s.resource_kinds)
    raw = adapter.get_latest_property(client, list(res.keys()), "summary|tag")
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
