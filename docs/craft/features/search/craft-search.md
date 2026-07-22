# Craft Search

Craft search uses the standard `orbyte-cli` bundled into the sandbox image. The sandbox calls the
CLI as an ordinary internet client; it does not connect directly to the Orbyte API server or any
cluster-internal service.

Search requests flow out through the egress proxy, which recognizes the Orbyte search traffic and
injects a scoped Orbyte PAT before forwarding the request. This keeps the credential out of the
sandbox while still allowing search to run as the sandbox user.

The extra internet round trip is intentional. Sandboxes should not be able to initiate connections
to anything inside the cluster, so even first-party Orbyte API calls use the same external egress path
as other network traffic.
