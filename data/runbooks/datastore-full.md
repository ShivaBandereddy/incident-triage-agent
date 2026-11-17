# Datastore full

## Symptoms
- Alert: datastore usage above 95%
- Logs: "Datastore <name> free space N% below 5% threshold"
- Logs: "Snapshot consolidation failed for <vm>: insufficient space on <datastore>"
- Logs: "Alarm Datastore usage on disk <name> changed to Red"
- Logs: "VM <name> suspended, no more space for virtual disk on <datastore>"
- VMs on the datastore pause or fail to power on, and snapshot or backup jobs fail

## Likely causes
1. Old or large snapshots (delta disks) growing and never consolidated
2. Thin-provisioned disks growing beyond the datastore capacity (overcommit)
3. Too many VMs placed on one datastore, or no capacity planning
4. Leftover files: orphaned disks, old ISO images, VM swap files, large log files

## How to tell this apart from similar issues
- Datastore latency: space is normal but I/O is slow ("latency increased") (see datastore-latency.md)
- Storage path down: logs say "path state changed to dead", and free space is normal (see storage-path-down.md)
- RAID degraded: a controller reports a degraded virtual drive or SMART failure (see raid-degraded.md)
- Memory pressure: the problem is host memory (ballooning, swapping), not datastore space (see memory-pressure.md)
- Free space below the threshold, together with failed snapshot consolidation or a suspended VM, points here

## Diagnosis steps
1. Identify the datastore and check capacity, used space, free space and provisioned space
2. Find VMs with snapshots and check the snapshot sizes and ages (large delta files)
3. Check thin-provisioned disks that can still grow, and the total provisioned space against the capacity
4. Look for orphaned files and unused ISO images on the datastore
5. Check which VMs are suspended, waiting for a space question to be answered

## Fix steps (suggestions only, never auto-run)
- Consolidate or delete old snapshots after confirming with the VM owner
- Move VMs to another datastore (Storage vMotion) to free space
- Add capacity: extend the datastore or add a new LUN
- Remove orphaned files and unused ISO images after confirming they are not needed
- After space is freed, retry the VM question or resume the suspended VMs

## Escalate when
- Free space stays below 5% after cleanup and no space can be freed quickly
- VMs hosting critical services are suspended
- The datastore keeps filling up fast (capacity planning needed)
