# Running Remote Execution Service Integration Tests

## Prerequisites

### Environment
- **VM04 (Orchestrator)**: Tests are run from VM04
- **VM01, VM02, VM03**: Target machines for testing
- **Ubuntu**: All VMs running Ubuntu
- **Sudo**: Script requires sudo privileges

### Software
- Python 3.10 or newer
- pip3 (Python package manager)
- SSH client
- Network access between VM04 and VM01–VM03

### Configuration
- File `configs/config.yml` with valid VM configuration
- SSH access to VM01, VM02, VM03 (may require initial setup)

## Preparing the Environment

### 1. Verify configuration

Ensure `configs/config.yml` contains correct data:

```yaml
vms:
  vm01:
    ip: "192.168.244.143"
    ssh_user: "thadmin"
    ssh_port: 22
    enabled: true
  vm02:
    ip: "192.168.244.144"
    ssh_user: "thadmin"
    ssh_port: 22
    enabled: true
  vm03:
    ip: "192.168.244.145"
    ssh_user: "thadmin"
    ssh_port: 22
    enabled: true
  vm04:
    ip: "192.168.244.148"
    ssh_user: "thadmin"
    ssh_port: 22
    enabled: true
```

### 2. Check network connectivity

From VM04, verify VM01–VM03 are reachable:

```bash
ping -c 3 192.168.244.143  # VM01
ping -c 3 192.168.244.144  # VM02
ping -c 3 192.168.244.145  # VM03
```

### 3. Prepare the project

Log in to VM04 and go to the project directory:

```bash
cd /home/thadmin/th_timmy
# or
cd /path/to/th_timmy
```

Ensure the directory layout is correct:

```
th_timmy/
├── automation-scripts/
│   └── orchestrators/
│       └── remote_executor/
├── configs/
│   └── config.yml
└── tests/
    └── integration/
        └── orchestrators/
            └── remote_executor/
                └── test_remote_executor_integration.sh
```

## Running the Tests

### Automatic run (recommended)

The script will:
1. Check Python dependencies
2. Install missing packages
3. Check and generate SSH keys for VM01–VM03
4. Run tests on all target VMs

**Run:**

```bash
cd /path/to/th_timmy
sudo ./tests/integration/orchestrators/remote_executor/test_remote_executor_integration.sh
```

**Note**: The script needs sudo for:
- Installing Python packages (if missing)
- Managing SSH keys
- Possibly deploying keys to remote VMs

### Manual SSH key deployment (if automatic fails)

If automatic key deployment fails, do the following.

#### Step 1: Generate keys (if they do not exist)

The script will generate keys by default; you can do it manually:

```python
python3 << EOF
import sys
sys.path.insert(0, '/path/to/th_timmy')

from automation_scripts.orchestrators.remote_executor import KeyManager

key_manager = KeyManager()

# Generate keys for each VM
for vm_id in ['vm01', 'vm02', 'vm03']:
    try:
        private_key, public_key = key_manager.generate_key_pair(key_type='ed25519')
        key_manager.store_key(vm_id, private_key, public_key)
        print(f"Generated key for {vm_id}")
        print(f"Public key: {public_key.decode('utf-8')}")
    except Exception as e:
        print(f"Key for {vm_id} already exists or error: {e}")
EOF
```

#### Step 2: Retrieve public keys

```python
python3 << EOF
import sys
sys.path.insert(0, '/path/to/th_timmy')

from automation_scripts.orchestrators.remote_executor import KeyManager

key_manager = KeyManager()

for vm_id in ['vm01', 'vm02', 'vm03']:
    public_key = key_manager.get_public_key(vm_id)
    print(f"\n=== Public key for {vm_id} ===")
    print(public_key.decode('utf-8'))
EOF
```

#### Step 3: Add keys to authorized_keys on remote VMs

For each VM (VM01, VM02, VM03):

```bash
# Log in to the remote VM (e.g. VM01)
ssh thadmin@192.168.244.143

# Append the public key to authorized_keys
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "PASTE_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Or use `ssh-copy-id` (if you have password access):

```bash
# From VM04
ssh-copy-id -i ~/.ssh/th_timmy_keys.pub thadmin@192.168.244.143
```

## Tests performed by the script

The script runs the following tests for each VM (VM01, VM02, VM03):

1. **Execute simple command** – run a simple command (`echo 'hello'`)
2. **Upload file** – upload a file to the remote VM
3. **Download file** – download a file from the remote VM
4. **File checksum verification** – SHA256 checksum verification
5. **Interactive command blocking** – blocking of interactive commands

Global tests:
6. **Invalid VM ID rejection** – rejection of invalid VM IDs

## Interpreting results

### Success

```
[INFO] Test Summary:
[INFO]   Passed: 16
[INFO]   Failed: 0
[INFO] All tests passed!
```

### Failures

If tests fail, check:

1. **Connection errors**:
   - Network: `ping <vm_ip>`
   - SSH: `ssh thadmin@<vm_ip>`
   - Firewall/iptables

2. **Authentication errors**:
   - Public key present in `~/.ssh/authorized_keys` on the remote VM
   - Permissions: `chmod 600 ~/.ssh/authorized_keys`
   - Directory: `chmod 700 ~/.ssh`

3. **Key not found**:
   - Re-run the script to regenerate missing keys
   - Confirm KeyManager can read the keys

4. **Permission errors**:
   - Run the script with sudo
   - Check project directory permissions

## Collecting test output

### Test logs

The script prints results to stdout. To save to a file:

```bash
sudo ./tests/integration/orchestrators/remote_executor/test_remote_executor_integration.sh 2>&1 | tee test_results.log
```

### Detailed logs

For more detail, change the Python log level or run bash with `-x`:

```bash
sudo bash -x ./tests/integration/orchestrators/remote_executor/test_remote_executor_integration.sh 2>&1 | tee detailed_test_results.log
```

## Troubleshooting

### "config.yml not found"

**Solution**: Ensure you are in the project directory and `configs/config.yml` exists:

```bash
cd /path/to/th_timmy
ls -la configs/config.yml
```

### "Python 3 is not installed"

**Solution**: Install Python 3.10+:

```bash
sudo apt update
sudo apt install python3 python3-pip
```

### "Key not found for vm01"

**Solution**: The script generates keys automatically. If it still fails:

1. Check permissions on `~/.ssh/th_timmy_keys.encrypted`
2. Check environment variable `TH_TIMMY_KEY_ENCRYPTION_KEY`
3. Use manual key generation (see above)

### "SSHConnectionError: Connection failed"

**Solution**:
1. Reachability: `ping <vm_ip>`
2. SSH: `ssh thadmin@<vm_ip>`
3. Public key in `authorized_keys` on the remote VM
4. Firewall/iptables

### "SSHAuthenticationError: Authentication failed"

**Solution**:
1. Public key added to `~/.ssh/authorized_keys` on the remote VM
2. Permissions: `chmod 600 ~/.ssh/authorized_keys`
3. SSH user matches `config.yml`
4. Generate a new key and deploy again

### "Permission denied" when running the script

**Solution**: Run with sudo:

```bash
sudo ./tests/integration/orchestrators/remote_executor/test_remote_executor_integration.sh
```

## Security

### SSH keys

- Keys are stored encrypted in `~/.ssh/th_timmy_keys.encrypted`
- Encryption key in `~/.ssh/th_timmy_encryption_key` (permissions 600)
- Do **not** commit keys to the Git repository

### Privileges

- The script needs sudo only for:
  - Installing Python packages (if missing)
  - Deploying keys
- Tests themselves run with normal user privileges

## Support

If you run into issues:
1. Review test logs
2. Use the “Troubleshooting” section above
3. Report in a ticket with:
   - Full script output
   - VM configuration (no secrets)
   - Python and OS versions

## Final notes

- Tests are intended to run on VM04 (orchestrator)
- They automatically check and generate SSH keys
- All tests are idempotent (safe to run repeatedly)
- Tests do not permanently change the system (they use `/tmp` for test files)
