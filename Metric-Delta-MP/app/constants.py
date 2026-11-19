# Adapter identity (must match manifest.txt "adapter_kinds")
ADAPTER_KIND = "MetricDeltaAdapter"
ADAPTER_NAME = "Metric Delta"

# Adapter instance parameter keys
PARAM_CONFIG_FILE = "config_file"
PARAM_METRIC_PREFIX = "metric_prefix"

# Defaults
DEFAULT_CONFIG_FILE = "metric_delta_config.json"  # users should point to a clone
DEFAULT_METRIC_PREFIX = "Custom Metrics|Delta"

# Folder under content/files/ that shows up in
# Configurations > Management Packs Configuration
SOLUTION_CONFIG_FOLDER = "SolutionConfig"

# Suite API tuning
RESOURCE_PAGE_SIZE = 1000
STATS_BATCH_SIZE = 200  # resource IDs per stats query
