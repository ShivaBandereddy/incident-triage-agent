# RAID degraded

## Symptoms
- Alert: storage controller reports a degraded array on a node
- Logs: "storcli: Disk slot N SMART predictive failure on <node>"
- Logs: "storcli: Virtual drive 0 state changed to Degraded, 1 drive offline"
- Logs: "storcli: Rebuild started on VD0 slot N"
- Logs: "kernel: megaraid_sas: Physical drive removed, enclosure N slot N"
- The node keeps running and data stays available, but it has no (or reduced) disk redundancy until the rebuild finishes

## Likely causes
1. A physical disk failed or reported SMART predictive failure
2. A drive was removed, loosened or reseated by mistake
3. Backplane, cable or controller problem affecting one or more slots
4. An older disk of the same batch and age that is likely to fail soon too

## How to tell this apart from similar issues
- Datastore latency: slow I/O with latency messages, and no controller degraded or drive logs (see datastore-latency.md). A rebuild can also add latency
- Storage path down: logs say "path state changed to dead" or "LOOP DOWN" on a fabric path (see storage-path-down.md)
- Datastore full: logs say "free space below threshold" (see datastore-full.md)
- Host failure: the host stops responding and HA restarts VMs (see host-failure-ha.md)
- Controller logs (storcli, megaraid_sas) showing a degraded virtual drive or a drive removed or failing point here

## Diagnosis steps
1. Identify the node, the enclosure and the slot of the affected drive from the logs
2. Check the virtual drive and physical drive status with the controller tool (for example storcli /c0 show, and the virtual and physical drive listings)
3. Check whether a rebuild is running and how far it has progressed, and whether a hot spare was used
4. Check the SMART status and age of the other drives in the same array
5. Check whether the drive was physically removed, or whether several slots report problems (backplane or cable)

## Fix steps (suggestions only, never auto-run)
- Replace the failed or predicted-to-fail drive with a vendor-supported drive, after confirming the correct slot (use the locate LED, so the wrong drive is not pulled)
- Let the rebuild finish, and confirm the virtual drive returns to Optimal
- Make sure a recent backup exists before changing disks
- If several slots report problems, ask the vendor to check the backplane, cable and controller

## Escalate when
- A second drive fails or reports predictive failure in the same array during the rebuild
- The virtual drive goes offline, or data is not accessible
- No replacement drive is available, or the rebuild does not progress
