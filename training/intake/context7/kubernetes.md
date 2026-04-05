# Kubernetes
> Source: Context7 MCP | Category: infra
> Fetched: 2026-04-04

### Create a Deployment — Concepts

Source: https://kubernetes.io/docs/tutorials/_print

A Kubernetes Pod is the smallest deployable unit, consisting of one or more containers that share networking and storage. A Deployment acts as a management layer that monitors the health of Pods, ensuring they remain running and handling restarts if a container terminates. Using Deployments is the standard best practice for scaling and managing the lifecycle of application Pods within a cluster.

---

### Manage Deployment and Service

Source: https://kubernetes.io/docs/tutorials/_print

Commands to apply the deployment, verify pod status, expose the deployment as a service, and port-forward for local access.

```bash
kubectl apply -f https://k8s.io/examples/deployments/deployment-with-configmap-and-sidecar-container.yaml
kubectl get pods --selector=app.kubernetes.io/name=configmap-sidecar-container
kubectl expose deployment configmap-sidecar-container --name=configmap-sidecar-service --port=8081 --target-port=80
kubectl port-forward service/configmap-sidecar-service 8081:8081 &
```

---

### Manage Deployment Lifecycle

Source: https://kubernetes.io/docs/tutorials/configuration/updating-configuration-via-a-configmap

Commands to apply the deployment manifest, verify pod status, and expose the application via a service.

```bash
kubectl apply -f https://k8s.io/examples/deployments/deployment-with-configmap-and-sidecar-container.yaml
kubectl get pods --selector=app.kubernetes.io/name=configmap-sidecar-container
kubectl expose deployment configmap-sidecar-container --name=configmap-sidecar-service --port=8081 --target-port=80
```

---

### Interact with Kubernetes Deployments and Services using kubectl

Source: https://kubernetes.io/docs/reference/kubectl/quick-reference

Commands for interacting with Kubernetes Deployments and Services, including retrieving logs, forwarding ports, and executing commands within pods.

```bash
kubectl logs deploy/my-deployment                         # dump Pod logs for a Deployment (single-container case)
kubectl logs deploy/my-deployment -c my-container         # dump Pod logs for a Deployment (multi-container case)

kubectl port-forward svc/my-service 5000                  # listen on local port 5000 and forward to port 5000 on Service backend
kubectl port-forward svc/my-service 5000:my-service-port  # listen on local port 5000 and forward to Service target port with name <my-service-port>

kubectl port-forward deploy/my-deployment 5000:6000       # listen on local port 5000 and forward to port 6000 on a Pod created by <my-deployment>
kubectl exec deploy/my-deployment -- ls                   # run command in first Pod and first container in Deployment (single- or multi-container cases)
```

---

### Manage Kubernetes Pod and Service Lifecycle

Source: https://kubernetes.io/docs/tutorials/security/seccomp

Commands to deploy, inspect, expose, and clean up Kubernetes resources.

```bash
kubectl apply -f https://k8s.io/examples/pods/security/seccomp/ga/audit-pod.yaml
kubectl get pod audit-pod
kubectl expose pod audit-pod --type NodePort --port 5678
kubectl get service audit-pod
kubectl delete service audit-pod --wait
kubectl delete pod audit-pod --wait --now
```
