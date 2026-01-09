# VM-04: Orchestrator - Installation

Installation and verification scripts for VM-04 (Orchestrator - n8n in Docker).

## Files

- `install_vm04.sh` - Installation script for all required tools
- `health_check.sh` - Installation verification script
- `requirements.txt` - List of Python packages required for VM-04
- `docker-compose.yml` - n8n configuration in Docker container
- `config.example.yml` - Example configuration file
- `config.yml` - Configuration file (to be created by user)
- `.env` - Environment variables file for docker-compose (created automatically)

## Requirements

- Ubuntu Server 22.04 LTS
- Root privileges (sudo)
- Internet access
- **IMPORTANT**: Configuration file `config.yml` with n8n password set

## Preparation

### 1. Create configuration file

**REQUIRED** before running installation:

```bash
cd /path/to/timmy_developer/th_timmy/hosts/vm04-orchestrator
cp config.example.yml config.yml
nano config.yml
```

**Must fill in:**
- `basic_auth_password` - strong password for n8n user

## Installation

### Running

```bash
cd /path/to/timmy_developer/th_timmy/hosts/vm04-orchestrator
sudo ./install_vm04.sh [PROJECT_ROOT] [CONFIG_FILE]
```

**Example:**
```bash
# Using default PROJECT_ROOT and config.yml
sudo ./install_vm04.sh

# Or with custom path
sudo ./install_vm04.sh $HOME/th_timmy config.yml
```

### What does the script install?

1. **Basic system tools**: git, curl, wget, vim, nano, etc.
2. **Docker Engine** from official Docker repository:
   - docker-ce, docker-ce-cli
   - containerd.io
   - docker-buildx-plugin
   - docker-compose-plugin
3. **Python 3.10+** with pip and venv
4. **System libraries**: libssl-dev, libffi-dev
5. **Python packages** from `requirements.txt`:
   - pyyaml, python-dotenv, requests
   - loguru
   - docker (Python SDK)
6. **n8n configuration**:
   - docker-compose.yml
   - .env with credentials
   - Automatic startup (if auto_start=true)
7. **Firewall configuration** (port 5678)

### Post-installation structure

```
$HOME/th_timmy/
├── hosts/
│   └── vm04-orchestrator/
│       ├── install_vm04.sh
│       ├── health_check.sh
│       ├── requirements.txt
│       ├── docker-compose.yml
│       ├── config.example.yml
│       ├── config.yml (created by user)
│       └── .env (created automatically)
└── venv/                    # Virtual environment
```

## Installation Verification

After installation, run the verification script:

```bash
./health_check.sh [PROJECT_ROOT] [CONFIG_FILE]
```

**Example:**
```bash
./health_check.sh $HOME/th_timmy config.yml
```

### What does health_check verify?

- ✅ Operating system version (Ubuntu 22.04)
- ✅ Installed system tools
- ✅ Docker and Docker Compose (version, service status)
- ✅ Python 3.10+
- ✅ Virtual environment
- ✅ All required Python packages
- ✅ docker-compose.yml and .env
- ✅ n8n Docker container (status)
- ✅ Port 5678 and firewall
- ✅ Locale configuration

## Managing n8n

### Starting n8n

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose up -d
```

### Stopping n8n

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose down
```

### Restarting n8n

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose restart
```

### Checking status

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose ps
```

### n8n logs

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose logs -f n8n
```

### Accessing n8n

Open in browser:
```
http://VM04_IP:5678
```

Login using:
- **Username**: value from `config.yml` → `basic_auth_user`
- **Password**: value from `config.yml` → `basic_auth_password`

## Troubleshooting

### Problem: "Cannot connect to the Docker daemon"

**Solution:**
1. Log out and log back in (after adding to docker group)
2. Or use `sudo` before docker commands
3. Check status: `sudo systemctl status docker`

### Problem: "n8n container won't start"

**Solution:**
1. Check logs: `cd $VM04_DIR && docker compose logs n8n`
2. Check if port 5678 is free: `netstat -tlnp | grep 5678`
3. Check if .env exists and has correct values
4. Check docker-compose.yml: `docker compose config`

### Problem: "n8n password doesn't work"

**Solution:**
1. Check `.env` file in `$VM04_DIR/.env`
2. Make sure password in `.env` matches password in `config.yml`
3. Restart container: `docker compose restart n8n`

### Problem: "Permission denied" with docker commands

**Solution:**
1. Check if user is in docker group: `groups`
2. If not, add: `sudo usermod -aG docker $USER`
3. Log out and log back in

### Problem: "Port 5678 already in use"

**Solution:**
1. Check what's using the port: `sudo lsof -i :5678`
2. Stop other services using this port
3. Or change port in `config.yml` and `docker-compose.yml`

## Documentation

Detailed requirements can be found in:
- `../../INPUT/VM04_TOOLS_REQUIREMENTS.md`

## Security

⚠️ **IMPORTANT:**
- Never commit `config.yml` or `.env` files to repository (they're in .gitignore)
- Use strong passwords for n8n
- Limit firewall access only to trusted IPs
- Regularly update Docker and container images
- Consider using HTTPS in production (requires additional configuration)

## Updating n8n

To update n8n to the latest version:

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose pull
docker compose up -d
```
