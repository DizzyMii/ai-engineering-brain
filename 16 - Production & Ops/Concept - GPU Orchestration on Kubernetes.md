---
tags: [concept, domain/production-ops, level/advanced]
aliases: [K8s GPU scheduling, NVIDIA GPU Operator, MIG]
summary: "Scheduling and sharing GPUs for LLM inference on Kubernetes: device plugin semantics, MIG/time-slicing/MPS, gang scheduling, cold starts."
---

> **One-paragraph hook:** Running LLM inference on Kubernetes pits a scheduler built for stateless, interchangeable CPU pods against a resource that's expensive, physically scarce, unshareable by default, and takes minutes instead of milliseconds to warm up. Getting GPUs onto pods reliably, without wasting most of a $2–3/hr H100 on a model that needs a fraction of it, is its own discipline. It sits underneath [[Concept - Autoscaling LLM Inference]] and downstream of the [[Decision - Self-Hosting vs Managed LLM API]] choice that brings a team here in the first place.

## The mechanism

Kubernetes exposes a GPU as an *extended resource*, `nvidia.com/gpu`, which the NVIDIA device plugin advertises to the kubelet. The plugin is a daemon on every GPU node that discovers the physical devices and registers their count through the kubelet's device-plugin API. Extended resources are integers with no default overcommit. A pod's `resources.requests` and `resources.limits` for `nvidia.com/gpu` must be equal, and the scheduler only binds the pod to a node with that many *whole* GPUs free. There's no CPU-style `0.5` request. The allocation API hands back whole device IDs and sets `NVIDIA_VISIBLE_DEVICES` in the container, and `nvidia-container-toolkit` mounts the matching `/dev/nvidia*` character devices into the container's namespace. A 7B model that needs 20GB of an 80GB card still takes the entire GPU as far as the scheduler is concerned.

Three sharing mechanisms trade isolation for utilization in different ways:

| Mechanism | Isolation | How it works | Best for |
|---|---|---|---|
| MIG | Hardware (memory + fault) | Partitions an A100/H100 into up to 7 slices (e.g. `1g.10gb` profiles on an 80GB A100), each with a dedicated SM, L2-cache, and memory-bandwidth share, tied to the [[Concept - GPU Memory Hierarchy]] this note assumes | Multi-tenant workloads that need hard isolation |
| Time-slicing | None | Software round-robin context switching on one physical GPU; every process sees the full device but shares it serially | Bursty or low-priority workloads where isolation doesn't matter |
| MPS | Partial (no memory protection) | A single CUDA context server lets multiple processes submit kernels concurrently instead of serializing, cutting context-switch overhead vs. time-slicing | Many small, mutually-trusted concurrent inference processes |

Only MIG survives a noisy or hostile neighbor without one process's OOM taking down another's inference server. Time-slicing and MPS give up that safety for higher utilization when tenants trust each other.

NVIDIA's **GPU Operator** bundles the driver install (or a containerized driver), the container toolkit, the device-plugin daemonset, the DCGM metrics exporter (temperature, power, ECC error counts, utilization, feeding Prometheus/Grafana) and node feature discovery (labeling nodes by GPU generation) into one component. The alternative is hand-provisioning drivers across a heterogeneous fleet that will drift out of sync.

Scheduling uses taints/tolerations to dedicate GPU node pools and node affinity to pin a specific GPU generation. For multi-GPU pods, topology matters. Two GPUs on the same NVLink domain talk far faster than two split across a PCIe switch, so topology-aware placement (or just keeping a multi-GPU pod on one node) keeps tensor-parallel inference from silently slowing down. Workloads spanning several nodes, such as a large model sharded across nodes, need *gang scheduling*. Volcano's or Kueue's `PodGroup` schedules the whole set of pods atomically, all or nothing, so a partly scheduled job doesn't hold GPUs on one node while waiting forever for the rest.

The main cold-start cost for an LLM pod is loading weights, not starting the container: tens to hundreds of gigabytes (a 70B model at fp16 is roughly 140GB; see [[Reference - Memory Math for Transformers]] for the arithmetic) from an image pull or network volume into host memory and then VRAM. Add CUDA context init and, for engines like [[Breakdown - vLLM]], CUDA-graph capture. For large models that commonly takes one to ten minutes. Mitigations include baked-in model layers, read-many PVC-backed model caches, init containers that pre-fetch weights to local NVMe before the main container starts, and safetensors-mmap-style streaming loads that overlap disk reads with VRAM population.

## In practice

A typical pod spec sets `resources.limits: {nvidia.com/gpu: 1}` (or an alternate resource name like `nvidia.com/mig-1g.10gb` for a MIG slice). `kubectl describe node` shows allocatable/free GPU counts, and DCGM-exporter metrics feed Grafana dashboards for temperature, ECC errors and utilization. Real deployments include KServe, Ray Serve / KubeRay, NVIDIA Triton Inference Server behind the GPU Operator, and production [[Breakdown - vLLM]] deployments. Node-pool size comes from the concurrency ceiling that [[Concept - LLM Load Testing and Capacity Planning]] finds through load testing, not from a guess, and [[Concept - Autoscaling LLM Inference]] governs how replica count moves within that fixed pool.

## Failure modes

**GPU fragmentation.** Pods stuck `Pending` with "Insufficient nvidia.com/gpu" while the cluster shows free GPU capacity, because the free GPUs are scattered across nodes and no single node has enough for the pod's full request.

**Xid / ECC errors.** A physically degrading GPU throws Xid codes (DCGM surfaces them, e.g. a code meaning the GPU fell off the bus), and the node has to be cordoned and drained. [[Gotchas - Hardware Failures at Scale]] covers that pattern in general.

**Shared-GPU OOM.** Under time-slicing or MPS, one tenant's memory spike can starve or crash a co-located tenant's process, since neither enforces memory isolation the way MIG does.

**Cold start outruns the scaling signal.** Weight loading takes minutes, so a scale-up triggered by a load spike routinely arrives too late to help. This is where [[Concept - Autoscaling LLM Inference]] comes in: it has to treat cold-start time as a hard limit on responsiveness, not a tuning parameter.

**Driver/toolkit skew.** A partial GPU Operator upgrade across a heterogeneous fleet leaves some nodes on a driver version the container doesn't expect. The crash loops look like an application bug when the cause is infra drift.

[[Gotchas - LLM Production Operations]] collects these and related pitfalls.

## The non-obvious

Kubernetes operators didn't choose "requests must equal limits" as a GPU policy. The device-plugin API forces it, since it only hands out whole integer devices and has no overcommit path. So "one small model wastes a whole $30–40k GPU" isn't a misconfiguration you can fix. It's how vanilla Kubernetes behaves, and MIG, time-slicing and MPS are workarounds bolted onto a scheduler that doesn't understand fractional, shareable accelerators the way it understands fractional CPU. Teams that take on GPU orchestration on Kubernetes without first checking, with the math in [[Decision - Self-Hosting vs Managed LLM API]], that utilization will be high enough to justify the complexity often end up recreating the same low-utilization waste a managed API would have avoided, at higher operational cost.

## Connections

- [[Concept - Autoscaling LLM Inference]] — replica-count changes happen inside the GPU node pool this note describes; cold-start time here is the hard constraint autoscaling policy has to respect.
- [[Concept - GPU Memory Hierarchy]] — MIG's hardware partitioning literally slices the SM/L2/memory-bandwidth hierarchy this note explains.
- [[Reference - Memory Math for Transformers]] — the weight-size arithmetic that determines how much VRAM a model needs, and therefore whether it fits on a MIG slice or needs a full card.
- [[Breakdown - vLLM]] — the serving engine most commonly run inside these pods, and the source of the CUDA-graph-capture cold-start cost described above.
- [[Concept - LLM Load Testing and Capacity Planning]] — node-pool size is derived from the concurrency ceiling this note's load testing finds, not chosen a priori.
- [[Decision - Self-Hosting vs Managed LLM API]] — the upstream decision that determines whether a team needs GPU orchestration on Kubernetes at all.
- [[Gotchas - LLM Production Operations]] — the broader collection of production pitfalls this note's failure modes feed into.
- [[Gotchas - Hardware Failures at Scale]] — the Xid/ECC-error handling and cordon-and-drain procedure this note's hardware failure mode points to.

## Sources

- NVIDIA — GPU Operator and Device Plugin for Kubernetes documentation — the driver/toolkit/device-plugin/DCGM automation described above.
- Kubernetes device plugin framework (Kubernetes SIG-Node) — the extended-resource, integer-only allocation API that forces `requests == limits` for GPUs.
- Volcano (CNCF) and Kueue (Kubernetes SIGs) — the gang-scheduling systems (`PodGroup`) used for multi-node GPU jobs.
