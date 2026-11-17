# vSphere Tags Management Pack for VCF Operations

The VCF Operations vCenter adapter collects all vSphere tags of an object as **one string**
in the property `Summary | vSphere Tag` (`summary|tag`):

```
[<Environment-Production>, <Backup-Gold>, <Application-Web>, <Application-DB>]
```

That single string is hard to use in views, reports, custom groups or policies. This
management pack splits it into **one property per tag category** on the same object:

| Property key | Value |
|---|---|
| `summary\|tag\|Environment` | `Production` |
| `summary\|tag\|Backup` | `Gold` |
| `summary\|tag\|Application` | `DB, Web` |

You can then pick e.g. *Summary | vSphere Tag | Environment* as a column in a view, group
by it, or use it in a custom group membership rule.

Built with the [VCF Operations Integration SDK](https://github.com/vmware/vmware-vcf-operations-integration-sdk).

## How it works

* The adapter does **not** connect to vCenter. It only uses the VCF Operations Suite API,
  which the collector gives to every SDK adapter automatically.
* Each collection cycle it:
  1. queries all objects of the configured types from the vCenter adapter (`VMWARE`),
  2. reads the current `summary|tag` value of those objects in batches with
     `GET /api/resources/properties` (falling back to `GET /api/resources/{id}/properties`).
     `POST /api/resources/properties/latest/query` is not used because it strips the
     `<...>` parts from the value, which removes the tag names,
  3. parses the string and returns `<prefix>|<Category>` properties for the existing
     objects (it extends the vCenter adapter objects, it does not create new ones).
* Several tags from the same category (multi-cardinality categories) are joined, sorted,
  with `, `.
* Every category seen in the current collection (plus the *Known Categories*) is written to
  every in-scope object. Objects without a tag in that category get the *Value for Unset
  Categories* (default `none`). This also overwrites the value after a tag is removed.

## Configuration (adapter instance)

| Setting | Default | Description |
|---|---|---|
| Object Types | `VirtualMachine,HostSystem,ClusterComputeResource,Datastore,Datacenter` | vCenter adapter resource kinds to process. |
| Known Categories | *(empty)* | Comma-separated category names. Needed for categories containing `-` (see below). Listed categories are always written. |
| Property Prefix *(advanced)* | `summary\|tag` | Parent key of the generated properties. |
| Split Category and Tag At *(advanced)* | `first` | `first` or `last` `-` when the category is not a known one. |
| Multi-Value Separator *(advanced)* | `, ` | Separator for several tags of one category. |
| Value for Unset Categories *(advanced)* | `none` | Value for categories an object has no tag in. Empty = write nothing. |
| Source Adapter Kind *(advanced)* | `VMWARE` | Adapter kind that owns the tagged objects. |

### Categories or tags containing `-`

The vCenter adapter joins category and tag with `-`, so `<Backup-Policy-Gold>` is
ambiguous. Resolution order:

1. If the item starts with a *Known Category* followed by `-`, the longest such category
   wins (`Backup-Policy` → tag `Gold`).
2. Otherwise it is split at the first `-` (default) or last `-`, per *Split Category and
   Tag At*.

`|` and `:` in category names are replaced with `/` and `_` because they have special
meaning in VCF Operations stat keys.

## Known limitations

* Attributes added to another adapter's objects cannot carry metadata (labels, units),
  so the properties appear with their raw category names.
* If a category is removed from **every** object (and is not a *Known Category*), the
  stale value stays on objects that had it. Add the category to *Known Categories* once
  to clean it up.
* Tags reach this MP one collection cycle after the vCenter adapter collected them.

## Development

Requires Python 3.11 or 3.12, Docker, and the SDK tools:

```bash
pip install vmware-aria-operations-integration-sdk
cd aria-operations-content/vSphere-Tags-MP
python3 -m venv "venv-vSphere Tags"
. "venv-vSphere Tags/bin/activate"
pip install -r adapter_requirements.txt pytest

# unit tests (no VCF Operations needed)
python -m pytest -q tests

# run test connection / collection against a live VCF Operations instance
mp-test connect
mp-test collect

# build the .pak file
mp-build
```

`mp-test` asks for Suite API connection details (VCF Operations FQDN, user, password).
After installing the `.pak`, add an account of type *vSphere Tags* under
**Data Sources > Integrations**. One adapter instance per VCF Operations cluster is enough;
it covers all vCenter adapter instances.

## License

Apache-2.0
