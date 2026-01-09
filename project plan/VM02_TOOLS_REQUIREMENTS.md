# Wymagane Narzędzia dla VM-02: Database

Dokument ten zawiera szczegółową listę wszystkich narzędzi, pakietów systemowych i oprogramowania wymaganych dla VM-02 (Database). Informacje te są przeznaczone dla zespołu developerskiego do tworzenia skryptów instalacyjnych.

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

## VM-02: Database

### Przeznaczenie
Centralne magazyn danych - PostgreSQL z pełnym schematem bazy danych.

### Wymagane Narzędzia

#### 1. PostgreSQL
```bash
# Pakiet: postgresql
- PostgreSQL database server
- Wersja: 14+ (Ubuntu 22.04 domyślnie ma 14.x)
- Minimalna wymagana: 14.0

# Pakiet: postgresql-contrib
- Dodatkowe moduły PostgreSQL (opcjonalnie, ale zalecane)
- Wersja: 14.x

# Pakiet: postgresql-client
- Klient PostgreSQL (psql, pg_dump, etc.)
- Wersja: 14.x

# Pakiet: libpq-dev
- PostgreSQL client library (development files)
- Wersja: 14.x
```

**Komendy instalacji:**
```bash
sudo apt-get update
sudo apt-get install -y \
    postgresql \
    postgresql-contrib \
    postgresql-client \
    libpq-dev
```

**Weryfikacja:**
```bash
# Sprawdzenie wersji PostgreSQL
sudo -u postgres psql --version

# Sprawdzenie statusu serwisu
sudo systemctl status postgresql
```

#### 2. Narzędzia do Backup
```bash
# Pakiet: cron
- Task scheduler (do automatycznych backupów)
- Wersja: 3.0+

# Pakiet: rsync
- Synchronizacja plików (do backupów)
- Wersja: 3.2.x
```

**Komendy instalacji:**
```bash
sudo apt-get install -y cron rsync
```

#### 3. Python (do skryptów zarządzających)
```bash
# Te same pakiety co VM-01:
- python3
- python3-pip
- python3-venv
- python3-dev
```

**Komendy instalacji:**
```bash
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev
```

#### 4. Python Packages (dla skryptów)

**WAŻNE: Utworzenie pliku requirements.txt**

Każda VM wymaga pliku `requirements.txt` w głównym katalogu projektu (`/path/to/project/requirements.txt`). Dla VM-02 plik powinien zawierać następujące pakiety:

**Lokalizacja pliku:** `{PROJECT_ROOT}/requirements.txt`

**Zawartość requirements.txt dla VM-02:**
```txt
# Database
psycopg2-binary>=2.9.0
sqlalchemy>=2.0.0

# Utilities
pyyaml>=6.0
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
# Database
psycopg2-binary>=2.9.0
sqlalchemy>=2.0.0

# Utilities
pyyaml>=6.0
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

### Konfiguracja VM-02

#### 1. Konfiguracja PostgreSQL
```bash
# Plik: /etc/postgresql/14/main/postgresql.conf
# Edycja (wymaga sudo):
sudo nano /etc/postgresql/14/main/postgresql.conf

# Ważne ustawienia:
# - listen_addresses = '*' (lub konkretne IP)
# - port = 5432
# - max_connections = 100 (dostosować do potrzeb)
# - shared_buffers = 256MB (dostosować do RAM)
# - effective_cache_size = 1GB (dostosować do RAM)
```

#### 2. Konfiguracja Dostępu (pg_hba.conf)
```bash
# Plik: /etc/postgresql/14/main/pg_hba.conf
# Dodanie linii dla dostępu z innych VM:
sudo nano /etc/postgresql/14/main/pg_hba.conf

# Przykładowe linie:
# host    threat_hunting    threat_hunter    VM01_IP/32    md5
# host    threat_hunting    threat_hunter    VM03_IP/32    md5
```

#### 3. Utworzenie Bazy Danych i Użytkownika
```bash
# Przełączenie na użytkownika postgres
sudo -u postgres psql

# W psql:
CREATE DATABASE threat_hunting;
CREATE USER threat_hunter WITH PASSWORD 'strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE threat_hunting TO threat_hunter;
\q
```

#### 4. Konfiguracja Firewall
```bash
# Otwarcie portu PostgreSQL
sudo ufw allow 5432/tcp
sudo ufw reload

# Sprawdzenie
sudo ufw status
```

#### 5. Konfiguracja Backup (cron)
```bash
# Utworzenie skryptu backup
sudo nano /usr/local/bin/pg_backup.sh

# Dodanie do crontab
sudo crontab -e
# Przykład: codziennie o 2:00
# 0 2 * * * /usr/local/bin/pg_backup.sh
```

### Weryfikacja Kompletnej Instalacji VM-02
```bash
# Sprawdzenie PostgreSQL
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT version();"

# Sprawdzenie bazy danych
sudo -u postgres psql -d threat_hunting -c "\dt"

# Sprawdzenie użytkownika
sudo -u postgres psql -c "\du"

# Test połączenia z zewnątrz (z VM-01 lub VM-03)
psql -h VM02_IP -U threat_hunter -d threat_hunting -c "SELECT 1;"
```

---

**Ostatnia aktualizacja**: 2025-01-09
**Wersja dokumentu**: 1.0

