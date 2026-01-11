# Hardening Guide

This guide covers security hardening for all VMs in the Threat Hunting Lab. Hardening reduces the attack surface by closing unnecessary ports, tightening SSH settings, and adding security tools like fail2ban.

## Overview

We've broken down hardening into reusable functions that all VMs use, plus VM-specific steps. This guide covers:

- What each hardening step does
- How to apply hardening to each VM
- How to test that hardening didn't break anything
- What to do if something goes wrong

## Common Hardening Functions

The `hosts/shared/hardening_common.sh` file provides reusable hardening functions used by all VMs.

### Available Functions

1. **`configure_firewall(ports, allowed_ips)`** - Configures ufw firewall
2. **`configure_ssh(disable_root, port, timeout)`** - Configures SSH security
3. **`install_fail2ban(services)`** - Installs and configures fail2ban
4. **`configure_logrotate(config_file, log_path)`** - Configures log rotation
5. **`configure_auto_updates()`** - Configures automatic security updates
6. **`configure_auditd()`** - Configures system auditing (optional)

### Usage

These functions are sourced by VM-specific hardening scripts:

```bash
source hosts/shared/hardening_common.sh

# Configure firewall
configure_firewall "22,5432,8888" "10.0.0.0/24"

# Configure SSH
configure_ssh true 22 300

# Install fail2ban
install_fail2ban "sshd,postgresql"
```

## Hardening Procedure

### Step 1: Test Before Hardening

**Important:** Always test before hardening! This creates a baseline so you can verify that hardening didn't break anything.

```bash
cd /path/to/th_timmy
./hosts/shared/test_before_after_hardening.sh
```

The script will:
1. Run all connection and data flow tests
2. Save the results (you'll see files like `before_hardening_connections_*.json`)
3. Wait for you to apply hardening on all VMs
4. Run the tests again after you're done
5. Show you a comparison of before vs after

This is really useful when something breaks - you'll know immediately if it was the hardening that caused it.

### Step 2: Apply Hardening

Apply hardening on each VM using the VM-specific hardening scripts:

#### VM-01: Ingest/Parser

```bash
# On VM-01
cd /path/to/th_timmy
./hosts/vm01-ingest/harden_vm01.sh
```

#### VM-02: Database

```bash
# On VM-02
cd /path/to/th_timmy
./hosts/vm02-database/harden_vm02.sh
```

#### VM-03: Analysis/Jupyter

```bash
# On VM-03
cd /path/to/th_timmy
./hosts/vm03-analysis/harden_vm03.sh
```

#### VM-04: Orchestrator

```bash
# On VM-04
cd /path/to/th_timmy
./hosts/vm04-orchestrator/harden_vm04.sh
```

### Step 3: Verify Hardening

After applying hardening on all VMs, return to the test script and press Enter to continue. The script will:
1. Run tests after hardening
2. Compare results with baseline
3. Show differences

## Hardening Components

### Firewall Configuration

The firewall (ufw) is configured to:
- Deny all incoming connections by default
- Allow only necessary ports
- Restrict access by IP address (optional)

**Important**: Always allow SSH (port 22) to avoid locking yourself out!

### SSH Security

SSH is hardened by:
- Disabling root login
- Changing default port (optional)
- Setting connection timeout
- Enabling key-based authentication

### Fail2ban

Fail2ban protects against brute-force attacks by:
- Monitoring authentication failures
- Banning IP addresses after multiple failures
- Configurable ban time and retry limits

### Automatic Updates

Automatic security updates ensure:
- Critical security patches are applied promptly
- System stays up-to-date with minimal manual intervention
- Unused packages are removed automatically

### Log Rotation

Log rotation prevents:
- Disk space exhaustion
- Performance degradation
- Loss of important log data

## Production Checklist

Before putting this in production, make sure you've done all of these:

- [ ] Firewall configured and enabled (check with `sudo ufw status`)
- [ ] SSH hardened (root login disabled, check `/etc/ssh/sshd_config`)
- [ ] fail2ban installed and running (`sudo fail2ban-client status`)
- [ ] Automatic security updates enabled
- [ ] Log rotation configured (check `/etc/logrotate.d/`)
- [ ] Strong passwords set for all services (database, n8n, JupyterLab)
- [ ] Unnecessary services disabled (check `systemctl list-units`)
- [ ] Tested that you can still access everything after hardening

If you're not sure about any of these, the hardening scripts should handle most of them automatically. But it's good to verify.

### Additional Recommendations

- [ ] Enable auditd for system auditing
- [ ] Configure intrusion detection (IDS)
- [ ] Set up centralized logging
- [ ] Implement backup procedures
- [ ] Regular security scans
- [ ] Access control lists (ACLs)
- [ ] Encrypted communication (TLS/SSL)

## Testing Before/After Hardening

### Why Test?

Testing before and after hardening ensures:
- System functionality is not broken
- All services remain accessible
- Network connectivity is maintained
- Data flow continues to work

### Test Procedure

1. **Before Hardening**:
   ```bash
   ./hosts/shared/test_before_after_hardening.sh
   ```
   - Tests run automatically
   - Results saved to `before_hardening_*.json`

2. **Apply Hardening**:
   - Run hardening scripts on each VM
   - Wait for all VMs to complete

3. **After Hardening**:
   - Return to test script
   - Press Enter to continue
   - Tests run automatically
   - Results compared with baseline

### Expected Results

After hardening, you may see:
- **Same or better connectivity**: All tests should still pass
- **Improved security**: Firewall blocks unauthorized access
- **No functionality loss**: All services remain accessible

### Troubleshooting

If tests fail after hardening:

1. **Check firewall rules**: Ensure necessary ports are allowed
2. **Verify SSH access**: Ensure you can still SSH to VMs
3. **Check service status**: Ensure all services are running
4. **Review logs**: Check system logs for errors

## Best Practices

### Security Principles

1. **Least Privilege** - Only give access to what's needed. If a service doesn't need root, don't run it as root.
2. **Defense in Depth** - Don't rely on one security measure. Firewall + fail2ban + SSH hardening + strong passwords = much better than just one.
3. **Stay Updated** - Security updates matter. The automatic updates help, but check occasionally that they're actually running.
4. **Monitor Logs** - Check fail2ban logs, SSH logs, and system logs regularly. You'll catch issues faster.
5. **Backup Everything** - Especially the database. Test your backups too - untested backups are worse than no backups.

### Maintenance Tips

1. **Review Quarterly** - Security isn't set-and-forget. Review your firewall rules, SSH config, and fail2ban settings every few months.
2. **Document Changes** - If you customize hardening beyond what the scripts do, write it down. Future you will appreciate it.
3. **Test After Changes** - Any time you modify security settings, run the tests again.
4. **Watch the Logs** - Set up log monitoring if possible. Even just checking `journalctl` weekly helps catch issues.

### Compliance Notes

If you're in a regulated environment:
- The 90-day retention policy is a good starting point, but check your specific requirements
- Audit logs are automatically maintained by the system
- Consider encrypting the database if you're storing sensitive data
- Review your organization's security standards and make sure this setup meets them

## Troubleshooting

### Problem: Locked out of VM after hardening

**Solution**:
- Access VM via console (if available)
- Review firewall rules: `ufw status`
- Temporarily disable firewall: `ufw disable` (then reconfigure)

### Problem: Services not accessible after hardening

**Solution**:
- Check firewall rules: `ufw status numbered`
- Allow necessary ports: `ufw allow <port>/tcp`
- Verify service is running: `systemctl status <service>`

### Problem: fail2ban blocking legitimate access

**Solution**:
- Check fail2ban status: `fail2ban-client status`
- Unban IP: `fail2ban-client set <jail> unbanip <ip>`
- Adjust fail2ban configuration if needed

## Additional Resources

- [Ubuntu Security Guide](https://ubuntu.com/security)
- [CIS Benchmarks](https://www.cisecurity.org/benchmark/ubuntu_linux)
- [OWASP Security Guidelines](https://owasp.org/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

