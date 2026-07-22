LABEL_SANDBOX_ID = "orbyte.app/sandbox-id"
LABEL_TENANT_ID = "orbyte.app/tenant-id"
LABEL_K8S_COMPONENT = "app.kubernetes.io/component"
LABEL_K8S_COMPONENT_SANDBOX = "sandbox"
LABEL_K8S_MANAGED_BY = "app.kubernetes.io/managed-by"
LABEL_K8S_MANAGED_BY_ORBYTE = "orbyte"

# Docker-backend equivalents of the K8s component label. The proxy's
# DockerEventsLookup filters on these; ``docker_sandbox_manager`` stamps them
# onto every sandbox container it creates.
LABEL_DOCKER_COMPONENT = "orbyte.app/component"
LABEL_DOCKER_COMPONENT_SANDBOX = "craft-sandbox"
