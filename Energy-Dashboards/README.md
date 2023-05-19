# VMware Aria Operations Custom Energy Data Dashboards
This content is related to: https://thomas-kopton.de/vblog/?p=xxx

## Prerequisites
There are few prerequisites to get dashboards up and running after importing all content into VMware Aria Operations.

### VMware Aria Operations
In VMware Aria Operations following objects need to be created manually:
- Custom Groups to add Energy Rate and CO2 to kWh ratio custom properties
![Custom Group configuration](https://github.com/tkopton/aria-operations-content/blob/main/Sustainability-01/custom-group-settings.png)
## Installation
The overall order is:
1. Create your Custom Groups and add the right custom properties
2. Import the Aria Automation Orchestrator package and configure the attributes to reflect your Aria Operations FQDN
   * tk-ariaOps-getResourcesBySpecs-agnostic
   * Look for baseUrl attribute - one of my to do is to make it a variable
3. Import the Super Metrics and make sure that they are enabled in your policies, make also sure that the Super Metric formula reflects your custom attributes
4. Import Views and Dashboards
