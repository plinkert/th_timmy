# Wymagane Narzędzia dla VM-01: Ingest/Parser

Dokument ten zawiera szczegółową listę wszystkich narzędzi, pakietów systemowych i oprogramowania wymaganych dla VM-01 (Ingest/Parser). Informacje te są przeznaczone dla zespołu developerskiego do tworzenia skryptów instalacyjnych.

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

## VM-01: Ingest/Parser

### Przeznaczenie
Zbieranie, parsowanie i normalizacja danych z różnych źródeł (pliki, API).

### Wymagane Narzędzia

#### 1. Python i Środowisko
```bash
# Pakiet: python3
- Python interpreter
- Wersja: 3.10+ (Ubuntu 22.04 domyślnie ma 3.10.6)
- Minimalna wymagana: 3.10.0

# Pakiet: python3-pip
- Package installer for Python
- Wersja: 22.0.2+ (domyślnie w Ubuntu 22.04)

# Pakiet: python3-venv
- Moduł do tworzenia wirtualnych środowisk Python
- Wersja: 3.10+

# Pakiet: python3-dev
- Nagłówki i biblioteki deweloperskie Python
- Wymagane do kompilacji niektórych pakietów Python (np. psycopg2)
```

**Komendy instalacji:**
```bash
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev
```

**Weryfikacja:**
```bash
python3 --version  # Powinno pokazać: Python 3.10.x
pip3 --version
python3 -m venv --help
```

#### 2. Biblioteki Systemowe dla Python Packages
```bash
# Pakiet: libpq-dev
- PostgreSQL client library (wymagane dla psycopg2)
- Wersja: 14+ (Ubuntu 22.04 ma 14.x)

# Pakiet: libssl-dev
- OpenSSL development files (wymagane dla cryptography)
- Wersja: 3.0.x

# Pakiet: libffi-dev
- Foreign Function Interface library (wymagane dla niektórych pakietów)
- Wersja: 3.4.x

# Pakiet: libxml2-dev
- XML parsing library (opcjonalnie, dla niektórych parserów)
- Wersja: 2.9.x

# Pakiet: libxslt1-dev
- XSLT library (opcjonalnie)
- Wersja: 1.1.x
```

**Komendy instalacji:**
```bash
sudo apt-get install -y \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev
```

#### 3. Python Packages (instalowane przez pip)

**WAŻNE: Utworzenie pliku requirements.txt**

Każda VM wymaga pliku `requirements.txt` w głównym katalogu projektu (`/path/to/project/requirements.txt`). Dla VM-01 plik powinien zawierać następujące pakiety:

**Lokalizacja pliku:** `{PROJECT_ROOT}/requirements.txt`

**Zawartość requirements.txt dla VM-01:**
```txt
# Core dependencies
pandas>=1.5.0
numpy>=1.23.0

# Data processing
pyarrow>=10.0.0

# Database
psycopg2-binary>=2.9.0
sqlalchemy>=2.0.0

# Utilities
pyyaml>=6.0
python-dateutil>=2.8.0
requests>=2.31.0

# Security
cryptography>=41.0.0
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

# Utilities
pyyaml>=6.0
python-dateutil>=2.8.0
requests>=2.31.0

# Security
cryptography>=41.0.0
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

#### 4. Narzędzia do Obsługi Plików
```bash
# Pakiet: file
- Określanie typu pliku
- Wersja: 5.41+

# Pakiet: unzip
- Rozpakowywanie archiwów ZIP
- Wersja: 6.0+

# Pakiet: zip
- Tworzenie archiwów ZIP
- Wersja: 3.0+
```

**Komendy instalacji:**
```bash
sudo apt-get install -y file unzip zip
```

### Konfiguracja VM-01

#### 1. Utworzenie Virtual Environment
```bash
PROJECT_ROOT="/home/user/th_timmy"
cd "$PROJECT_ROOT"
python3 -m venv venv
source venv/bin/activate
```

#### 2. Konfiguracja Zmiennych Środowiskowych
```bash
# Ustawienie locale
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# Dodanie do ~/.bashrc (opcjonalnie)
echo 'export LC_ALL=en_US.UTF-8' >> ~/.bashrc
echo 'export LANG=en_US.UTF-8' >> ~/.bashrc
```

#### 3. Konfiguracja Firewall (jeśli wymagane)
```bash
# Otwarcie portów (jeśli VM-01 ma API endpoint)
sudo ufw allow 8000/tcp  # Przykład dla FastAPI w Fazie 4
sudo ufw reload
```

### Weryfikacja Kompletnej Instalacji VM-01
```bash
# Sprawdzenie Python
python3 --version
which python3

# Sprawdzenie pip
pip3 --version

# Sprawdzenie venv
python3 -m venv --help

# Sprawdzenie bibliotek systemowych
dpkg -l | grep -E "libpq-dev|libssl-dev|libffi-dev"

# Sprawdzenie Python packages (po aktywacji venv)
source venv/bin/activate
pip list | grep -E "pandas|numpy|psycopg2|sqlalchemy"
```

---

**Ostatnia aktualizacja**: 2025-01-09
**Wersja dokumentu**: 1.0

