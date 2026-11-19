# Metric Delta Management Pack for VCF Operations

VCF Operations stores most counters as the value at a point in time. Many questions are
about the **change** between two collections instead: how much did this counter move since
the last cycle?

This management pack calculates, for a configurable set of metrics, the difference between
the **last** and the **last minus one** value, and stores it as a new metric on the same
object:

| Source metric | New metric |
|---|---|
| `disk\|usage_average` | `Custom Metrics\|Delta\|disk\|usage_average` |
| `net\|usage_average` | `Custom Metrics\|Delta\|net\|usage_average` |

The objects are the existing ones, for example the VMs and hosts of the vCenter adapter.
No new objects are created.

**If a metric has no delta, nothing is written.** `0` is a valid delta (the value did not
change), so writing `0` for "no data" would be wrong. A metric is skipped when the object
has fewer than two valid samples, or when the newest sample is older than the optional
`maxSampleAgeMinutes`.

Built with the [VCF Operations Integration SDK](https://github.com/vmware/vmware-vcf-operations-integration-sdk).

## Quick install (ready-made .pak)

No build needed: download [`pak/MetricDeltaAdapter_1.0.0.pak`](pak/MetricDeltaAdapter_1.0.0.pak)
and install it.

1. In VCF Operations, go to **Data Sources > Integrations > Repository > Add** and upload the .pak.
2. Create the configuration file (see below) under
   **Configurations > Management Packs Configuration**.
3. Under **Accounts > Add Account**, choose **Metric Delta**, give it a name, enter the
   configuration file name, pick the cloud proxy and save. One account per VCF Operations
   instance is enough.
4. After two collection cycles, open one of the configured objects and look under
   **Custom Metrics | Delta**.

The .pak contains no adapter code itself. It points to the container image
`docker.io/tkopton/metricdeltaadapter@sha256:a384b4f5fbe4560861c88d23fe678154a7508d6ab9793d67a54b243ae0036849`,
which the cloud proxy pulls from Docker Hub when the account starts. The cloud proxy
therefore needs access to Docker Hub. For air-gapped environments, build your own .pak and
image (see Development) and push it to a registry your cloud proxy can reach.

## How it works

* The adapter does **not** connect to vCenter or any other endpoint. It only uses the
  VCF Operations Suite API, which the collector gives to every SDK adapter automatically.
* Each collection cycle it:
  1. reads the configuration file with
     `GET api/configurations/files?path=SolutionConfig/<file>`,
  2. queries all objects of the configured `adapterKind`/`resourceKind` from
     `GET api/resources`,
  3. asks for the last two samples of the configured stat keys with
     `POST api/resources/stats/latest/query` and `maxSamples: 2`, in batches of 200
     object IDs,
  4. returns `last - previous` as a metric on the existing objects (the SDK's
     "extending an existing management pack" pattern; object keys are rebuilt with
     `key_to_object()`).
* A failing metric set is logged and skipped. The other sets of the same cycle still run.

## Configuration file

The management pack ships a **reference** file `metric_delta_config.json`. Do not edit it,
because an upgrade of the management pack overwrites it. Clone it instead under
**Configurations > Management Packs Configuration**, and enter the name of the clone in the
adapter instance.

```json
{
  "metricSets": [
    {
      "adapterKind": "VMWARE",
      "resourceKind": "VirtualMachine",
      "maxSampleAgeMinutes": 15,
      "metrics": ["disk|usage_average", "net|usage_average"]
    },
    {
      "adapterKind": "VMWARE",
      "resourceKind": "HostSystem",
      "enabled": false,
      "metrics": ["cpu|usage_average", "mem|usage_average"]
    }
  ]
}
```

| Key | Required | Description |
|---|---|---|
| `adapterKind` | yes | Adapter kind owning the objects, e.g. `VMWARE`. |
| `resourceKind` | yes | Object type, e.g. `VirtualMachine`, `HostSystem`. |
| `metrics` | yes | Stat keys, **case-sensitive**, exactly as the source adapter publishes them. |
| `maxSampleAgeMinutes` | no | Freshness check on the newest sample, see below. Without it, a metric that stopped updating keeps publishing the same delta every cycle. |
| `enabled` | no | `false` skips the whole set. Default `true`. The shipped reference file has the `HostSystem` set disabled as an example. |

JSON has no comments, so the reference file carries its notes in a `_comment` key, which
the adapter ignores. Changes apply on the next collection cycle, no restart needed.

### What `maxSampleAgeMinutes` does

It is a freshness check on the **newest of the two samples**, nothing else. At collection
time the adapter compares the timestamp of the newest sample with the current time:

```
now - timestamp(newest sample) > maxSampleAgeMinutes  ->  no value is written
```

Without the setting there is no such check: a delta is calculated whenever two samples
exist, however old they are.

Why it matters: when a metric stops being collected, because the VM is powered off, the
source adapter stopped or the metric was removed from a policy, its last two samples stay
in the database. The delta is then still calculable, and every cycle would write the same
number again with a current timestamp. The delta metric would look alive while its source
is dead. With the setting, the delta simply stops, which is the honest answer.

A sensible value is a little more than the collection interval of the source metric, for
example 15 minutes for a metric collected every 5 minutes, so one missed cycle does not
blank the delta.

One thing it does **not** do: it does not limit the gap *between* the two samples. If an
object was not collected for a day and comes back, the two newest samples can be a day
apart, and the delta covers that whole gap. The newest sample is fresh, so the check
passes.

## Adapter instance settings

| Setting | Default | Description |
|---|---|---|
| Configuration File | `metric_delta_config.json` | File name in **Management Packs Configuration**. `.json` is added when no extension is given. |
| Metric Group *(advanced)* | `Custom Metrics\|Delta` | Parent key of the generated metrics. |

**Test Connection** validates these two fields only. VCF Operations passes Suite API
credentials to an adapter during collection, not during test connection, so the
configuration file itself is read and validated at the start of **each collection**. A
missing file or invalid JSON shows up as a collection error on the adapter instance and in
the adapter log.

## Known limitations

* Metrics added to another adapter's objects cannot carry metadata (units, labels), so the
  delta appears with the raw stat key of the source metric.
* The delta is one collection cycle behind the source metric.
* A delta is a difference per collection interval, not a rate. If the source metric's
  collection interval changes, deltas before and after are not comparable.

## Development

Requires Python 3.11 or 3.12, Docker, and the SDK tools:

```bash
pip install vmware-aria-operations-integration-sdk
cd vcf-operations-content/Metric-Delta-MP
python3 -m venv "venv-Metric Delta Adapter"
. "venv-Metric Delta Adapter/bin/activate"
pip install -r adapter_requirements.txt pytest

# unit tests for the delta logic (no VCF Operations needed)
python -m pytest -q tests

# run test connection / collection against a live VCF Operations instance
mp-test connect
mp-test collect

# build the .pak file
mp-build
```

`mp-test collect` asks for Suite API connection details (VCF Operations FQDN, user,
password). Answer **Yes** to "Set connection information for SuiteAPI calls?", otherwise
the collection has no Suite API client.

## License

Apache-2.0
