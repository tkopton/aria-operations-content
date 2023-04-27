# VMware Aria Operations Custom Sustainability Dashboard
This content is related to: https://thomas-kopton.de/vblog/?p=1399

## Prerequisites
There are few prerequisites to get the workflows and dashboards up and running after importing all components into VMware Aria Automation Orchestrator and Aria Operations.

### VMware Aria Automation Orchestrator
The login procedure the Aria Orchestrator workflows are using to communicate with Aria Operations will be improved in an upcoming version and requires a Configuration element in Orchestrator.
In my workflow I am using the following structure:

```
tk-ops-framework
|__accessTokenTTL
|__accessToken
```

All workflows and actions are using transient REST host and operations, no Inventory configuration required.

### VMware Aria Operations
In VMware Aria Operations following objects need to be created manually:
- Custom Groups to add Energy Rate custom property
![Custom Group configuration](https://github.com/tkopton/aria-operations-content/blob/main/Sustainability-01/custom-group-settings.png)
## Installation
The overall order is:
1. Create your Custom Groups and add the right custom properties
2. Import the Aria Automation Orchestrator package and configure the attributes to reflect your Aria Operations FQDN
   * tk-ariaOps-getResourcesBySpecs-agnostic
   * Look for baseUrl attribute - one of my to do is to make it a variable
3. Import the Super Metrics and make sure that they are enabled in your policies, make also sure that the Super Metric formula reflects your custom attributes
4. Import Views and Dashboards
