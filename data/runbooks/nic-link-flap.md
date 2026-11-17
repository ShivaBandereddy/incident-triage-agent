# NIC link flap

## Symptoms
- Alert: uplink (vmnic) flapping on a host
- Logs: "Link: vmnicN link state down" followed by "link state up", repeating
- Logs: "Uplink: vmnicN flapping, N transitions in 60 s"
- Logs: "Net: uplink vmnicN marked down by beacon probing, failover to remaining uplink"
- Brief network drops or packet loss for VMs, usually recovering on their own as traffic fails over to another uplink

## Likely causes
1. Bad or loose network cable, or a failing SFP / transceiver
2. Faulty switch port or switch line card
3. NIC driver or firmware problem
4. Speed or duplex mismatch, or a LACP / port-channel misconfiguration

## How to tell this apart from similar issues
- Host failure: the host stops responding completely and HA restarts VMs (see host-failure-ha.md)
- Storage path down: the link or path loss is on a vmhba (storage HBA), not on a vmnic (see storage-path-down.md)
- DNS failure: the network link is stable, but names cannot be resolved (see dns-failure.md)
- Memory pressure: no link state changes in the logs (see memory-pressure.md)
- Repeated link down / up transitions on the same vmnic, with the host still reachable through another uplink, points here

## Diagnosis steps
1. Identify the host and the vmnic from the logs, and count how many transitions happen per minute
2. On the host, check the NIC status, speed and duplex (esxcli network nic list)
3. Check the switch port for errors (CRC errors, link flaps, err-disable) and its logs
4. Check whether other hosts on the same switch also flap: one host points to its cable or NIC, many hosts point to the switch
5. Check NIC driver and firmware versions against the vendor compatibility list

## Fix steps (suggestions only, never auto-run)
- Replace the cable or SFP, or move the connection to another switch port
- Update the NIC driver or firmware to a supported version
- Verify teaming and failover order, and that the switch and host agree on speed, duplex and LACP settings
- Keep the flapping uplink out of the team until the cause is fixed

## Escalate when
- All uplinks of a host flap at the same time, or the management network is lost
- Flapping continues after the cable, SFP and switch port have been replaced
- Several hosts on the same switch show flapping
