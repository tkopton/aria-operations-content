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
