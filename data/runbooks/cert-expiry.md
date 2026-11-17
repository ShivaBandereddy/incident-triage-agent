# Certificate expiry

## Symptoms
- Alert: API calls failing with TLS errors on a host
- Logs: "vpxd: TLS handshake failed: certificate has expired"
- Logs: "hostd: SSL certificate for <host> expired on <date>"
- Logs: "vpxa: Authentication failed: certificate verify failed (certificate has expired)"
- Logs: "rhttpproxy: SSL_accept failed: sslv3 alert certificate expired"
- Hosts disconnect from vCenter, or API clients and tools fail to connect, while the network and name resolution work

## Likely causes
1. The host or vCenter SSL certificate reached its expiry date and was not renewed
2. Automatic renewal failed, or nobody owned the renewal process
3. The CA (root or intermediate) certificate expired
4. A wrong system clock makes a valid certificate look expired (check this first)

## How to tell this apart from similar issues
- NTP drift: errors mention "clock skew" or "time sync lost", and a wrong clock can also make certificates look expired (see ntp-drift.md)
- DNS failure: names cannot be resolved, "Name or service not known" (see dns-failure.md)
- Host failure: the host stops responding and HA restarts VMs (see host-failure-ha.md)
- NIC link flap: vmnic link state changes (see nic-link-flap.md)
- TLS errors that say "certificate has expired", with the clock correct and DNS working, point here

## Diagnosis steps
1. Identify which service or host reports the error, and which certificate it uses
2. Check the system clock on both sides first, so a wrong clock is ruled out
3. Check the certificate validity dates (for example openssl s_client -connect <host>:443, then openssl x509 -noout -dates)
4. Check how many hosts and services use certificates from the same CA or the same date
5. Check whether the CA certificate is also expired or close to expiry

## Fix steps (suggestions only, never auto-run)
- Renew or replace the expired certificate using the vendor-supported procedure (for ESXi hosts, renew the host certificate; for vCenter, the certificate manager)
- Take a backup or snapshot before changing vCenter certificates, and plan a change window
- Reconnect hosts to vCenter and restart the affected services only as the vendor documents
- After renewal, check that API clients and monitoring connect again
- Add certificate expiry monitoring with alerts 30 days before the expiry date

## Escalate when
- The vCenter machine certificate or the root CA certificate is expired
- Many hosts or services are affected at the same time
- Hosts cannot reconnect to vCenter after renewal
