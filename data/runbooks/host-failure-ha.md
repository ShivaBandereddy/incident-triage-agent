# Host failure with HA restart

## Symptoms
- Alert: host not responding in vCenter
- Logs: "fdm: host <name> is not responding"
- Logs: "fdm: host <name> datastore heartbeat lost on <datastore>"
- Logs: "fdm: HA initiating restart of N VMs from failed host <name>"
- Logs: "vpxd: VM <name> powered on by HA" (VMs restarted on other hosts)
- VMs on that host were briefly down, then came back on other hosts

## Likely causes
1. Host crash (PSOD, purple screen of death) or hardware fault (memory, motherboard, CPU)
2. Power loss to the host (PSU failure, PDU or circuit problem)
3. Host management network isolation (switch or uplink failure), where VMs may still be running
4. Host hung or rebooted after a firmware or driver problem

## How to tell this apart from similar issues
- Storage path down: the host stays up and responding, only a path or HBA is affected (see storage-path-down.md)
- NIC link flap: a vmnic goes down and up but the host stays reachable through another uplink (see nic-link-flap.md)
- Memory pressure: the host is alive with ballooning or swapping, and no HA restart happens (see memory-pressure.md)
- Datastore latency: slow I/O with the host still responding (see datastore-latency.md)
- "Host is not responding" together with "HA initiating restart" and VMs "powered on by HA" on other hosts points here

## Diagnosis steps
1. Identify the failed host and the list of VMs that HA restarted
2. Check the out-of-band console (iDRAC, iLO or UCS Manager) for power state, hardware events and a PSOD screen
3. Check whether the host answers ping on the management network: no ping with the console showing it running points to network isolation, not host failure
4. Check the other hosts' health and cluster capacity after the restarts (HA admission control, memory and CPU headroom)
5. Confirm that restarted VMs and their applications are healthy

## Fix steps (suggestions only, never auto-run)
- If the host crashed, collect logs or the core dump before rebooting it, then restart it and keep it in maintenance mode until the cause is known
- If hardware failed, open a vendor support case and replace the part
- If network isolation caused it, fix the uplink or switch port, then confirm the host reconnects to vCenter
- After recovery, check that VMs are balanced across hosts again (DRS)

## Escalate when
- More than one host fails in the same cluster
- HA could not restart some VMs (insufficient resources or restart failures)
- The same host fails again after a reboot
