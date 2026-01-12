# Tools Guide - Threat Hunting Automation Lab

**Version**: 1.0  
**For**: Non-technical users

This guide describes all available tools in the system, what they're for and how to use them step by step.

---

## Table of Contents

1. [Management tools (n8n)](#management-tools-n8n)
2. [Analysis tools (JupyterLab)](#analysis-tools-jupyterlab)
3. [Command line tools](#command-line-tools)
4. [Service tools (API)](#service-tools-api)
5. [When to use which tool?](#when-to-use-which-tool)

---

## Management tools (n8n)

All management tools are available through n8n - a workflow automation platform. Access to n8n: `http://<VM-04_IP>:5678`

### 1. Management Dashboard

**What it is:** Main control panel for the entire system.

**Where:** n8n → Workflow "Management Dashboard" → Webhook "Dashboard UI"

**What it's for:**
- Monitoring status of all machines in real-time
- Displaying system metrics (CPU, RAM, disk)
- Quick actions (synchronization, health checks)
- Configuration management

**How to use - step by step:**

1. **Log into n8n:**
   ```
   Open browser → http://<VM-04_IP>:5678
   Enter username and password
   Click "Sign In"
   ```

2. **Find Management Dashboard:**
   ```
   In left menu click "Workflows"
   Find "Management Dashboard" on list
   Click on it to open
   ```

3. **Activate workflow (if not active):**
   ```
   In top right corner find "Active" toggle
   Click to turn it on (should be green)
   ```

4. **Open dashboard:**
   ```
   In workflow find node "Dashboard UI" (usually at the end)
   Click on it
   In "Webhook URL" section copy the URL
   Open this URL in new browser tab
   ```

5. **Using dashboard:**
   - **System Overview:**
     - You see 4 cards - one for each machine
     - Card color indicates status:
       - 🟢 Green = everything works correctly
       - 🟡 Yellow = there are problems but machine works
       - 🔴 Red = machine doesn't work
   - **Metrics:**
     - Under each card you see:
       - CPU Usage: processor usage (in %)
       - Memory Usage: memory usage (in %)
       - Disk Usage: disk usage (in %)
   - **Action buttons:**
     - "Sync Repository" - synchronizes code on all machines
     - "Refresh Status" - refreshes status of all machines
     - "Run Health Check" - runs detailed check of selected machine

**Example usage:**

```
Scenario: You want to check if all machines work correctly

1. Open Management Dashboard
2. Check card colors - all should be green
3. If any card is yellow or red:
   a. Click on it
   b. Check metrics - there may be problem with memory or disk
   c. Click "Run Health Check"
   d. Wait for results (1-2 minutes)
   e. Read report - it will show what's wrong
```

**Usage frequency:** Daily or several times a day to monitor system.

---

### 2. Testing Management Interface

**What it is:** Interface for running and managing system tests.

**Where:** n8n → Workflow "Testing Management" → Webhook "Testing Dashboard"

**What it's for:**
- Testing connections between machines
- Testing data flow
- Checking machine health
- Reviewing test history

**How to use - step by step:**

1. **Open Testing Management:**
   ```
   In n8n → Workflows → "Testing Management"
   Make sure workflow is active
   ```

2. **Open test dashboard:**
   ```
   Find node "Testing Dashboard"
   Copy webhook URL
   Open in browser
   ```

3. **Run connection tests:**
   ```
   Click button "Run Connection Tests"
   Wait 1-2 minutes
   You'll see results:
     ✅ PASS - test passed successfully
     ❌ FAIL - test failed
     ⚠️ WARN - test passed but with warnings
   ```

4. **Run data flow tests:**
   ```
   BEFORE running: Set database password
   In terminal (on machine from which you run):
     export POSTGRES_PASSWORD="YourPassword"
   
   In dashboard click "Run Data Flow Tests"
   Wait 2-3 minutes
   Check results
   ```

5. **Run health checks:**
   ```
   Click "Run Health Checks"
   Select machine (or "All VMs")
   Wait 2-5 minutes
   You'll see detailed report for each machine
   ```

6. **Browse test history:**
   ```
   Click "View Test History"
   You'll see list of all executed tests
   You can click on test to see details
   ```

**When to use:**
- After system installation (verification that everything works)
- After configuration changes
- When something doesn't work (diagnostics)
- Regularly (e.g., once a week) as preventive check

**Example usage:**

```
Scenario: After installation you want to make sure everything works

1. Open Testing Management Dashboard
2. Click "Run Connection Tests"
3. Check results - all should be ✅ PASS
4. If there are errors:
   a. Write down which tests didn't pass
   b. Check configuration (IP addresses, ports)
   c. Check firewall
5. Click "Run Data Flow Tests"
6. Check results - should be ✅ PASS
7. If there are errors:
   a. Check if database is running
   b. Check database password
   c. Check logs
```

---

### 3. Deployment Management Interface

**What it is:** Interface for managing installations and deployments.

**Where:** n8n → Workflow "Deployment Management" → Webhook "Deployment Dashboard"

**What it's for:**
- Checking installation status on machines
- Running installations remotely (without logging into machine)
- Reviewing installation logs
- Deployment verification

**How to use - step by step:**

1. **Open Deployment Management:**
   ```
   In n8n → Workflows → "Deployment Management"
   Make sure workflow is active
   ```

2. **Open dashboard:**
   ```
   Find node "Deployment Dashboard"
   Copy webhook URL
   Open in browser
   ```

3. **Check installation status:**
   ```
   Click "Get Installation Status"
   You'll see table with status for each machine:
     ✅ Installed - machine is installed
     ❌ Not Installed - machine is not installed
     ⚠️ Unknown - cannot check
   ```

4. **Run installation on machine:**
   ```
   Select machine from list (e.g., "vm01")
   Click "Run Installation"
   Fill form:
     - Project Root: /home/your_username/th_timmy
     - Config File: (leave empty if using default)
   Click "Start Installation"
   ```

5. **Monitor progress:**
   ```
   You'll see installation progress in real-time
   You can click "View Logs" to see detailed logs
   Wait for completion (may take 10-20 minutes)
   ```

6. **Verify installation:**
   ```
   After completion click "Verify Deployment"
   Select machine
   System will check if installation succeeded
   You'll see verification report
   ```

**When to use:**
- During first system installation
- When you need to reinstall machine
- When updating software
- When checking if everything is installed

**Example usage:**

```
Scenario: You need to reinstall VM-01

1. Open Deployment Management Dashboard
2. Click "Get Installation Status"
3. Check VM-01 status - may be "Not Installed" or "Unknown"
4. Click "Run Installation"
5. Select "vm01" from list
6. Fill form:
   - Project Root: /home/user/th_timmy
7. Click "Start Installation"
8. Monitor progress - you'll see logs in real-time
9. After completion click "Verify Deployment"
10. Check report - should show ✅ all tests PASS
```

---

### 4. Hardening Management Interface

**What it is:** Interface for managing machine security.

**Where:** n8n → Workflow "Hardening Management" → Webhook "Hardening Dashboard"

**What it's for:**
- Checking security status of machines
- Running security process (hardening)
- Comparing before/after security state
- Reviewing security reports

**How to use - step by step:**

1. **Open Hardening Management:**
   ```
   In n8n → Workflows → "Hardening Management"
   Make sure workflow is active
   ```

2. **Open dashboard:**
   ```
   Find node "Hardening Dashboard"
   Copy webhook URL
   Open in browser
   ```

3. **Check security status:**
   ```
   Click "Get Hardening Status"
   You'll see status for each machine:
     ✅ Hardened - machine is fully secured
     ⚠️ Partial - machine is partially secured
     ❌ Not Hardened - machine is not secured
     ❓ Unknown - cannot check status
   ```

4. **BEFORE running hardening - run tests:**
   ```
   IMPORTANT: Always run tests before hardening!
   
   In Testing Management Dashboard:
   1. Click "Run Connection Tests"
   2. Click "Run Data Flow Tests"
   3. Save results - they will be reference point
   ```

5. **Run hardening:**
   ```
   In Hardening Dashboard:
   1. Select machine (e.g., "vm01")
   2. Click "Run Hardening"
   3. IMPORTANT: Check "Capture Before State"
      (will save state before securing)
   4. Click "Start"
   5. Wait 5-10 minutes (depends on machine)
   ```

6. **Compare before/after:**
   ```
   After completion:
   1. Click "Compare Before/After"
   2. Select hardening ID (will be displayed after completion)
   3. Select machine
   4. Click "Compare"
   5. You'll see differences:
      - What was changed
      - Which ports were closed
      - Which settings were changed
   ```

7. **Verify that everything works:**
   ```
   After hardening:
   1. Go back to Testing Management Dashboard
   2. Run tests again
   3. Compare results with tests before hardening
   4. All tests should still pass
   ```

**When to use:**
- After system installation (secure before use)
- When you want to increase security
- When you need to meet security requirements (e.g., compliance)
- Regularly (e.g., once a quarter) as check

**WARNING:** After securing, some ports may be blocked. Make sure you have SSH access to machines!

**Example usage:**

```
Scenario: You want to secure all machines after installation

1. BEFORE hardening:
   a. Open Testing Management Dashboard
   b. Run all tests
   c. Save results (take screenshot or write in notebook)

2. Open Hardening Management Dashboard

3. For each machine (vm01, vm02, vm03, vm04):
   a. Click "Get Hardening Status"
   b. Check status - probably will be "Not Hardened"
   c. Click "Run Hardening"
   d. Check "Capture Before State"
   e. Click "Start"
   f. Wait for completion (5-10 minutes)
   g. Save hardening ID

4. AFTER hardening all machines:
   a. Go back to Testing Management Dashboard
   b. Run all tests again
   c. Compare results - should be same as before hardening
   d. If tests don't pass:
      - Check firewall (may be too restrictive)
      - Check hardening logs
      - Contact administrator

5. Compare before/after:
   a. In Hardening Dashboard click "Compare Before/After"
   b. Select hardening ID
   c. See what was changed
```

---

### 5. Playbook Manager

**What it is:** Interface for managing playbooks (threat analysis scripts).

**Where:** n8n → Workflow "Playbook Manager" → Webhook "Playbook Dashboard"

**What it's for:**
- Browsing available playbooks
- Creating new playbooks
- Editing existing playbooks
- Validating playbooks (checking if they're correct)
- Testing playbooks

**What is a playbook?**
A playbook is a ready script for analyzing specific threat. It contains:
- Threat description (e.g., "Phishing emails")
- MITRE ATT&CK technique (e.g., T1566)
- Queries for different tools (Splunk, Sentinel, etc.)
- Analysis logic

**How to use - step by step:**

1. **Open Playbook Manager:**
   ```
   In n8n → Workflows → "Playbook Manager"
   Make sure workflow is active
   ```

2. **Open dashboard:**
   ```
   Find node "Playbook Dashboard"
   Copy webhook URL
   Open in browser
   ```

3. **Browse available playbooks:**
   ```
   Click "List Playbooks"
   You'll see table with all playbooks:
     - Name
     - Description
     - MITRE Technique ID
     - Status (Valid/Invalid)
     - Last modification date
   ```

4. **View playbook details:**
   ```
   Click on playbook in table
   You'll see details:
     - Full description
     - All queries
     - Configuration
   ```

5. **Create new playbook:**
   ```
   Click "Create New Playbook"
   Fill form:
     
     Name: "Phishing Detection"
     Description: "Detects phishing emails and malicious links"
     MITRE Technique ID: "T1566"
     
     Queries:
       Splunk: "index=security sourcetype=email | search ..."
       Sentinel: "EmailEvents | where ..."
       Defender: "DeviceEvents | where ..."
   
   Click "Create"
   System will automatically validate playbook
   ```

6. **Edit existing playbook:**
   ```
   Select playbook from list
   Click "Edit"
   Change needed fields
   Click "Save"
   System will validate changes
   ```

7. **Validate playbook:**
   ```
   Select playbook
   Click "Validate"
   System will check:
     - If structure is correct
     - If queries are correct
     - If all required fields are filled
   You'll see validation report
   ```

**When to use:**
- When you want to create new playbook for specific threat analysis
- When you need to update existing playbook
- When you want to check if playbook is correct
- When you want to see what playbooks are available

**Example usage:**

```
Scenario: You want to create playbook for detecting ransomware

1. Open Playbook Manager Dashboard
2. Click "Create New Playbook"
3. Fill form:
   - Name: "Ransomware Detection"
   - Description: "Detects ransomware activity based on file encryption patterns"
   - MITRE Technique ID: "T1486" (Data Encrypted for Impact)
4. Add queries for your tools:
   - Splunk: (Splunk query)
   - Sentinel: (Sentinel query)
   - Defender: (Defender query)
5. Click "Create"
6. System will validate playbook
7. If there are errors, fix them and save again
8. Playbook is now ready to use!
```

---

### 6. Hunt Selection Form

**What it is:** Form for selecting hunts (threat hunts) and generating queries.

**Where:** n8n → Workflow "Hunt Selection Form" → Webhook "Hunt Selection Form"

**What it's for:**
- Selecting MITRE ATT&CK techniques for analysis
- Selecting available tools (Splunk, Sentinel, etc.)
- Automatically generating queries for selected hunts
- Running analysis

**How to use - step by step:**

1. **Open Hunt Selection Form:**
   ```
   In n8n → Workflows → "Hunt Selection Form"
   Make sure workflow is active
   ```

2. **Open form:**
   ```
   Find node "Hunt Selection Form"
   Copy webhook URL
   Open in browser
   ```

3. **Fill form:**
   
   **Step 3.1: Select MITRE ATT&CK techniques**
   ```
   You'll see list of MITRE ATT&CK techniques
   Check boxes next to techniques you want to analyze
   Examples:
     ☑ T1566 - Phishing
     ☑ T1059 - Command and Scripting Interpreter
     ☑ T1078 - Valid Accounts
   
   You can select multiple techniques
   ```

   **Step 3.2: Select available tools**
   ```
   Check tools you have available:
     ☑ Splunk
     ☑ Microsoft Sentinel
     ☑ Microsoft Defender
     ☑ Generic SIEM
   
   Select only those you actually have
   ```

   **Step 3.3: Select ingest mode**
   ```
   Select how you want to upload data:
     ○ Manual - manual upload of CSV/JSON files
     ● API - automatic retrieval via API
   
   If you don't have API, select "Manual"
   ```

4. **Generate queries:**
   ```
   Click "Generate Queries"
   System will automatically generate queries for:
     - Each selected technique
     - Each selected tool
   
   You'll see list of queries
   Each query has:
     - Name (e.g., "T1566 - Splunk Query")
     - Query (ready to copy)
     - Description
   ```

5. **Copy and use queries:**
   ```
   For each query:
   1. Click "Copy" next to query
   2. Open your tool (Splunk, Sentinel, etc.)
   3. Paste query
   4. Run query
   5. Save results (export to CSV or JSON)
   ```

6. **Upload results and run analysis:**
   ```
   After executing all queries:
   1. In form click "Upload Results"
   2. Select result files (CSV or JSON)
   3. Click "Upload"
   4. System will automatically:
      - Anonymize data
      - Process data
      - Map data to appropriate playbooks
   5. Click "Start Analysis"
   6. System will run analysis
   7. Wait for results (may take few minutes)
   ```

7. **Review results:**
   ```
   After analysis completes:
   1. You'll see summary:
      - How many findings were found
      - Which techniques were detected
      - Threat level
   2. Click "View Details" to see details
   3. You can export results to report
   ```

**When to use:**
- When you want to conduct threat hunting
- When you want to check specific MITRE ATT&CK techniques
- When you need ready queries for your SIEM/EDR tools
- When you want to automate analysis process

**Example usage:**

```
Scenario: You want to check if there are phishing activities in your network

1. Open Hunt Selection Form
2. Fill form:
   - Techniques: ☑ T1566 (Phishing)
   - Tools: ☑ Splunk, ☑ Microsoft Sentinel
   - Mode: ○ Manual (you don't have API)
3. Click "Generate Queries"
4. You'll see 2 queries:
   - "T1566 - Splunk Query"
   - "T1566 - Sentinel Query"
5. Copy Splunk query:
   a. Open Splunk
   b. Paste query
   c. Run
   d. Export results to CSV
6. Copy Sentinel query:
   a. Open Microsoft Sentinel
   b. Paste query
   c. Run
   d. Export results to CSV
7. In form click "Upload Results"
8. Select both CSV files
9. Click "Upload"
10. Click "Start Analysis"
11. Wait for results
12. Review findings - system will show what it found
```

---

## Analysis tools (JupyterLab)

### JupyterLab

**What it is:** Interactive environment for data analysis and report creation.

**Where:** http://<VM-03_IP>:8888

**What it's for:**
- Data analysis from database
- Creating visualizations (charts, graphics)
- Writing and executing Python scripts
- Creating reports
- Experimenting with data

**How to use - step by step:**

1. **Start JupyterLab:**
   ```
   Log into VM-03 via SSH
   In terminal type:
     cd ~/th_timmy
     source venv/bin/activate
     jupyter lab --ip=0.0.0.0 --port=8888
   ```

2. **Copy token:**
   ```
   In terminal you'll see something like:
     [I 2025-01-12 10:00:00.000 LabApp] 
     http://VM-03_IP:8888/lab?token=abc123def456...
   
   Copy token (part after "token=")
   ```

3. **Open JupyterLab in browser:**
   ```
   Open browser
   Go to: http://<VM-03_IP>:8888
   Paste token when prompted
   Click "Log in"
   ```

4. **Basic operations:**
   
   **Create new notebook:**
   ```
   In JupyterLab click "New" (in top right corner)
   Select "Python 3"
   New notebook will be created
   ```

   **Connect to database:**
   ```
   In first notebook cell type:
   
   import psycopg2
   import pandas as pd
   
   conn = psycopg2.connect(
       host="<VM-02_IP>",
       port=5432,
       database="threat_hunting",
       user="threat_hunter",
       password="YourDatabasePassword"
   )
   
   Press Shift+Enter to execute cell
   ```

   **Execute SQL query:**
   ```
   In new cell type:
   
   query = "SELECT * FROM normalized_logs LIMIT 100"
   df = pd.read_sql(query, conn)
   df.head()
   
   Press Shift+Enter
   You'll see first 100 rows of data in table
   ```

   **Create visualization:**
   ```
   In new cell type:
   
   import matplotlib.pyplot as plt
   
   # Example: chart of number of events over time
   df['timestamp'] = pd.to_datetime(df['timestamp'])
   df.groupby(df['timestamp'].dt.date).size().plot()
   plt.title('Number of events over time')
   plt.show()
   
   Press Shift+Enter
   You'll see chart
   ```

   **Save notebook:**
   ```
   Click "File" → "Save"
   Or press Ctrl+S
   ```

**When to use:**
- When you want to analyze data manually
- When you want to create own visualizations
- When you want to experiment with data
- When you want to write own analysis scripts
- When you want to create custom reports

**Example usage:**

```
Scenario: You want to analyze how many phishing events were in last week

1. Start JupyterLab (see above)
2. Create new notebook
3. Connect to database (see above)
4. Execute query:
   
   query = """
   SELECT 
       DATE(timestamp) as date,
       COUNT(*) as count
   FROM normalized_logs
   WHERE technique_id = 'T1566'
     AND timestamp >= NOW() - INTERVAL '7 days'
   GROUP BY DATE(timestamp)
   ORDER BY date
   """
   
   df = pd.read_sql(query, conn)
   df
   
5. Create chart:
   
   df.plot(x='date', y='count', kind='bar')
   plt.title('Phishing events in last week')
   plt.xlabel('Date')
   plt.ylabel('Number of events')
   plt.show()
   
6. Save notebook
```

---

## Command line tools

These tools are available from terminal (command line) on each machine.

### Health Check

**What it is:** Script checking machine health.

**Where:** On each machine: `~/th_timmy/hosts/vmXX-*/health_check.sh`

**How to use:**

```bash
# On VM-01
cd ~/th_timmy/hosts/vm01-ingest
./health_check.sh

# On VM-02
cd ~/th_timmy/hosts/vm02-database
./health_check.sh

# On VM-03
cd ~/th_timmy/hosts/vm03-analysis
./health_check.sh

# On VM-04
cd ~/th_timmy/hosts/vm04-orchestrator
./health_check.sh
```

**What it checks:**
- ✅ If all required programs are installed
- ✅ If services are running (PostgreSQL, JupyterLab, Docker)
- ✅ If configuration is correct
- ✅ If network connections work

**When to use:**
- After installation (verification)
- When something doesn't work (diagnostics)
- Regularly (check)

---

### Test Connections

**What it is:** Script testing connections between machines.

**Where:** `~/th_timmy/hosts/shared/test_connections.sh`

**How to use:**

```bash
# On any machine
cd ~/th_timmy
./hosts/shared/test_connections.sh
```

**What it checks:**
- ✅ If machines can ping each other
- ✅ If ports are open (SSH, PostgreSQL, JupyterLab, n8n)
- ✅ If can connect to database
- ✅ If services are available

**When to use:**
- After installation (connection verification)
- When you have connection problems
- Regularly (check)

---

### Test Data Flow

**What it is:** Script testing data flow through system.

**Where:** `~/th_timmy/hosts/shared/test_data_flow.sh`

**How to use:**

```bash
# On any machine
cd ~/th_timmy

# Set database password
export POSTGRES_PASSWORD="YourDatabasePassword"

# Run test
./hosts/shared/test_data_flow.sh
```

**What it checks:**
- ✅ If can write data to database
- ✅ If can read data from database
- ✅ If n8n is available
- ✅ If data flow works end-to-end

**When to use:**
- After installation (data flow verification)
- When you have data problems
- Regularly (check)

---

## Service tools (API)

These tools are available through API (programming interface). They're mainly used by n8n workflows, but you can also use them directly.

### Dashboard API

**What it is:** API for system management.

**Where:** http://<VM-04_IP>:8000 (if running)

**What it's for:**
- Getting system status
- Configuration management
- Repository synchronization
- Running health checks

**How to use:**

```bash
# Example: Get system status
curl http://<VM-04_IP>:8000/api/system/overview

# Example: Run health check
curl -X POST http://<VM-04_IP>:8000/api/health/check \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "vm01"}'
```

**Note:** This tool is mainly used by n8n workflows. If you're not a developer, you probably won't use it directly.

---

## When to use which tool?

### Daily monitoring

**Use:** Management Dashboard
- Check status of all machines
- Check metrics (CPU, RAM, disk)
- Run repository synchronization if needed

### Verification after installation

**Use:**
1. Testing Management Interface - run all tests
2. Management Dashboard - check status
3. Health Check (command line) - check each machine

### Securing system

**Use:**
1. Testing Management Interface - run tests BEFORE hardening
2. Hardening Management Interface - run hardening
3. Testing Management Interface - run tests AFTER hardening
4. Compare results

### Conducting threat hunting

**Use:**
1. Hunt Selection Form - select techniques and generate queries
2. Execute queries in your SIEM/EDR tools
3. Hunt Selection Form - upload results and run analysis
4. JupyterLab - analyze results in detail (optionally)

### Creating new playbook

**Use:**
1. Playbook Manager - create new playbook
2. Fill form
3. System will validate playbook
4. If there are errors, fix them

### Troubleshooting problems

**Use:**
1. Management Dashboard - check machine status
2. Testing Management Interface - run tests
3. Health Check (command line) - check details
4. Check logs (command line)

---

## Summary

This guide described all available tools in the system. Remember:

- **Management Dashboard** - daily monitoring
- **Testing Management** - verification and diagnostics
- **Deployment Management** - installations and deployments
- **Hardening Management** - securing
- **Playbook Manager** - playbook management
- **Hunt Selection Form** - threat hunting
- **JupyterLab** - data analysis
- **Command line tools** - advanced operations

All tools are designed to be easy to use, even for non-technical people. If you have questions, check documentation or contact system administrator.

**Good luck!** 🎉
