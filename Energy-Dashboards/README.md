# VMware Aria Operations Custom Energy Data Dashboards
This content is related to: [https://thomas-kopton.de/vblog/?p=1538](https://thomas-kopton.de/vblog/?p=1538)

## Prerequisites
There are few prerequisites to get dashboards up and running after importing all content into VMware Aria Operations.

### VMware Aria Operations
In VMware Aria Operations following objects need to be created manually:
- Custom Groups to add Energy Rate and CO2 to kWh ratio custom properties
![Custom Group configuration](https://github.com/tkopton/aria-operations-content/blob/main/Energy-Dashboards/custom_group_setup.png)
As described in the blog post: https://thomas-kopton.de/vblog/?p=1538
- Activate disabled metrics in the according policies
## Installation
The overall order is:
1. Create your Custom Groups and add the right custom properties
2. Import the Super Metrics and make sure that they are enabled in your policies, make also sure that the Super Metric formula reflects your custom attributes
3. Import Views and Dashboards
