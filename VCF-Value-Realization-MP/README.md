# VCF Value Realization – Management Pack Builder Design

A Management Pack Builder (MPB) design for VCF Operations that collects **Security Posture Management (SPM) benchmark** data from VCF Operations itself and exposes each benchmark as an object with its compliance metrics.

* **Design file:** `VCF Value Realization.json` (MPB design export)
* **Built with:** VCF Operations 9.1.1 (`9.1.1.0100.25795063`)
* **Design version:** 1.0.0

## What it collects

**Source:** the VCF Operations Suite API (`/suite-api`) of the instance you point it at.

**Authentication:** a session token. The design calls `POST api/auth/token/acquire` with username, password and auth source. It passes the returned token as `Authorization: vRealizeOpsToken <token>` and releases it with `api/auth/token/release`.

**Request:** `GET /internal/security-posture-management/benchmarks`

**Object type:** `spmBenchmark`, one object per entry in `benchmarks[]`. Its identifier is key + name, and its name comes from the benchmark name.

| Label                         | Source field      | Type                |
|-------------------------------|-------------------|---------------------|
| `spmBenchmarkKey`             | `key`             | Property            |
| `spmBenchmarkName`            | `name`            | Property            |
| `spmBenchmarkStatus`          | `status`          | Property            |
| `spmBenchmarkComplianceScore` | `complianceScore` | Metric              |
| `spmBenchmarkRulesCount`      | `rulesCount`      | Metric              |

> **Note:** the benchmarks endpoint is an **internal, unsupported** API. It requires the `X-vRealizeOps-API-use-unsupported: true` header, which the design sets. It may change between VCF Operations releases without notice.

## How to use

1. In VCF Operations, open **Build > Developer Center > Management Pack Builder**.
2. Import `VCF Value Realization.json` as a design.
3. In **Source**, enter the hostname of your VCF Operations instance and test the connection with a user that can read SPM data.
4. Run the request and check the `spmBenchmark` objects, then **Build** and install the resulting `.pak`.
5. Create an adapter instance with the hostname, credentials and auth source (for example `local`).

## Compatibility

MPB designs are version-specific. Broadcom KB [454434](https://knowledge.broadcom.com/external/article/454434) states that management packs built with a pre-9.1.1 MPB stop collecting after an upgrade to 9.1.1 and must be rebuilt. This design was created on 9.1.1. Rebuild it after later upgrades if collection stops.
