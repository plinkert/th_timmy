# Comprehensive Deployment Guide - Threat Hunting Automation Lab

**Version**: 1.0  
**Date**: 2025-01-12

> **Note:** This guide provides comprehensive step-by-step instructions for system deployment. For experienced system administrators, the [Quick Start Guide](QUICK_START.md) offers a faster installation path.

---

## Table of Contents

1. [Introduction](#introduction)
2. [What is this system?](#what-is-this-system)
3. [What do you need?](#what-do-you-need)
4. [Environment preparation](#environment-preparation)
5. [Step-by-step installation](#step-by-step-installation)
6. [System configuration](#system-configuration)
7. [Installation verification](#installation-verification)
8. [Available tools and their usage](#available-tools-and-their-usage)
9. [Troubleshooting](#troubleshooting)
10. [Next steps](#next-steps)

---

## Introduction

This guide provides comprehensive step-by-step instructions for deploying and configuring the Threat Hunting Automation Lab system. Each step is documented in detail to ensure successful deployment.

---

## What is this system?

**Threat Hunting Automation Lab** is a system that helps security teams automatically search for threats in IT infrastructure. The system consists of 4 virtual machines (VMs) that work together:

1. **VM-01 (Ingest/Parser)** - Collects and processes data from various sources
2. **VM-02 (Database)** - Stores data in a database
3. **VM-03 (Analysis/Jupyter)** - Enables data analysis and report creation
4. **VM-04 (Orchestrator)** - Central management of the entire system

**Usage example:**
The system enables automated threat detection by processing security logs. For example, to check for suspicious activities in your network, the system:
- Automatically collects logs from various systems (firewall, servers, workstations)
- Analyzes them for known threat patterns (e.g., intrusion attempts, malware)
- Generates readable reports with results
- Everything managed from one place (dashboard in browser)

---

## What do you need?

### Hardware requirements

You need access to **4 virtual machines (VMs)** with the following specifications:

| VM | Processor | RAM | Disk | Description |
|---|---|---|---|---|
| VM-01 | 2 cores | 4 GB | 20 GB | Data collection |
| VM-02 | 2 cores | 4 GB | 50 GB | Database (more space for data) |
| VM-03 | 4 cores | 8 GB | 30 GB | Analysis (more computing power) |
| VM-04 | 2 cores | 4 GB | 20 GB | Management |

**Note:** If you don't have access to virtual machines, you can create them in the cloud (e.g., AWS, Azure, Google Cloud) or on your own server. Most cloud providers offer free trial periods, so you can test the system without costs.

### Software requirements

Each virtual machine must have installed:

- **Ubuntu Server 22.04 LTS** (or newer version)
- **Internet access** (for downloading software)
- **SSH access** (for remote management)

### Network requirements

- All 4 VMs must be on the same network (can communicate with each other)
- You need to know the IP address of each machine
- Ports that must be open:
  - **22** - SSH (remote access)
  - **5432** - PostgreSQL (database)
  - **8888** - JupyterLab (analysis)
  - **5678** - n8n (management)

### Access requirements

- **User account** on each machine with administrator privileges (sudo)
- **Passwords** or **SSH keys** to log into machines
- **Familiarity** with terminal/command line interface (all commands are documented in this guide)

---

## Environment preparation

### Step 1: Check access to virtual machines

Before you start, make sure that:

1. **You have access to all 4 virtual machines**
   - You can log into them via SSH
   - You have administrator privileges (sudo)

2. **You know the IP addresses of each machine**
   - Write them down in a safe place
   - You'll need them during configuration

3. **You have internet access** from each machine
   - The system will download software from the internet

### Step 2: Prepare a notebook

Write down the following information (you'll need it):

```
VM-01 IP: ________________
VM-02 IP: ________________
VM-03 IP: ________________
VM-04 IP: ________________

Database password: ________________
n8n password: ________________
JupyterLab password: ________________
```

**Important:** Use strong passwords! Don't use simple passwords like "123456" or "password".

### Step 3: Check network connectivity

From each machine, check if you can connect to others:

```bash
# On VM-01, check connection to VM-02
ping <VM-02_IP>

# You should see responses (pings)
# If you don't see responses, check network settings
```

**How to do it:**
1. Log into VM-01 via SSH
2. Type: `ping <VM-02_IP_address>`
3. Press Enter
4. If you see "64 bytes from..." - connection works
5. Press Ctrl+C to stop

Repeat this for all machine combinations.

---

## Step-by-step installation

### Stage 1: Download and prepare code

#### Step 1.1: Log into VM-04

VM-04 will be the management machine, so we start with it.

```bash
# Log in via SSH (replace <VM-04_IP> with actual IP address)
ssh your_username@<VM-04_IP>
```

**SSH access methods:**
- On Windows: Use **PuTTY** or **Windows Terminal**
- On Linux/Mac: Use terminal with `ssh` command
- Authentication: Username and password, or SSH key

#### Step 1.2: Download project code

After logging into VM-04, execute:

```bash
# Go to home directory
cd ~

# Download project (replace <repository-url> with actual repository address)
git clone <repository-url> th_timmy

# Go to project directory
cd th_timmy
```

**Alternative download method (without Git):**
- Download project as ZIP file
- Extract to home directory
- Rename directory to `th_timmy`

#### Step 1.3: Copy project to remaining machines

You need the same code on all machines. Recommended method:

```bash
# From VM-04, copy project to remaining machines
# (replace <VM-01_IP>, <VM-02_IP>, <VM-03_IP> with actual addresses)

# Copy to VM-01
scp -r ~/th_timmy your_username@<VM-01_IP>:~/

# Copy to VM-02
scp -r ~/th_timmy your_username@<VM-02_IP>:~/

# Copy to VM-03
scp -r ~/th_timmy your_username@<VM-03_IP>:~/
```

**Alternatively:** You can download project separately on each machine (repeat Step 1.2 on each machine).

### Stage 2: System configuration

#### Step 2.1: Create configuration file

On VM-04 (or on machine from which you manage):

```bash
# Go to project directory
cd ~/th_timmy

# Copy example configuration file
cp configs/config.example.yml configs/config.yml
```

#### Step 2.2: Edit configuration file

Open file `configs/config.yml` in text editor:

```bash
# Use nano (text editor)
nano configs/config.yml
```

**How to use nano:**
- To edit text, just start typing
- To save: Ctrl+O, then Enter
- To exit: Ctrl+X

**What you need to change in file:**

Find `vms:` section and change IP addresses:

```yaml
vms:
  vm01:
    ip: "10.0.0.10"  # CHANGE to actual VM-01 IP address
  vm02:
    ip: "10.0.0.11"  # CHANGE to actual VM-02 IP address
  vm03:
    ip: "10.0.0.12"  # CHANGE to actual VM-03 IP address
  vm04:
    ip: "10.0.0.13"  # CHANGE to actual VM-04 IP address
```

Find `network:` section and change network settings:

```yaml
network:
  subnet: "10.0.0.0/24"  # CHANGE to your network (e.g., "192.168.1.0/24")
  gateway: "10.0.0.1"     # CHANGE to network gateway
```

**How to find network information (step by step):**

1. Log into any machine via SSH
2. In terminal type: `ip addr show`
3. You'll see something like:
   ```
   inet 192.168.1.10/24
   ```
   - IP address is: `192.168.1.10`
   - Subnet is: `192.168.1.0/24` (first 3 numbers + ".0/24")
4. To find gateway (network gateway), type: `ip route show`
5. You'll see something like:
   ```
   default via 192.168.1.1
   ```
   - Gateway is: `192.168.1.1` (often ends with .1)

Save file (Ctrl+O, Enter) and close (Ctrl+X).

### Stage 3: Installation on each machine

**IMPORTANT:** Install machines in this order:
1. First VM-02 (database) - other machines depend on it
2. Then VM-01 (data collection)
3. Then VM-03 (analysis)
4. Finally VM-04 (management)

#### VM-02 Installation (Database)

**Step 3.1: Log into VM-02**

```bash
ssh your_username@<VM-02_IP>
```

**Step 3.2: Go to project directory**

```bash
cd ~/th_timmy/hosts/vm02-database
```

**Step 3.3: Create database configuration file**

```bash
# Copy example file
cp config.example.yml config.yml

# Open in editor
nano config.yml
```

**What you need to set:**

1. **`database_password`** - Strong password for database (store securely)
   ```yaml
   database_password: "YourStrongPassword123!"
   ```

2. **`allowed_ips`** - IP addresses of machines that can connect to database
   ```yaml
   allowed_ips:
     - "10.0.0.10"  # VM-01 IP
     - "10.0.0.12"  # VM-03 IP
   ```

Save file (Ctrl+O, Enter) and close (Ctrl+X).

**Step 3.4: Run installation**

```bash
# Run installation script (you need administrator privileges)
sudo ./install_vm02.sh
```

**What happens during installation:**
- Installs PostgreSQL (database)
- Creates database and user
- Configures network access
- Installs helper tools

**Installation duration:** 10-15 minutes. Keep the terminal session open during installation. Wait for the "Installation completed successfully" message or similar confirmation.

**Step 3.5: Check if installation succeeded**

```bash
# Run verification script
./health_check.sh
```

**What you should see:**
- ✅ All tests should be marked as "PASS" or "OK"
- If you see errors, write them down and go to "Troubleshooting" section

#### VM-01 Installation (Data collection)

**Step 3.6: Log into VM-01**

```bash
ssh your_username@<VM-01_IP>
```

**Step 3.7: Go to project directory**

```bash
cd ~/th_timmy/hosts/vm01-ingest
```

**Step 3.8: Run installation**

```bash
sudo ./install_vm01.sh
```

**What happens during installation:**
- Installs Python and development tools
- Installs data processing libraries
- Configures virtual environment

**Step 3.9: Check installation**

```bash
./health_check.sh
```

#### VM-03 Installation (Analysis)

**Step 3.10: Log into VM-03**

```bash
ssh your_username@<VM-03_IP>
```

**Step 3.11: Go to project directory**

```bash
cd ~/th_timmy/hosts/vm03-analysis
```

**Step 3.12: (Optional) Create JupyterLab configuration file**

```bash
# Copy example file
cp config.example.yml config.yml

# Open in editor
nano config.yml
```

**What you can set:**
- `jupyter_ip` - IP address where JupyterLab will be available (leave "0.0.0.0" for all interfaces)
- `jupyter_port` - Port (default 8888)
- `jupyter_token` - Access token (leave empty to generate automatically)
- `jupyter_password` - Password (optional)

Save file (Ctrl+O, Enter) and close (Ctrl+X).

**Step 3.13: Run installation**

```bash
sudo ./install_vm03.sh
```

**What happens during installation:**
- Installs Python and JupyterLab
- Installs data analysis and machine learning libraries
- Configures JupyterLab

**Step 3.14: Check installation**

```bash
./health_check.sh
```

**Step 3.15: Start JupyterLab**

```bash
# Activate virtual environment
source ~/th_timmy/venv/bin/activate

# Start JupyterLab
jupyter lab --ip=0.0.0.0 --port=8888
```

**Save the token that appears!** You'll need it for logging in. Token looks something like: `abc123def456ghi789...` - copy entire token and save in safe place (e.g., in notebook).

**Example output:**
```
[I 2025-01-12 10:00:00.000 LabApp] http://VM-03_IP:8888/lab?token=abc123def456...
```

**To stop JupyterLab:** Press Ctrl+C in terminal.

#### VM-04 Installation (Management)

**Step 3.16: Log into VM-04**

```bash
ssh your_username@<VM-04_IP>
```

**Step 3.17: Go to project directory**

```bash
cd ~/th_timmy/hosts/vm04-orchestrator
```

**Step 3.18: Create n8n configuration file**

```bash
# Copy example file
cp config.example.yml config.yml

# Open in editor
nano config.yml
```

**What you need to set:**

1. **`basic_auth_user`** - Username for logging into n8n
   ```yaml
   basic_auth_user: "admin"
   ```

2. **`basic_auth_password`** - Password for logging into n8n (store securely)
   ```yaml
   basic_auth_password: "YourStrongPassword123!"
   ```

Save file (Ctrl+O, Enter) and close (Ctrl+X).

**Step 3.19: Run installation**

```bash
sudo ./install_vm04.sh
```

**What happens during installation:**
- Installs Docker
- Downloads and runs n8n in Docker container
- Configures network access

**Step 3.20: Check installation**

```bash
./health_check.sh
```

**Step 3.21: Check if n8n is running**

```bash
# Check Docker container status
docker ps

# You should see "n8n" container in "Up" state
```

**Step 3.22: Open n8n in browser**

Open browser and go to:
```
http://<VM-04_IP>:5678
```

Log in using:
- **Username:** The one you set in `config.yml`
- **Password:** The one you set in `config.yml`

---

## System configuration

### n8n workflows configuration

After logging into n8n, you need to import ready workflows.

#### Step 4.1: Import Management Dashboard

1. In n8n, click **"Workflows"** in left menu
2. Click **"Import from File"** (or import icon)
3. Go to directory: `~/th_timmy/hosts/vm04-orchestrator/n8n-workflows/`
4. Select file: `management-dashboard.json`
5. Click **"Import"**

**Repeat this for remaining workflows:**
- `testing-management.json` - Test management
- `deployment-management.json` - Deployment management
- `hardening-management.json` - Security management
- `playbook-manager.json` - Playbook management
- `hunt-selection-form.json` - Hunt selection form

#### Step 4.2: Activate workflows

1. After importing, each workflow will be visible on list
2. Click on workflow to open it
3. Click **"Active"** button (in top right corner) to activate it
4. Workflow is now active and will run automatically

---

## Installation verification

### Connection tests

On any machine (preferably VM-04), run connection tests:

```bash
cd ~/th_timmy
./hosts/shared/test_connections.sh
```

**What you should see:**
- ✅ All ping tests should be "PASS"
- ✅ Port tests should be "PASS"
- ⚠️ SSH tests may show "WARN" (this is normal if you don't have SSH keys configured)

### Data flow test

```bash
# Set database password as environment variable
export POSTGRES_PASSWORD="YourDatabasePassword"

# Run data flow test
./hosts/shared/test_data_flow.sh
```

**What you should see:**
- ✅ Database write tests should be "PASS"
- ✅ Database read tests should be "PASS"
- ✅ n8n tests should be "PASS"

---

## Available tools and their usage

The system contains many tools for management and monitoring. Below you'll find detailed description of each tool.

### 1. Management Dashboard (n8n)

**What it is:** Main system management panel, available through browser.

**Where it is:** http://<VM-04_IP>:5678

**What it's for:**
- Monitoring status of all machines
- Displaying system metrics (CPU, RAM, disk)
- Configuration management
- Repository synchronization
- Quick actions (health checks, tests)

**How to use:**

1. **Log into n8n:**
   - Open browser
   - Go to: `http://<VM-04_IP>:5678`
   - Log in using username and password from `config.yml`

2. **Open Management Dashboard:**
   - In n8n, find workflow "Management Dashboard"
   - Click on it to open
   - Click "Active" button to activate it (if not active)

3. **Access dashboard:**
   - Dashboard is available through webhook
   - In workflow find node "Dashboard UI"
   - Click on it and copy webhook URL
   - Open this URL in browser

4. **Using dashboard:**
   - **System Overview:** You see status of all 4 machines
     - 🟢 Green = machine works correctly
     - 🟡 Yellow = machine has problems but works
     - 🔴 Red = machine doesn't work
   - **Metrics:** You see CPU, RAM and disk usage for each machine
   - **Repository synchronization:** Click "Sync Repository" button to synchronize code on all machines
   - **Health Checks:** Click "Refresh Status" button to check status of all machines

**Example usage:**

```
1. Open dashboard in browser
2. Check machine status - all should be green
3. If any machine is yellow or red:
   - Click on it to see details
   - Check metrics - there may be problem with memory or disk
   - Click "Run Health Check" to run detailed check
```

### 2. Testing Management Interface

**What it is:** Interface for managing system tests.

**Where it is:** In n8n, workflow "Testing Management"

**What it's for:**
- Running connection tests between machines
- Testing data flow
- Checking machine health
- Reviewing test results

**How to use:**

1. **Open Testing Management:**
   - In n8n, find workflow "Testing Management"
   - Click on it
   - Make sure it's active

2. **Access interface:**
   - Find node "Testing Dashboard"
   - Copy webhook URL
   - Open in browser

3. **Running tests:**
   - **Connection Tests:** Tests connections between machines
     - Click "Run Connection Tests"
     - Wait for results (may take 1-2 minutes)
   - **Data Flow Tests:** Tests data flow through system
     - Click "Run Data Flow Tests"
     - Make sure database password is set
   - **Health Checks:** Checks health of all machines
     - Click "Run Health Checks"
     - You'll see detailed information about each machine

**When to use:**
- After system installation (verification that everything works)
- After configuration changes
- When something doesn't work (diagnostics)
- Regularly (e.g., once a week) as check

### 3. Deployment Management Interface

**What it is:** Interface for managing deployments and installations.

**Where it is:** In n8n, workflow "Deployment Management"

**What it's for:**
- Checking installation status on machines
- Running installations remotely
- Reviewing installation logs
- Deployment verification

**How to use:**

1. **Open Deployment Management:**
   - In n8n, find workflow "Deployment Management"
   - Click on it
   - Make sure it's active

2. **Access interface:**
   - Find node "Deployment Dashboard"
   - Copy webhook URL
   - Open in browser

3. **Check installation status:**
   - Click "Get Installation Status"
   - You'll see installation status for each machine:
     - ✅ Installed - machine is installed
     - ❌ Not Installed - machine is not installed
     - ⚠️ Unknown - cannot check status

4. **Run installation:**
   - Select machine from list
   - Click "Run Installation"
   - Provide parameters (project path, etc.)
   - Click "Start"
   - Monitor progress in logs

**When to use:**
- During first system installation
- When you need to reinstall machine
- When updating software
- When checking if everything is installed

### 4. Hardening Management Interface

**What it is:** Interface for managing machine security.

**Where it is:** In n8n, workflow "Hardening Management"

**What it's for:**
- Checking security status of machines
- Running security process (hardening)
- Comparing before/after security
- Reviewing security reports

**How to use:**

1. **Open Hardening Management:**
   - In n8n, find workflow "Hardening Management"
   - Click on it
   - Make sure it's active

2. **Access interface:**
   - Find node "Hardening Dashboard"
   - Copy webhook URL
   - Open in browser

3. **Check security status:**
   - Click "Get Hardening Status"
   - You'll see status for each machine:
     - ✅ Hardened - machine is secured
     - ⚠️ Partial - machine is partially secured
     - ❌ Not Hardened - machine is not secured

4. **Run hardening:**
   - **IMPORTANT:** Before running, run tests to have reference point
   - Select machine
   - Click "Run Hardening"
   - Select option "Capture Before State" (save state before)
   - Click "Start"
   - Wait for completion (may take 5-10 minutes)

5. **Compare before/after:**
   - After hardening completes, you can compare results
   - Click "Compare Before/After"
   - Select hardening ID
   - You'll see differences

**When to use:**
- After system installation (secure before use)
- When you want to increase security
- When you need to meet security requirements
- Regularly (e.g., once a quarter) as check

**WARNING:** After hardening, some ports may be blocked. Make sure you have SSH access to machines!

### 5. Playbook Manager

**What it is:** Interface for managing playbooks (threat analysis scripts).

**Where it is:** In n8n, workflow "Playbook Manager"

**What it's for:**
- Browsing available playbooks
- Creating new playbooks
- Editing existing playbooks
- Validating playbooks
- Testing playbooks

**How to use:**

1. **Open Playbook Manager:**
   - In n8n, find workflow "Playbook Manager"
   - Click on it
   - Make sure it's active

2. **Access interface:**
   - Find node "Playbook Dashboard"
   - Copy webhook URL
   - Open in browser

3. **Browse playbooks:**
   - Click "List Playbooks"
   - You'll see list of all available playbooks
   - Each playbook has:
     - Name
     - Description
     - Status (valid/invalid)
     - Last modification date

4. **Create new playbook:**
   - Click "Create New Playbook"
   - Fill form:
     - Playbook name
     - Description
     - MITRE ATT&CK Technique ID (e.g., T1566)
     - Queries for different tools (Splunk, Sentinel, etc.)
   - Click "Create"
   - System will automatically validate playbook

5. **Edit playbook:**
   - Select playbook from list
   - Click "Edit"
   - Change needed fields
   - Click "Save"
   - System will validate changes

**When to use:**
- When you want to create new playbook for specific threat analysis
- When you need to update existing playbook
- When you want to check if playbook is correct
- When you want to see what playbooks are available

### 6. Hunt Selection Form

**What it is:** Form for selecting hunts (threat hunts) and tools.

**Where it is:** In n8n, workflow "Hunt Selection Form"

**What it's for:**
- Selecting MITRE ATT&CK techniques for analysis
- Selecting available tools (Splunk, Sentinel, etc.)
- Generating queries for selected hunts
- Running analysis

**How to use:**

1. **Open Hunt Selection Form:**
   - In n8n, find workflow "Hunt Selection Form"
   - Click on it
   - Make sure it's active

2. **Access form:**
   - Find node "Hunt Selection Form"
   - Copy webhook URL
   - Open in browser

3. **Fill form:**
   - **Select MITRE ATT&CK techniques:**
     - Check boxes next to techniques you want to analyze
     - You can select multiple techniques
   - **Select available tools:**
     - Check tools you have available (Splunk, Sentinel, Defender, etc.)
   - **Select ingest mode:**
     - Manual - manual data upload
     - API - automatic retrieval via API
   - Click "Generate Queries"

4. **Generate queries:**
   - System will automatically generate queries for selected techniques and tools
   - You'll see list of queries
   - You can copy them and use in your tools

5. **Run analysis:**
   - After executing queries in your tools, upload results
   - Click "Start Analysis"
   - System will automatically process data and generate report

**When to use:**
- When you want to conduct threat hunting
- When you want to check specific MITRE ATT&CK techniques
- When you need queries for your SIEM/EDR tools
- When you want to automate analysis process

### 7. JupyterLab (Data analysis)

**What it is:** Interactive environment for data analysis and report creation.

**Where it is:** http://<VM-03_IP>:8888

**What it's for:**
- Data analysis from database
- Creating visualizations
- Writing and executing Python scripts
- Creating reports
- Experimenting with data

**How to use:**

1. **Start JupyterLab:**
   - Log into VM-03 via SSH
   - Run:
     ```bash
     cd ~/th_timmy
     source venv/bin/activate
     jupyter lab --ip=0.0.0.0 --port=8888
     ```
   - Copy token that appears

2. **Open JupyterLab in browser:**
   - Open browser
   - Go to: `http://<VM-03_IP>:8888`
   - Paste token when prompted

3. **Basic operations:**
   - **Create new notebook:**
     - Click "New" → "Python 3"
     - New notebook will be created
   - **Connect to database:**
     ```python
     import psycopg2
     
     conn = psycopg2.connect(
         host="<VM-02_IP>",
         port=5432,
         database="threat_hunting",
         user="threat_hunter",
         password="YourPassword"
     )
     ```
   - **Execute query:**
     ```python
     import pandas as pd
     
     query = "SELECT * FROM normalized_logs LIMIT 100"
     df = pd.read_sql(query, conn)
     df.head()
     ```

**When to use:**
- When you want to analyze data manually
- When you want to create own visualizations
- When you want to experiment with data
- When you want to write own analysis scripts

### 8. Command line tools

The system also contains tools you can use from command line (terminal).

#### 8.1. Health Check

**What it is:** Script checking machine health.

**Where it is:** On each machine: `~/th_timmy/hosts/vmXX-*/health_check.sh`

**How to use:**

```bash
# On any machine
cd ~/th_timmy/hosts/vm01-ingest  # (or vm02, vm03, vm04)
./health_check.sh
```

**What it checks:**
- If all required programs are installed
- If services are running (PostgreSQL, JupyterLab, Docker)
- If configuration is correct
- If network connections work

#### 8.2. Test Connections

**What it is:** Script testing connections between machines.

**Where it is:** `~/th_timmy/hosts/shared/test_connections.sh`

**How to use:**

```bash
# On any machine
cd ~/th_timmy
./hosts/shared/test_connections.sh
```

**What it checks:**
- If machines can ping each other (basic connectivity)
- If ports are open (SSH, PostgreSQL, JupyterLab, n8n)
- If can connect to database
- If services are available

#### 8.3. Test Data Flow

**What it is:** Script testing data flow through system.

**Where it is:** `~/th_timmy/hosts/shared/test_data_flow.sh`

**How to use:**

```bash
# On any machine
cd ~/th_timmy
export POSTGRES_PASSWORD="YourDatabasePassword"
./hosts/shared/test_data_flow.sh
```

**What it checks:**
- If can write data to database
- If can read data from database
- If n8n is available
- If data flow works end-to-end

---

## Troubleshooting

### Problem: Can't log in via SSH

**Possible causes:**
- Wrong IP address
- Wrong username
- SSH port (22) is blocked by firewall
- Machine is turned off

**Solution:**
1. Check machine IP address
2. Check if machine is turned on
3. Check firewall settings
4. Try using different SSH client (PuTTY, Windows Terminal)

### Problem: Installation failed

**Possible causes:**
- No internet access
- No administrator privileges (sudo)
- Wrong configuration
- Insufficient resources (memory, disk)

**Solution:**
1. Check installation logs (will be displayed in terminal)
2. Check if you have internet access: `ping 8.8.8.8`
3. Check privileges: `sudo -v`
4. Check disk space: `df -h`
5. Check memory: `free -h`

### Problem: Database doesn't work

**Possible causes:**
- PostgreSQL is not running
- Wrong password
- Port is blocked by firewall
- Database was not created

**Solution:**
1. Check PostgreSQL status: `sudo systemctl status postgresql`
2. If not running, start: `sudo systemctl start postgresql`
3. Check password in `config.yml`
4. Check firewall: `sudo ufw status`
5. Check logs: `sudo journalctl -u postgresql -n 50`

### Problem: JupyterLab doesn't open in browser

**Possible causes:**
- JupyterLab is not running
- Port 8888 is blocked
- Wrong IP address
- Wrong token

**Solution:**
1. Check if JupyterLab is running: `ps aux | grep jupyter`
2. If not running, start again (see "VM-03 Installation" section)
3. Check firewall: `sudo ufw status`
4. Check IP address: `ip addr show`
5. Use token from terminal (when starting JupyterLab)

### Problem: n8n doesn't work

**Possible causes:**
- Docker container is not running
- Port 5678 is blocked
- Wrong configuration

**Solution:**
1. Check container status: `docker ps`
2. If not running, start: `cd ~/th_timmy/hosts/vm04-orchestrator && docker compose up -d`
3. Check logs: `docker compose logs n8n`
4. Check firewall: `sudo ufw status`
5. Check configuration in `config.yml`

### Problem: Tests don't pass

**Possible causes:**
- Machines can't communicate
- Services are not running
- Wrong configuration

**Solution:**
1. Check network connections: `ping <IP_address>`
2. Check if services are running (PostgreSQL, JupyterLab, n8n)
3. Check configuration in `configs/config.yml`
4. Check test logs (will be saved in `test_results/`)

### Problem: Can't log into n8n

**Possible causes:**
- Wrong username or password
- n8n is not running
- Port is blocked

**Solution:**
1. Check configuration in `hosts/vm04-orchestrator/config.yml`
2. Check if n8n is running: `docker ps`
3. Check logs: `docker compose logs n8n`
4. Try resetting password (if you have access to container)

---

## Next steps

After successful installation and system verification, you can:

1. **Secure system:**
   - Run hardening on all machines
   - Use Hardening Management Interface in n8n

2. **Configure automatic tasks:**
   - Configure automatic health checks
   - Configure automatic repository synchronization

3. **Create first playbook:**
   - Use Playbook Manager in n8n
   - Create playbook for specific MITRE ATT&CK technique

4. **Conduct first hunt:**
   - Use Hunt Selection Form
   - Select techniques for analysis
   - Generate queries
   - Run analysis

5. **Familiarize with documentation:**
   - Read documentation in `docs/` directory
   - Familiarize with playbook examples
   - Learn to use JupyterLab for analysis

---

## Support

If you encounter problems not described in this guide:

1. **Check documentation:**
   - `docs/PROJECT_STATUS.md` - Project status and known issues
   - `docs/TESTING.md` - Testing guide
   - `docs/CONFIGURATION.md` - Configuration guide

2. **Check logs:**
   - Installation logs are displayed in terminal
   - Service logs: `sudo journalctl -u <service_name>`
   - Docker logs: `docker compose logs`

3. **Run diagnostic tests:**
   - `./health_check.sh` on each machine
   - `./hosts/shared/test_connections.sh`
   - `./hosts/shared/test_data_flow.sh`

---

## Summary

This guide walked you through:
- ✅ Environment preparation
- ✅ Installation on all machines
- ✅ System configuration
- ✅ Installation verification
- ✅ Usage of all available tools
- ✅ Troubleshooting

The system is now ready to use. You can proceed with threat hunting and data analysis operations.
