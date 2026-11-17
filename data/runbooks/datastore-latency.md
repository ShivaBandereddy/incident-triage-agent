# Datastore latency

## Symptoms
- Alert: datastore read/write latency above 100 ms for 10 min
- Logs: "performance has deteriorated. I/O latency increased from X ms to Y ms"
- Logs: "Datastore <name> read latency Y ms exceeds threshold" and "I/O from VM stalled"
- Logs: "ScsiDeviceIO ... failed H:0x0 D:0x28 (queue full)"
- VMs on the datastore feel slow, but no host is down and no path is reported dead

## Likely causes
1. Overloaded storage array or a noisy-neighbour VM
2. Congested storage network (FC or iSCSI fabric)
3. Queue depth exhaustion on the host or array (queue full, D:0x28)
4. Failing disk behind the datastore (see raid-degraded.md if the controller reports a degraded array)

## How to tell this apart from similar issues
- Storage path down: logs say "path state changed to dead" or "lost path redundancy" (see storage-path-down.md)
- Datastore full: logs say "free space below threshold" or "no more space for virtual disk" (see datastore-full.md)
- RAID degraded: logs say "Virtual drive ... Degraded" or "SMART predictive failure" (see raid-degraded.md)
- Host failure: logs say "host is not responding" or HA restarts VMs (see host-failure-ha.md)
- Latency alone, with no dead path, no full datastore and no degraded array, points here

## Diagnosis steps
1. Identify which datastore and which hosts show the latency
2. On an affected host run esxtop (disk device view): high DAVG points to the array or fabric, high KAVG points to host-side queueing
3. Check top VMs by IOPS on that datastore for a noisy neighbour
4. Check storage array latency and fabric/switch port errors

## Fix steps (suggestions only, never auto-run)
- Move heavy VMs to another datastore (Storage vMotion)
- Rebalance workloads or add storage capacity
- Review queue depth settings with the storage team before changing anything

## Escalate when
- Latency stays above 100 ms for more than 30 minutes after mitigation
- Multiple datastores on the same array show latency at once
