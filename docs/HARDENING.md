# Hardening Guide

This guide explains the security hardening procedures for the Threat Hunting Lab VMs.

## Overview

Hardening is the process of securing systems by reducing their attack surface. This guide covers:

- Common hardening functions
- VM-specific hardening procedures
- SSH key management (Remote Execution, Step 0.1)
- Repository Sync and secret scanning (Step 0.2)
- Configuration Management and backups (Step 0.3)
- Testing before and after hardening
- Best practices

## SSH key management (Remote Execution, Step 0.1)

The Remote Execution Service on VM04 uses SSH keys to run commands and transfer files on VM01–VM04. The following applies to Step 0.1.

### Key storage

- **Path:** Keys are stored in `~/.ssh/th_timmy_keys` by default. This is configurable via `remote_execution.key_storage_path` in `configs/config.yml`.
- **Generation and deployment:** Use `hosts/vm04-orchestrator/setup_ssh_keys.sh` to generate keys and deploy them to VM01–VM03 (and VM04 if needed). The script enforces key-only auth and updates `~/.ssh/config`.

### Requirements

- **Key-only authentication:** Password-based SSH login must be disabled for Remote Execution targets. Use only key-based auth; no passwords in config or scripts.
- **Strong algorithms:** Use at least 2048-bit RSA, 256-bit ECDSA, or Ed25519. Weak algorithms (e.g. MD5, SHA1, DES, RC4) must be disabled.
- **Host key verification:** Server host keys must be verified; do not disable StrictHostKeyChecking for production.

### Key rotation

- **Target:** Rotate SSH keys every **90 days** (aligned with `remote_execution.key_rotation_days` in config where supported). Document the procedure in runbooks or operational docs; automate where possible.
- **Process:** Regenerate keys, deploy via `setup_ssh_keys.sh` (or equivalent), update any automation that references key paths, then revoke old keys.

### Security rules

- **No keys in repository or logs:** Never commit private keys, key material, or passwords to the repository. Do not log key paths, key names, or key content. Use `.gitignore` for any local key directories if they are under the project tree.
- **Non-interactive commands only:** Remote Execution allows only non-interactive commands: use timeouts for all operations and do not feed stdin. Interactive commands (e.g. `sudo` prompting for a password) must be rejected or documented as out-of-scope. See [automation_scripts/orchestrators/remote_executor/README.md](../automation_scripts/orchestrators/remote_executor/README.md) (Troubleshooting / Security) for details.

## Repository Sync and secret scanning (Step 0.2)

Before syncing the repository from VM04 to VM01–VM03, the Repository Sync Service runs a secret scan (e.g. gitleaks). If secrets are detected, sync is blocked and an alert is generated; secret content is never logged. Configure `repository.secret_scanning` in `configs/config.yml` (enabled, tool, config_path, block_on_secrets). Branch protection for main (e.g. require PR, reviews, tests, no direct push) is configured in the hosting system (GitHub/GitLab); it is documented in CONFIGURATION and in [automation_scripts/orchestrators/repo_sync/README.md](../automation_scripts/orchestrators/repo_sync/README.md). Recommend integrating gitleaks in CI (e.g. on push/PR).

## Configuration Management and backups (Step 0.3)

Configuration Management backs up config files in encrypted form (e.g. AES) with configurable retention (e.g. 90 days). Backup keys or passphrases must not be stored in the repository; use environment variables (e.g. TH_TIMMY_CONFIG_BACKUP_PASSPHRASE) or a secure key path. See [automation_scripts/orchestrators/config_manager/README.md](../automation_scripts/orchestrators/config_manager/README.md) and the `config_management` section in `configs/config.example.yml`.

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

Before applying hardening, run tests to establish a baseline:

```bash
cd /path/to/th_timmy
./hosts/shared/test_before_after_hardening.sh
```

This will:
1. Run connection and data flow tests
2. Save results to `test_results/before_hardening_*.json`
3. Wait for you to apply hardening
4. Run tests after hardening
5. Compare results

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

## Production Requirements

### Minimum Hardening Checklist

- [ ] Firewall configured and enabled
- [ ] SSH hardened (root login disabled)
- [ ] fail2ban installed and configured
- [ ] Automatic security updates enabled
- [ ] Log rotation configured
- [ ] Strong passwords set for all services
- [ ] Unnecessary services disabled
- [ ] Regular security updates applied

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

### Security

1. **Principle of Least Privilege**: Grant minimum necessary access
2. **Defense in Depth**: Multiple layers of security
3. **Regular Updates**: Keep systems updated
4. **Monitoring**: Monitor for security events
5. **Backup**: Regular backups of critical data

### Maintenance

1. **Regular Reviews**: Review security configuration regularly
2. **Documentation**: Document all hardening changes
3. **Testing**: Test after any configuration changes
4. **Monitoring**: Monitor system logs for issues
5. **Updates**: Apply security updates promptly

### Compliance

1. **Data Retention**: Follow 90-day retention policy
2. **Access Control**: Implement proper access controls
3. **Audit Logs**: Maintain audit logs
4. **Encryption**: Use encryption for sensitive data
5. **Compliance**: Follow relevant security standards

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

