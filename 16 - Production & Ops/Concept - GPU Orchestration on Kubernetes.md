---
tags: [concept, domain/production-ops, level/advanced]
aliases: [K8s GPU scheduling, NVIDIA GPU Operator, MIG]
summary: "Scheduling and sharing GPUs for LLM inference on Kubernetes: device plugin semantics, MIG/time-slicing/MPS, gang scheduling, cold starts."
---

> **One-paragraph hook:** Running LLM inference on Kubernetes means fighting a scheduler designed for stateless, horizontally-fungible CPU pods against a resource that is expensive, physically scarce, unshareable by default, and takes minutes rather than milliseconds to warm up. Getting GPUs onto pods reliably — without wasting most of a $2–3/hr H100 on a model that needs a fraction of it — is its own discipline, sitting underneath [[Concept - Autoscaling LLM Inference]] and downstream of the [[Decision - Self-Hosting vs Managed LLM API]] choice that leads a team here in the first place.

## The mechanism

Kubernetes exposes a GPU as an *extended resource*, `nvidia.com/gpu`, advertised to the kubelet by the NVIDIA device plugin — a daemon running on every GPU node that discovers the physical devices and registers their count via the kubelet's device-plugin API. Extended resources are integers with no default overcommit: a pod's `resources.requests` and `resources.limits` for `nvidia.com/gpu` must be equal, and the scheduler only binds a pod to a node with that many *whole* GPUs still free. There is no CPU-style `0.5` request — the device-plugin allocation API hands back whole device IDs, sets `NVIDIA_VISIBLE_DEVICES` in the container, and the `nvidia-container-toolkit` mounts the corresponding `/dev/nvidia*` character devices into the container's namespace. A 7B model that needs 20GB of an 80GB card's memory still occupies the entire GPU as far as the scheduler is concerned.

Three sharing mechanisms trade isolation for utilization differently:

| Mechanism | Isolation | How it works | Best for |
|---|---|---|---|
| MIG | Hardware (memory + fault) | Partitions an A100/H100 into up to 7 slices (e.g. `1g.10gb` profiles on an 80GB A100), each with a dedicated SM, L2-cache, and memory-bandwidth share, tied to the [[Concept - GPU Memory Hierarchy]] this note assumes | Multi-tenant workloads that need hard isolation |
| Time-slicing | None | Software round-robin context switching on one physical GPU; every process sees the full device but shares it serially | Bursty or low-priority workloads where isolation doesn't matter |
| MPS | Partial (no memory protection) | A single CUDA context server lets multiple processes submit kernels concurrently instead of serializing, cutting context-switch overhead vs. time-slicing | Many small, mutually-trusted concurrent inference processes |

MIG is the only option that survives a noisy or hostile neighbor without one process's OOM taking down another's inference server; time-slicing and MPS trade that safety for higher utilization when tenants are mutually trusted.

NVIDIA's **GPU Operator** packages the driver install (or a containerized driver), the container toolkit, the device-plugin daemonset, the DCGM metrics exporter (temperature, power, ECC error counts, utilization — feeding Prometheus/Grafana), and node feature discovery (labeling nodes by GPU generation) into one manageable component, instead of hand-provisioning drivers across a heterogeneous fleet that inevitably drifts out of sync.

Scheduling uses taints/tolerations to dedicate GPU node pools, plus node affinity to pin to a specific GPU generation. For multi-GPU pods, topology matters: two GPUs on the same NVLink domain communicate far faster than two GPUs split across a PCIe switch, so topology-aware placement (or simply keeping a multi-GPU pod single-node) avoids silently degrading tensor-parallel inference. For workloads spanning multiple nodes — a large model sharded across nodes — you need *gang scheduling*: Volcano or Kueue's `PodGroup` construct schedules the whole set of pods atomically, all-or-nothing, so a partially-scheduled job doesn't sit holding GPUs on one node while waiting forever for the rest of the gang.

The dominant cold-start cost for an LLM pod isn't container startup, it's loading tens to hundreds of gigabytes of weights (a 70B model at fp16 is roughly 140GB — the arithmetic behind [[Reference - Memory Math for Transformers]]) from an image pull or network volume into host memory and then VRAM, plus CUDA context init and, for engines like [[Breakdown - vLLM]], CUDA-graph capture. That sequence commonly takes one to ten minutes for large models, mitigated with baked-in model layers, read-many PVC-backed model caches, init containers that pre-fetch weights to local NVMe ahead of the main container starting, or safetensors-mmap-style streaming loads that overlap disk read with VRAM population.

## In practice

A typical pod spec sets `resources.limits: {nvidia.com/gpu: 1}` (or an alternate resource name like `nvidia.com/mig-1g.10gb` for a MIG slice); `kubectl describe node` shows allocatable/free GPU counts; DCGM-exporter metrics feed Grafana dashboards for temperature, ECC errors, and utilization. Real deployments include KServe, Ray Serve / KubeRay, NVIDIA Triton Inference Server behind the GPU Operator, and production [[Breakdown - vLLM]] deployments. Node-pool size itself is derived from the concurrency ceiling [[Concept - LLM Load Testing and Capacity Planning]] finds via load testing, not chosen in the abstract — and [[Concept - Autoscaling LLM Inference]] governs how replica count moves within that fixed pool of nodes.

## Failure modes

**GPU fragmentation.** Pods stuck `Pending` with "Insufficient nvidia.com/gpu" despite the cluster showing free GPU capacity elsewhere, because the free GPUs are scattered as partial per-node availability rather than concentrated where the pod's full request can land.

**Xid / ECC errors.** A physically degrading GPU throws Xid codes (DCGM surfaces them — e.g. a code indicating the GPU fell off the bus) requiring cordon-and-drain of the node, the operational pattern covered generally in [[Gotchas - Hardware Failures at Scale]].

**Shared-GPU OOM.** Under time-slicing or MPS, one tenant's memory spike can starve or crash a co-located tenant's process, because neither mechanism enforces memory isolation the way MIG does.

**Cold start outruns the scaling signal.** Because weight loading takes minutes, a scale-up triggered by a load spike routinely arrives too late to help that spike — the seam with [[Concept - Autoscaling LLM Inference]], which has to treat cold-start time as a hard constraint on responsiveness, not a tuning parameter.

**Driver/toolkit skew.** A partial GPU Operator upgrade across a heterogeneous node fleet leaves a subset of nodes on a different driver version than the container expects, producing crash loops that look like an application bug rather than an infra drift.

These and related pitfalls are collected in [[Gotchas - LLM Production Operations]].

## The non-obvious

"Requests must equal limits" isn't a policy Kubernetes operators chose for GPUs — it's forced by the device-plugin API, which only hands out whole integer devices with no overcommit path. That means "one small model wastes a whole $30–40k GPU" isn't a misconfiguration to fix; it's the default behavior of vanilla Kubernetes, and MIG/time-slicing/MPS exist specifically as workarounds bolted onto a scheduler that fundamentally doesn't understand fractional, shareable accelerators the way it understands fractional CPU. Teams that reach for GPU orchestration on Kubernetes without first confirming — via the math in [[Decision - Self-Hosting vs Managed LLM API]] — that utilization will be high enough to justify owning that complexity often end up recreating, at greater operational cost, exactly the low-utilization waste a managed API would have avoided.

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
