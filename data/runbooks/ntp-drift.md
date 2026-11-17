# NTP drift

## Symptoms
- Alert: authentication failures on a node
- Logs: "ntpd: time sync lost, offset N s"
- Logs: "krb5: Clock skew too great while authenticating to AD"
- Logs: "sshd: pam_krb5: authentication failure for <user> (clock skew)"
- Logs: "chronyd: Cannot synchronise: no selectable sources"
- Users and services fail to log in with Kerberos / AD accounts, while the password is correct and the node is otherwise healthy

## Likely causes
1. NTP server down or unreachable from the node
2. Firewall or network blocking NTP (UDP port 123)
3. Wrong or missing NTP server in the node configuration, or the NTP / chrony service stopped
4. Hardware clock drift, or a VM clock that conflicts with the host time sync

## How to tell this apart from similar issues
- DNS failure: names cannot be resolved, while here name resolution works and the error mentions clock skew (see dns-failure.md)
- Certificate expiry: TLS errors with "certificate has expired", without clock skew messages (see cert-expiry.md)
- Host failure: the node stops responding and HA restarts VMs (see host-failure-ha.md)
- A wrong password also causes authentication failures, but it does not log "clock skew" or "time sync lost"
- Authentication failures together with "clock skew" and a time sync lost message point here

## Diagnosis steps
1. Identify the node and check its current time against a trusted time source or the domain controller
2. Check the sync status and offset (chronyc tracking and chronyc sources, or ntpq -p)
3. Check that the node can reach the NTP servers (network path and UDP port 123)
4. Check the NTP server health, and whether other nodes also drift
5. Check the NTP configuration on the node, and VM time sync settings if the node is a VM

## Fix steps (suggestions only, never auto-run)
- Restore the NTP server or the network path to it, and correct the NTP server list in the configuration
- Restart the NTP or chrony service, and confirm the offset goes back to near zero
- If the time is far off, correct it with approval and then let NTP keep it in sync
- After the time is correct, check that Kerberos / AD logins work again

## Escalate when
- The offset is more than a few minutes on many nodes at the same time (NTP infrastructure problem)
- Time drifts again soon after being corrected
- Domain controllers themselves have the wrong time
