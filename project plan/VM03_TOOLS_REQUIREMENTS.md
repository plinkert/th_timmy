# Wymagane Narzędzia dla VM-03: Analysis/Jupyter

Dokument ten zawiera szczegółową listę wszystkich narzędzi, pakietów systemowych i oprogramowania wymaganych dla VM-03 (Analysis/Jupyter). Informacje te są przeznaczone dla zespołu developerskiego do tworzenia skryptów instalacyjnych.

---

## Wspólne Wymagania dla Wszystkich VM

### System Operacyjny
- **OS**: Ubuntu Server 22.04 LTS (Jammy Jellyfish)
- **Architektura**: amd64 (x86_64)
- **Wymagania**: Minimalna instalacja Ubuntu Server

### Podstawowe Narzędzia Systemowe (wszystkie VM)
```bash
# Pakiet: build-essential
- gcc (GNU Compiler Collection)
- g++ (GNU C++ Compiler)
- make
- libc6-dev

# Pakiet: software-properties-common
- add-apt-repository (do dodawania repozytoriów)

# Pakiet: apt-transport-https
- Obsługa HTTPS dla apt

# Pakiet: ca-certificates
- Certyfikaty SSL/TLS

# Pakiet: curl
- Narzędzie do pobierania plików przez HTTP/HTTPS
- Wersja: najnowsza dostępna w repo Ubuntu 22.04

# Pakiet: wget
- Alternatywa dla curl
- Wersja: najnowsza dostępna w repo Ubuntu 22.04

# Pakiet: gnupg
- GNU Privacy Guard (do weryfikacji podpisów)
- Wersja: 2.2.x lub nowsza

# Pakiet: lsb-release
- Linux Standard Base (do wykrywania wersji systemu)

# Pakiet: git
- System kontroli wersji
- Wersja: 2.34+ (domyślnie w Ubuntu 22.04)

# Pakiet: vim lub nano
- Edytory tekstu (do edycji plików konfiguracyjnych)
- vim (wersja 8.2+) lub nano (wersja 5.9+)

# Pakiet: net-tools
- ifconfig, netstat (narzędzia sieciowe)

# Pakiet: iproute2
- ip, ss (nowoczesne narzędzia sieciowe)

# Pakiet: ufw
- Uncomplicated Firewall (konfiguracja firewall)

# Pakiet: locales
- Obsługa lokalizacji (en_US.UTF-8)
```

### Komendy Instalacji Wspólnych Narzędzi
```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    curl \
    wget \
    gnupg \
    lsb-release \
    git \
    vim \
    nano \
    net-tools \
    iproute2 \
    ufw \
    locales

# Konfiguracja locale
sudo locale-gen en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
```

### Weryfikacja Wspólnych Narzędzi
```bash
# Sprawdzenie wersji systemu
lsb_release -a

# Sprawdzenie podstawowych narzędzi
git --version
curl --version
wget --version
vim --version || nano --version
```

---

## VM-03: Analysis/Jupyter

### Przeznaczenie
Interaktywna analiza danych, wykonywanie playbooków, interfejs użytkownika.

### Wymagane Narzędzia

#### 1. Python i Środowisko (rozszerzone)
```bash
# Te same pakiety co VM-01:
- python3
- python3-pip
- python3-venv
- python3-dev

# Dodatkowo:
# Pakiet: python3-tk
- Tkinter (GUI toolkit, wymagane dla niektórych wizualizacji matplotlib)
- Wersja: 3.10.x
```

**Komendy instalacji:**
```bash
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-tk
```

#### 2. Biblioteki Systemowe (rozszerzone)
```bash
# Wszystkie z VM-01 plus:

# Pakiet: libpq-dev
- PostgreSQL client library

# Pakiet: libssl-dev
- OpenSSL development files

# Pakiet: libffi-dev
- Foreign Function Interface library

# Pakiet: libjpeg-dev
- JPEG library (dla matplotlib/seaborn)
- Wersja: 8d+

# Pakiet: libpng-dev
- PNG library (dla matplotlib/seaborn)
- Wersja: 1.6.x

# Pakiet: libfreetype6-dev
- FreeType font library (dla matplotlib)
- Wersja: 2.11.x

# Pakiet: pkg-config
- Package configuration tool
- Wersja: 0.29.x
```

**Komendy instalacji:**
```bash
sudo apt-get install -y \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    pkg-config
```

#### 3. JupyterLab i Rozszerzenia
```bash
# Python packages (instalowane przez pip w venv):
- jupyterlab>=4.0.0
- notebook>=7.0.0
- ipykernel>=6.25.0
- ipywidgets>=8.0.0
- jupyterlab-widgets>=3.0.0  # Rozszerzenie dla widgetów
- jupyterlab-git>=0.41.0     # Git integration (opcjonalnie)
```

**Komendy instalacji:**
```bash
# W venv:
source venv/bin/activate
pip install --upgrade pip

pip install \
    jupyterlab>=4.0.0 \
    notebook>=7.0.0 \
    ipykernel>=6.25.0 \
    ipywidgets>=8.0.0 \
    jupyterlab-widgets>=3.0.0
```

#### 4. Python Packages do Analizy

**WAŻNE: Utworzenie pliku requirements.txt**

Każda VM wymaga pliku `requirements.txt` w głównym katalogu projektu (`/path/to/project/requirements.txt`). Dla VM-03 plik powinien zawierać następujące pakiety:

**Lokalizacja pliku:** `{PROJECT_ROOT}/requirements.txt`

**Zawartość requirements.txt dla VM-03:**
```txt
# Core dependencies
pandas>=1.5.0
numpy>=1.23.0

# Data processing
pyarrow>=10.0.0

# Database
psycopg2-binary>=2.9.0
sqlalchemy>=2.0.0

# Jupyter
jupyterlab>=4.0.0
notebook>=7.0.0
ipykernel>=6.25.0
ipywidgets>=8.0.0
jupyterlab-widgets>=3.0.0

# ML/AI
scikit-learn>=1.3.0
matplotlib>=3.7.0
seaborn>=0.12.0
openai>=1.0.0

# Utilities
pyyaml>=6.0
python-dateutil>=2.8.0
requests>=2.31.0

# Security
python-dotenv>=1.0.0

# Logging
loguru>=0.7.0
```

**Instrukcje tworzenia pliku requirements.txt:**
```bash
# Przejście do głównego katalogu projektu
cd /path/to/project

# Utworzenie pliku requirements.txt (jeśli nie istnieje)
cat > requirements.txt << 'EOF'
# Core dependencies
pandas>=1.5.0
numpy>=1.23.0

# Data processing
pyarrow>=10.0.0

# Database
psycopg2-binary>=2.9.0
sqlalchemy>=2.0.0

# Jupyter
jupyterlab>=4.0.0
notebook>=7.0.0
ipykernel>=6.25.0
ipywidgets>=8.0.0
jupyterlab-widgets>=3.0.0

# ML/AI
scikit-learn>=1.3.0
matplotlib>=3.7.0
seaborn>=0.12.0
openai>=1.0.0

# Utilities
pyyaml>=6.0
python-dateutil>=2.8.0
requests>=2.31.0

# Security
python-dotenv>=1.0.0

# Logging
loguru>=0.7.0
EOF
```

**Komendy instalacji:**
```bash
# Utworzenie venv
cd /path/to/project
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Sprawdzenie czy requirements.txt istnieje
if [ ! -f "requirements.txt" ]; then
    echo "ERROR: Plik requirements.txt nie został znaleziony!"
    echo "Utwórz plik requirements.txt zgodnie z instrukcjami powyżej."
    exit 1
fi

# Instalacja zależności
pip install -r requirements.txt
```

#### 5. Node.js (dla niektórych rozszerzeń Jupyter)
```bash
# Pakiet: nodejs
- Node.js runtime (wymagane dla niektórych rozszerzeń JupyterLab)
- Wersja: 18.x LTS (zalecane) lub 20.x
- Instalacja przez NodeSource repository (zalecane)

# Pakiet: npm
- Node Package Manager
- Wersja: 9.x+ (zazwyczaj dołączony do nodejs)
```

**Komendy instalacji Node.js:**
```bash
# Dodanie NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -

# Instalacja Node.js
sudo apt-get install -y nodejs

# Weryfikacja
node --version  # Powinno pokazać: v18.x.x lub v20.x.x
npm --version
```

**Alternatywnie (jeśli NodeSource nie działa):**
```bash
# Z domyślnego repo Ubuntu (starsza wersja)
sudo apt-get install -y nodejs npm
```

### Konfiguracja VM-03

#### 1. Utworzenie Virtual Environment
```bash
PROJECT_ROOT="/home/user/th_timmy"
cd "$PROJECT_ROOT"
python3 -m venv venv
source venv/bin/activate
```

#### 2. Konfiguracja JupyterLab
```bash
# Generowanie konfiguracji
jupyter lab --generate-config

# Edycja konfiguracji
nano ~/.jupyter/jupyter_lab_config.py

# Ważne ustawienia:
# c.ServerApp.ip = '0.0.0.0'  # Nasłuchiwanie na wszystkich interfejsach
# c.ServerApp.port = 8888
# c.ServerApp.open_browser = False
# c.ServerApp.token = ''  # Lub ustawić token z .env
# c.ServerApp.password = ''  # Lub ustawić hasło
```

#### 3. Konfiguracja Jupyter jako Service (opcjonalnie)
```bash
# Utworzenie systemd service
sudo nano /etc/systemd/system/jupyter.service

# Przykładowa konfiguracja:
# [Unit]
# Description=JupyterLab
# After=network.target
#
# [Service]
# Type=simple
# User=user
# WorkingDirectory=/home/user/th_timmy
# Environment="PATH=/home/user/th_timmy/venv/bin"
# ExecStart=/home/user/th_timmy/venv/bin/jupyter lab --ip=0.0.0.0 --port=8888 --no-browser
# Restart=always
#
# [Install]
# WantedBy=multi-user.target

# Włączenie i uruchomienie
sudo systemctl enable jupyter
sudo systemctl start jupyter
```

#### 4. Konfiguracja Firewall
```bash
# Otwarcie portu JupyterLab
sudo ufw allow 8888/tcp
sudo ufw reload
```

### Weryfikacja Kompletnej Instalacji VM-03
```bash
# Sprawdzenie Python
python3 --version

# Sprawdzenie JupyterLab
source venv/bin/activate
jupyter --version
jupyter lab --version

# Sprawdzenie Node.js (jeśli zainstalowany)
node --version
npm --version

# Sprawdzenie Python packages
pip list | grep -E "jupyter|pandas|numpy|matplotlib|seaborn"

# Test uruchomienia JupyterLab
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser
# Sprawdzenie w przeglądarce: http://VM03_IP:8888
```

---

**Ostatnia aktualizacja**: 2025-01-09
**Wersja dokumentu**: 1.0

