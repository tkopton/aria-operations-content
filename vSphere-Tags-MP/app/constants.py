ADAPTER_KIND = "vSphereTagsMP"
ADAPTER_NAME = "vSphere Tags"

# Adapter kind of the VCF Operations vCenter adapter whose objects we extend
DEFAULT_SOURCE_ADAPTER_KIND = "VMWARE"

# Property collected by the vCenter adapter that holds the tag string,
# e.g. "[<Environment-Production>, <Backup-Gold>]"
SOURCE_TAG_PROPERTY = "summary|tag"

# Adapter instance configuration keys
CFG_RESOURCE_KINDS = "resource_kinds"
CFG_PROPERTY_PREFIX = "property_prefix"
CFG_SPLIT_MODE = "split_mode"
CFG_KNOWN_CATEGORIES = "known_categories"
CFG_MULTI_VALUE_SEPARATOR = "multi_value_separator"
CFG_UNSET_VALUE = "unset_value"
CFG_SOURCE_ADAPTER_KIND = "source_adapter_kind"

DEFAULT_RESOURCE_KINDS = (
    "VirtualMachine,HostSystem,ClusterComputeResource,Datastore,Datacenter"
)
DEFAULT_PROPERTY_PREFIX = "summary|tag"
DEFAULT_SPLIT_MODE = "first"
DEFAULT_MULTI_VALUE_SEPARATOR = ", "
DEFAULT_UNSET_VALUE = "none"

# Number of resource IDs sent per Suite API "latest properties" query
PROPERTY_QUERY_BATCH_SIZE = 500
