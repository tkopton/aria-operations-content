# VCF Value Realization – Management Pack Builder Design

A Management Pack Builder (MPB) design for VCF Operations. It collects two kinds of data from VCF Operations itself and exposes them as objects with metrics:

* **Diagnostics findings**, one object per finding, with the number of affected objects
* **Security Posture Management (SPM) benchmarks**, with compliance score and rule count

Details:

* **Design file:** `VCF Value Realization.json` (MPB design export)
* **Built with:** VCF Operations 9.1.1 (`9.1.1.0100.25795063`)

## Source and authentication

**Source:** the VCF Operations Suite API (`/suite-api`) of the instance you point it at.

**Authentication:** a session token. The design calls `POST api/auth/token/acquire` with username, password and auth source, and releases the token with `api/auth/token/release`.

## Object types

### `vcfFinding` – Diagnostics findings

**Request:** `POST /api/diagnostics/findings/query?page=0&pageSize=1000` with body `{"filter": {}}`. This is the public Diagnostics API, called with header `Authorization: OpsToken <token>`.

**Object:** one per entry in `findings[]`. Its identifier is `ruleUuid`, and its name comes from `ruleName`.

| Label                         | Source field           | Type     |
|-------------------------------|------------------------|----------|
| `findingRuleUuid`             | `ruleUuid`             | Property |
| `findingRuleName`             | `ruleName`             | Property |
| `findingRuleDescription`      | `ruleDescription`      | Property |
| `findingCategory`             | `category`             | Property |
| `findingSeverity`             | `severity`             | Property |
| `findingType`                 | `findingType`          | Property |
| `findingRefreshMode`          | `refreshMode`          | Property |
| `findingAffectedObjectsCount` | `affectedObjectsCount` | Metric   |

To get the **number of findings per category**, group or filter the `vcfFinding` objects by the `findingCategory` property. You can do this in a view, a custom group or a super metric.

The collection user needs the `vcf_diagnostics.view` and `environment.vcfhealth.view` privileges. Each collection covers up to 1000 findings.

### `spmBenchmark` – Security Posture Management benchmarks

**Request:** `GET /internal/security-posture-management/benchmarks`, called with header `Authorization: vRealizeOpsToken <token>`.

**Object:** one per entry in `benchmarks[]`. Its identifier is key + name, and its name comes from the benchmark name.

| Label                         | Source field      | Type     |
|-------------------------------|-------------------|----------|
| `spmBenchmarkKey`             | `key`             | Property |
| `spmBenchmarkName`            | `name`            | Property |
| `spmBenchmarkStatus`          | `status`          | Property |
| `spmBenchmarkComplianceScore` | `complianceScore` | Metric   |
| `spmBenchmarkRulesCount`      | `rulesCount`      | Metric   |

> **Note:** the benchmarks endpoint is an **internal, unsupported** API. It requires the `X-vRealizeOps-API-use-unsupported: true` header, which the design sets. It may change between VCF Operations releases without notice.

## How to use

1. In VCF Operations, open **Build > Developer Center > Management Pack Builder**.
2. Import `VCF Value Realization.json` as a design.
3. In **Source**, enter the hostname of your VCF Operations instance and test the connection with a user that has the privileges listed above.
4. Run the requests and check the `vcfFinding` and `spmBenchmark` objects, then **Build** and install the resulting `.pak`.
5. Create an adapter instance with the hostname, credentials and auth source (for example `local`).

## Compatibility

MPB designs are version-specific. Broadcom KB [454434](https://knowledge.broadcom.com/external/article/454434) states that management packs built with a pre-9.1.1 MPB stop collecting after an upgrade to 9.1.1 and must be rebuilt. This design was created on 9.1.1. Rebuild it after later upgrades if collection stops.

## References

* [Diagnostics Public REST API – VCF 9.1 documentation](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/infrastructure-operations/using-vcf-operations-diagnostics/diagnostics-public-rest-api.html)
