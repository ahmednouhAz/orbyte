.PHONY: craft-sandbox-image craft-backend-image

# Requires an existing local Kubernetes cluster (e.g. kind) with the sandbox
# image loaded into it. The Helm-based one-shot cluster setup that used to
# live at deployment/helm/dev/ has been removed along with the Helm chart -
# Craft's Docker-mode sandbox backend (this product's actual deployment
# path) doesn't need it. These two targets remain for anyone testing
# against a manually-provisioned Kubernetes-mode sandbox cluster.
craft-sandbox-image:
	docker build -t onyxdotapp/sandbox:dev backend/orbyte/server/features/build/sandbox/image
	kind load docker-image onyxdotapp/sandbox:dev --name orbyte-dev

# Rebuild the image the in-cluster sandbox-proxy/api-server run, then restart them.
craft-backend-image:
	docker build -t onyxdotapp/onyx-backend:dev backend/
	kind load docker-image onyxdotapp/onyx-backend:dev --name orbyte-dev
	kubectl rollout restart deploy/orbyte-sandbox-proxy deploy/orbyte-api-server -n orbyte
