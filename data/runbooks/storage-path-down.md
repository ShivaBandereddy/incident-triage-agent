# Storage path down

## Symptoms
- Alert: storage path redundancy lost on a host
- Logs: "path <vmhba:C:T:L> state changed to dead"
- Logs: "NMP: lost path redundancy to naa..., 1 active path remaining"
- Logs: "qlnativefc: vmhbaN: LOOP DOWN detected" (FC HBA lost link)
- Logs: "Path <vmhba:C:T:L> is down for device naa..."
- Datastores usually stay accessible through the remaining path, so VMs may run normally until a second failure

## Likely causes
1. Failed, loose or unplugged FC cable or SFP
2. FC switch port or HBA failure
3. Zoning or LUN masking change, or an array controller port down
4. Array controller failover or reboot

## How to tell this apart from similar issues
- Datastore latency: logs say "performance has deteriorated" or "latency increased", with no path state change (see datastore-latency.md)
- Host failure: the host itself stops responding and HA restarts VMs (see host-failure-ha.md)
- RAID degraded: a local controller reports a degraded virtual drive or SMART failure, not a fabric path (see raid-degraded.md)
- NIC link flap: link state changes on a vmnic (network uplink), not on a vmhba (storage HBA) (see nic-link-flap.md)
- A dead path or LOOP DOWN on a vmhba, with the datastore still reachable through another path, points here

## Diagnosis steps
1. Identify the host, the vmhba and the device (naa ID) from the logs
2. On the host, list paths for the device (esxcli storage core path list) and see which are dead and which are active
3. Check whether other hosts lose paths to the same target: one host points to its HBA or cable, many hosts point to the switch or the array
4. Check FC switch port status and SFP light levels, and array controller port status

## Fix steps (suggestions only, never auto-run)
- Reseat or replace the cable or SFP on the affected port
- After the fix, rescan the storage adapters and confirm all paths show active
- If several hosts are affected, ask the storage team to check zoning and array ports

## Escalate when
- Only one active path remains for more than 15 minutes (one more failure would lose the datastore)
- All paths to a device are down
