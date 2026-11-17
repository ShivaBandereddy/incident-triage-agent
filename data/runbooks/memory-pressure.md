# Memory pressure

## Symptoms
- Alert: host memory usage above 95%
- Logs: "MemSched: host memory state changed to low"
- Logs: "Balloon: ballooning active on N VMs"
- Logs: "Swap: VM <name> swapped N MB to disk"
- Logs: "Alarm Host memory usage on <host> changed to Red, usage N%"
- VMs on the host become slow, and the host itself stays up and responding

## Likely causes
1. Memory overcommit: too many VMs or too much configured VM memory on one host
2. A VM with a memory leak or a sudden workload growth
3. Reduced cluster capacity after a host failure or maintenance, so remaining hosts carry more VMs
4. DRS not balancing, or large VM memory reservations limiting where VMs can run

## How to tell this apart from similar issues
- Host failure: the host stops responding and HA restarts VMs (see host-failure-ha.md). Memory pressure can appear on the other hosts after HA restarts VMs
- Datastore latency: slow I/O with latency messages and no ballooning or swapping logs (see datastore-latency.md). Heavy swapping can also add I/O load
- Datastore full: logs say "free space below threshold" (see datastore-full.md)
- NIC link flap: logs show vmnic link state changes (see nic-link-flap.md)
- Ballooning and swapping logs, with the host still responding, point here

## Diagnosis steps
1. Identify the host and check its memory usage, and whether the memory state is low
2. On the host run esxtop (memory view): check ballooned memory (MCTLSZ) and swapped memory (SWCUR) per VM
3. Find the VMs that use the most memory and check for a recent growth or a memory leak inside the guest
4. Check recent events: a host failure, HA restart or maintenance mode that moved VMs onto this host
5. Check cluster-wide memory headroom and DRS status

## Fix steps (suggestions only, never auto-run)
- Move VMs to other hosts with free memory (vMotion), or let DRS rebalance
- Power off or shut down VMs that are not needed, after confirming with the owner
- Right-size over-provisioned VMs, and review memory reservations and limits
- Add memory or add another host to the cluster

## Escalate when
- Host memory usage stays above 95% after VMs have been moved
- Critical VMs are heavily swapping
- Several hosts in the cluster show memory pressure at the same time (cluster capacity problem)
