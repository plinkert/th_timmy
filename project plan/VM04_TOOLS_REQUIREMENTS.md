# Wymagane Narzędzia dla VM-04: Orchestrator

Dokument ten zawiera szczegółową listę wszystkich narzędzi, pakietów systemowych i oprogramowania wymaganych dla VM-04 (Orchestrator). Informacje te są przeznaczone dla zespołu developerskiego do tworzenia skryptów instalacyjnych.

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

## VM-04: Orchestrator

### Przeznaczenie
Automatyzacja workflow, zarządzanie zadaniami, integracja z n8n.

### Wymagane Narzędzia

#### 1. Docker
```bash
# Pakiet: docker-ce
- Docker Community Edition (Engine)
- Wersja: 24.0+ (najnowsza stabilna)
- Instalacja z oficjalnego Docker repository

# Pakiet: docker-ce-cli
- Docker CLI
- Wersja: 24.0+

# Pakiet: containerd.io
- Container runtime
- Wersja: 1.6.x+

# Pakiet: docker-buildx-plugin
- Buildx plugin dla Docker
- Wersja: 0.11.x+

# Pakiet: docker-compose-plugin
- Docker Compose V2 (plugin)
- Wersja: 2.20.x+
```

**Komendy instalacji Docker:**
```bash
# 1. Aktualizacja pakietów
sudo apt-get update

# 2. Instalacja zależności
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 3. Dodanie oficjalnego GPG key Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 4. Dodanie Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. Instalacja Docker Engine
sudo apt-get update
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

# 6. Dodanie użytkownika do grupy docker
sudo usermod -aG docker $USER

# 7. Uruchomienie i włączenie Docker
sudo systemctl start docker
sudo systemctl enable docker

# 8. Weryfikacja
sudo docker run hello-world
```

**Weryfikacja Docker:**
```bash
# Sprawdzenie wersji
docker --version
docker compose version

# Sprawdzenie statusu
sudo systemctl status docker

# Test (wymaga wylogowania i ponownego zalogowania po dodaniu do grupy docker)
docker ps
```

#### 2. Python (dla skryptów zarządzających)
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

#### 3. Python Packages (dla skryptów)

**WAŻNE: Utworzenie pliku requirements.txt**

Każda VM wymaga pliku `requirements.txt` w głównym katalogu projektu (`/path/to/project/requirements.txt`). Dla VM-04 plik powinien zawierać następujące pakiety:

**Lokalizacja pliku:** `{PROJECT_ROOT}/requirements.txt`

**Zawartość requirements.txt dla VM-04:**
```txt
# Utilities
pyyaml>=6.0
python-dotenv>=1.0.0
requests>=2.31.0

# Logging
loguru>=0.7.0

# Docker (opcjonalnie, dla zarządzania kontenerami przez Python)
docker>=6.0.0
```

**Instrukcje tworzenia pliku requirements.txt:**
```bash
# Przejście do głównego katalogu projektu
cd /path/to/project

# Utworzenie pliku requirements.txt (jeśli nie istnieje)
cat > requirements.txt << 'EOF'
# Utilities
pyyaml>=6.0
python-dotenv>=1.0.0
requests>=2.31.0

# Logging
loguru>=0.7.0

# Docker (opcjonalnie, dla zarządzania kontenerami przez Python)
docker>=6.0.0
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

#### 4. n8n (w kontenerze Docker)
```bash
# n8n jest uruchamiane w kontenerze Docker
# Nie wymaga bezpośredniej instalacji pakietów systemowych
# Konfiguracja przez docker-compose.yml
```

### Konfiguracja VM-04

#### 1. Konfiguracja Docker Compose dla n8n
```bash
# Plik: hosts/vm04-orchestrator/docker-compose.yml
# Zawiera konfigurację n8n z:
# - Port: 5678
# - Volume dla danych n8n
# - Zmienne środowiskowe
# - Sieć Docker
```

**Przykładowy docker-compose.yml:**
```yaml
version: '3.8'

services:
  n8n:
    image: n8nio/n8n:latest
    container_name: threat-hunting-n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
    volumes:
      - n8n_data:/home/node/.n8n
    networks:
      - threat-hunting-net

volumes:
  n8n_data:

networks:
  threat-hunting-net:
    driver: bridge
```

#### 2. Konfiguracja Firewall
```bash
# Otwarcie portu n8n
sudo ufw allow 5678/tcp
sudo ufw reload
```

#### 3. Uruchomienie n8n
```bash
# Przejście do katalogu z docker-compose.yml
cd /path/to/project/hosts/vm04-orchestrator

# Uruchomienie n8n
docker compose up -d

# Sprawdzenie statusu
docker compose ps

# Sprawdzenie logów
docker compose logs -f n8n
```

### Weryfikacja Kompletnej Instalacji VM-04
```bash
# Sprawdzenie Docker
docker --version
docker compose version
sudo systemctl status docker

# Sprawdzenie kontenerów
docker ps
docker ps -a

# Sprawdzenie n8n
docker compose ps
curl http://localhost:5678

# Test w przeglądarce: http://VM04_IP:5678
```

---

**Ostatnia aktualizacja**: 2025-01-09
**Wersja dokumentu**: 1.0

