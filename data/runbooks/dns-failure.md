# DNS failure

## Symptoms
- Alert: management connectivity lost, host cannot resolve vcenter.corp.local
- Logs: "resolver: failed to resolve <name>: Name or service not known"
- Logs: "resolver: SERVFAIL for <name> from <dns server>"
- Logs: "hostd: cannot reach vCenter <name>, DNS lookup timed out"
- Logs: "resolver: no response from nameserver <dns server>"
- The host or service is up, but anything that needs a name (vCenter, AD, backup, monitoring) fails, while connections by IP address still work

## Likely causes
1. DNS server down, overloaded or its DNS service stopped
2. Network path to the DNS server blocked (firewall change, routing or VLAN issue)
3. Wrong DNS server address or search domain in the host configuration
4. Missing or stale DNS record, or a problem in the DNS zone

## How to tell this apart from similar issues
- NIC link flap: logs show vmnic link state down / up, here the link stays stable (see nic-link-flap.md)
- Host failure: the host itself stops responding and HA restarts VMs (see host-failure-ha.md)
- Certificate expiry: TLS handshake errors with "certificate has expired", while name resolution works (see cert-expiry.md)
- NTP drift: authentication errors with "clock skew", while name resolution works (see ntp-drift.md)
- Name lookups failing (no response, SERVFAIL, "Name or service not known"), while ping by IP works, points here

## Diagnosis steps
1. Identify which hosts and services fail, and which names cannot be resolved
2. From the host, try ping by IP address to the target: if IP works and the name fails, it is DNS
3. Check the DNS servers configured on the host (esxcli network ip dns server list), and test each one with a lookup (nslookup)
4. Check whether the DNS servers themselves are up, reachable and answering other queries
5. Check recent changes: firewall rules, DNS server updates, record changes, host network settings

## Fix steps (suggestions only, never auto-run)
- Restore or restart the DNS service on the failed DNS server
- Point the host to a working secondary DNS server, and correct wrong addresses or search domains
- Fix the firewall or routing rule that blocks DNS (port 53, UDP and TCP)
- Add or correct the missing DNS record
- As a temporary workaround only, with approval, add a static hosts entry on the host, and remove it after DNS is fixed

## Escalate when
- All configured DNS servers are down or unreachable
- Many hosts or services fail at the same time (infrastructure-wide DNS problem)
- vCenter cannot be reached by hosts, and HA or management operations are affected
