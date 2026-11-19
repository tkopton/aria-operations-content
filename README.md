# Various VMware VCF Operations (formerly known as VMware Aria Operations and vRealize Operations) Content

Content mentioned in my blog posts, including:
* Dashboards
* Views
* Symptom and Alert Definitions
* Super Metrics
* etc.

---

## Super Metrics
*Not necessarily related to my blog posts and located in a separate folder*
*A README.md is (or will be soon) available in this folder describiung the Super Metrics*

---

## vSphere Tags Management Pack
*Located in [vSphere-Tags-MP](vSphere-Tags-MP)*

A management pack built with the VCF Operations Integration SDK. It splits the single-string `Summary | vSphere Tag` property (`[<Category-Tag>, ...]`) into one property per tag category, e.g. `summary|tag|Environment = Production`, so tags can be used in views, reports and custom groups.

---

## Metric Delta Management Pack
*Located in [Metric-Delta-MP](Metric-Delta-MP)*

A management pack built with the VCF Operations Integration SDK. For a configurable set of metrics it calculates the difference between the last and the previous value and stores it as `Custom Metrics|Delta|<stat key>` on the same object. Objects without two valid samples get no value, because `0` is a valid delta.
