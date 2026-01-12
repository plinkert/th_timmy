# Kompleksowy Przewodnik Wdrożenia - Threat Hunting Automation Lab

**Wersja**: 1.0  
**Data**: 2025-01-12  
**Dla**: Użytkowników nietechnicznych

---

## Spis Treści

1. [Wprowadzenie](#wprowadzenie)
2. [Co to jest ten system?](#co-to-jest-ten-system)
3. [Czego potrzebujesz?](#czego-potrzebujesz)
4. [Przygotowanie środowiska](#przygotowanie-środowiska)
5. [Instalacja krok po kroku](#instalacja-krok-po-kroku)
6. [Konfiguracja systemu](#konfiguracja-systemu)
7. [Weryfikacja instalacji](#weryfikacja-instalacji)
8. [Dostępne narzędzia i ich użycie](#dostępne-narzędzia-i-ich-użycie)
9. [Rozwiązywanie problemów](#rozwiązywanie-problemów)
10. [Następne kroki](#następne-kroki)

---

## Wprowadzenie

Ten przewodnik został stworzony specjalnie dla osób, które nie mają doświadczenia technicznego. Każdy krok jest opisany szczegółowo, krok po kroku, tak abyś mógł samodzielnie wdrożyć i używać systemu Threat Hunting Automation Lab.

**Nie martw się** - nawet jeśli nie wiesz, co to jest "SSH" lub "PostgreSQL", ten przewodnik poprowadzi Cię przez cały proces.

---

## Co to jest ten system?

**Threat Hunting Automation Lab** to system, który pomaga zespołom bezpieczeństwa w automatycznym wyszukiwaniu zagrożeń w infrastrukturze IT. System składa się z 4 maszyn wirtualnych (VM), które współpracują ze sobą:

1. **VM-01 (Ingest/Parser)** - Zbiera i przetwarza dane z różnych źródeł
2. **VM-02 (Database)** - Przechowuje dane w bazie danych
3. **VM-03 (Analysis/Jupyter)** - Umożliwia analizę danych i tworzenie raportów
4. **VM-04 (Orchestrator)** - Centralne zarządzanie całym systemem

**Prosty przykład użycia:**
- System automatycznie zbiera logi z różnych systemów
- Analizuje je pod kątem podejrzanych działań
- Generuje raporty z wynikami
- Wszystko zarządzane z jednego miejsca (dashboard)

---

## Czego potrzebujesz?

### Wymagania sprzętowe

Musisz mieć dostęp do **4 maszyn wirtualnych (VM)** z następującymi specyfikacjami:

| VM | Procesor | Pamięć RAM | Dysk | Opis |
|---|---|---|---|---|
| VM-01 | 2 rdzenie | 4 GB | 20 GB | Zbieranie danych |
| VM-02 | 2 rdzenie | 4 GB | 50 GB | Baza danych (więcej miejsca na dane) |
| VM-03 | 4 rdzenie | 8 GB | 30 GB | Analiza (więcej mocy obliczeniowej) |
| VM-04 | 2 rdzenie | 4 GB | 20 GB | Zarządzanie |

**Uwaga:** Jeśli nie masz dostępu do maszyn wirtualnych, możesz je utworzyć w chmurze (np. AWS, Azure, Google Cloud) lub na własnym serwerze.

### Wymagania oprogramowania

Każda maszyna wirtualna musi mieć zainstalowane:

- **Ubuntu Server 22.04 LTS** (lub nowsza wersja)
- **Dostęp do internetu** (do pobierania oprogramowania)
- **Dostęp przez SSH** (do zdalnego zarządzania)

### Wymagania sieciowe

- Wszystkie 4 VM muszą być w tej samej sieci (mogą się komunikować)
- Musisz znać adresy IP każdej maszyny
- Porty, które muszą być otwarte:
  - **22** - SSH (dostęp zdalny)
  - **5432** - PostgreSQL (baza danych)
  - **8888** - JupyterLab (analiza)
  - **5678** - n8n (zarządzanie)

### Wymagania dostępu

- **Konto użytkownika** na każdej maszynie z uprawnieniami administratora (sudo)
- **Hasła** lub **klucze SSH** do logowania na maszyny
- **Podstawowa znajomość** terminala/linii poleceń (ale nie martw się - wszystko jest opisane)

---

## Przygotowanie środowiska

### Krok 1: Sprawdź dostęp do maszyn wirtualnych

Zanim zaczniesz, upewnij się, że:

1. **Masz dostęp do wszystkich 4 maszyn wirtualnych**
   - Możesz się na nie zalogować przez SSH
   - Masz uprawnienia administratora (sudo)

2. **Znasz adresy IP każdej maszyny**
   - Zapisz je w bezpiecznym miejscu
   - Będziesz ich potrzebował podczas konfiguracji

3. **Masz dostęp do internetu** z każdej maszyny
   - System będzie pobierał oprogramowanie z internetu

### Krok 2: Przygotuj notatnik

Zapisz następujące informacje (będziesz ich potrzebował):

```
VM-01 IP: ________________
VM-02 IP: ________________
VM-03 IP: ________________
VM-04 IP: ________________

Hasło do bazy danych: ________________
Hasło do n8n: ________________
Hasło do JupyterLab: ________________
```

**Ważne:** Użyj silnych haseł! Nie używaj prostych haseł jak "123456" lub "password".

### Krok 3: Sprawdź połączenie sieciowe

Z każdej maszyny sprawdź, czy możesz połączyć się z innymi:

```bash
# Na VM-01, sprawdź połączenie z VM-02
ping <VM-02_IP>

# Powinieneś zobaczyć odpowiedzi (pings)
# Jeśli nie widzisz odpowiedzi, sprawdź ustawienia sieci
```

**Jak to zrobić:**
1. Zaloguj się na VM-01 przez SSH
2. Wpisz: `ping <adres_IP_VM-02>`
3. Naciśnij Enter
4. Jeśli widzisz "64 bytes from..." - połączenie działa
5. Naciśnij Ctrl+C, aby zatrzymać

Powtórz to dla wszystkich kombinacji maszyn.

---

## Instalacja krok po kroku

### Etap 1: Pobranie i przygotowanie kodu

#### Krok 1.1: Zaloguj się na VM-04

VM-04 będzie maszyną zarządzającą, więc zaczynamy od niej.

```bash
# Zaloguj się przez SSH (zastąp <VM-04_IP> rzeczywistym adresem IP)
ssh twoja_nazwa_uzytkownika@<VM-04_IP>
```

**Jeśli nie wiesz, jak się zalogować przez SSH:**
- W systemie Windows możesz użyć programu **PuTTY** lub **Windows Terminal**
- W systemie Linux/Mac użyj terminala i komendy `ssh`
- Potrzebujesz nazwy użytkownika i hasła (lub klucza SSH)

#### Krok 1.2: Pobierz kod projektu

Po zalogowaniu na VM-04, wykonaj:

```bash
# Przejdź do katalogu domowego
cd ~

# Pobierz projekt (zastąp <repository-url> rzeczywistym adresem repozytorium)
git clone <repository-url> th_timmy

# Przejdź do katalogu projektu
cd th_timmy
```

**Jeśli nie masz dostępu do repozytorium Git:**
- Możesz pobrać projekt jako plik ZIP
- Rozpakuj go w katalogu domowym
- Zmień nazwę katalogu na `th_timmy`

#### Krok 1.3: Skopiuj projekt na pozostałe maszyny

Musisz mieć ten sam kod na wszystkich maszynach. Najprostszy sposób:

```bash
# Z VM-04, skopiuj projekt na pozostałe maszyny
# (zastąp <VM-01_IP>, <VM-02_IP>, <VM-03_IP> rzeczywistymi adresami)

# Skopiuj na VM-01
scp -r ~/th_timmy twoja_nazwa_uzytkownika@<VM-01_IP>:~/

# Skopiuj na VM-02
scp -r ~/th_timmy twoja_nazwa_uzytkownika@<VM-02_IP>:~/

# Skopiuj na VM-03
scp -r ~/th_timmy twoja_nazwa_uzytkownika@<VM-03_IP>:~/
```

**Alternatywnie:** Możesz pobrać projekt osobno na każdej maszynie (powtórz Krok 1.2 na każdej maszynie).

### Etap 2: Konfiguracja systemu

#### Krok 2.1: Utwórz plik konfiguracyjny

Na VM-04 (lub na maszynie, z której zarządzasz):

```bash
# Przejdź do katalogu projektu
cd ~/th_timmy

# Skopiuj przykładowy plik konfiguracyjny
cp configs/config.example.yml configs/config.yml
```

#### Krok 2.2: Edytuj plik konfiguracyjny

Otwórz plik `configs/config.yml` w edytorze tekstu:

```bash
# Użyj nano (prosty edytor tekstu)
nano configs/config.yml
```

**Jak używać nano:**
- Aby edytować tekst, po prostu zacznij pisać
- Aby zapisać: Ctrl+O, potem Enter
- Aby wyjść: Ctrl+X

**Co musisz zmienić w pliku:**

Znajdź sekcję `vms:` i zmień adresy IP:

```yaml
vms:
  vm01:
    ip: "10.0.0.10"  # ZMIEŃ na rzeczywisty adres IP VM-01
  vm02:
    ip: "10.0.0.11"  # ZMIEŃ na rzeczywisty adres IP VM-02
  vm03:
    ip: "10.0.0.12"  # ZMIEŃ na rzeczywisty adres IP VM-03
  vm04:
    ip: "10.0.0.13"  # ZMIEŃ na rzeczywisty adres IP VM-04
```

Znajdź sekcję `network:` i zmień ustawienia sieci:

```yaml
network:
  subnet: "10.0.0.0/24"  # ZMIEŃ na Twoją sieć (np. "192.168.1.0/24")
  gateway: "10.0.0.1"     # ZMIEŃ na bramę sieciową
```

**Jak znaleźć informacje o sieci:**
- Na każdej maszynie wpisz: `ip addr show` lub `ifconfig`
- Zobaczysz adres IP maszyny i informacje o sieci
- Subnet to zazwyczaj pierwsze 3 liczby adresu IP + ".0/24" (np. jeśli IP to 192.168.1.10, subnet to 192.168.1.0/24)
- Gateway to zazwyczaj adres IP routera (często kończy się na .1)

Zapisz plik (Ctrl+O, Enter) i zamknij (Ctrl+X).

### Etap 3: Instalacja na każdej maszynie

**WAŻNE:** Instaluj maszyny w tej kolejności:
1. Najpierw VM-02 (baza danych) - inne maszyny zależą od niej
2. Potem VM-01 (zbieranie danych)
3. Potem VM-03 (analiza)
4. Na końcu VM-04 (zarządzanie)

#### Instalacja VM-02 (Baza danych)

**Krok 3.1: Zaloguj się na VM-02**

```bash
ssh twoja_nazwa_uzytkownika@<VM-02_IP>
```

**Krok 3.2: Przejdź do katalogu projektu**

```bash
cd ~/th_timmy/hosts/vm02-database
```

**Krok 3.3: Utwórz plik konfiguracyjny dla bazy danych**

```bash
# Skopiuj przykładowy plik
cp config.example.yml config.yml

# Otwórz w edytorze
nano config.yml
```

**Co musisz ustawić:**

1. **`database_password`** - Silne hasło do bazy danych (zapisz je!)
   ```yaml
   database_password: "TwojeSilneHaslo123!"
   ```

2. **`allowed_ips`** - Adresy IP maszyn, które mogą łączyć się z bazą danych
   ```yaml
   allowed_ips:
     - "10.0.0.10"  # VM-01 IP
     - "10.0.0.12"  # VM-03 IP
   ```

Zapisz plik (Ctrl+O, Enter) i zamknij (Ctrl+X).

**Krok 3.4: Uruchom instalację**

```bash
# Uruchom skrypt instalacyjny (potrzebujesz uprawnień administratora)
sudo ./install_vm02.sh
```

**Co się dzieje podczas instalacji:**
- Instaluje PostgreSQL (baza danych)
- Tworzy bazę danych i użytkownika
- Konfiguruje dostęp sieciowy
- Instaluje narzędzia pomocnicze

**To może zająć 10-15 minut.** Poczekaj, aż instalacja się zakończy.

**Krok 3.5: Sprawdź, czy instalacja się powiodła**

```bash
# Uruchom skrypt weryfikacyjny
./health_check.sh
```

**Co powinieneś zobaczyć:**
- ✅ Wszystkie testy powinny być oznaczone jako "PASS" lub "OK"
- Jeśli widzisz błędy, zapisz je i przejdź do sekcji "Rozwiązywanie problemów"

#### Instalacja VM-01 (Zbieranie danych)

**Krok 3.6: Zaloguj się na VM-01**

```bash
ssh twoja_nazwa_uzytkownika@<VM-01_IP>
```

**Krok 3.7: Przejdź do katalogu projektu**

```bash
cd ~/th_timmy/hosts/vm01-ingest
```

**Krok 3.8: Uruchom instalację**

```bash
sudo ./install_vm01.sh
```

**Co się dzieje podczas instalacji:**
- Instaluje Python i narzędzia programistyczne
- Instaluje biblioteki do przetwarzania danych
- Konfiguruje środowisko wirtualne

**Krok 3.9: Sprawdź instalację**

```bash
./health_check.sh
```

#### Instalacja VM-03 (Analiza)

**Krok 3.10: Zaloguj się na VM-03**

```bash
ssh twoja_nazwa_uzytkownika@<VM-03_IP>
```

**Krok 3.11: Przejdź do katalogu projektu**

```bash
cd ~/th_timmy/hosts/vm03-analysis
```

**Krok 3.12: (Opcjonalnie) Utwórz plik konfiguracyjny dla JupyterLab**

```bash
# Skopiuj przykładowy plik
cp config.example.yml config.yml

# Otwórz w edytorze
nano config.yml
```

**Co możesz ustawić:**
- `jupyter_ip` - Adres IP, na którym JupyterLab będzie dostępny (zostaw "0.0.0.0" dla wszystkich interfejsów)
- `jupyter_port` - Port (domyślnie 8888)
- `jupyter_token` - Token dostępu (zostaw puste, aby wygenerować automatycznie)
- `jupyter_password` - Hasło (opcjonalnie)

Zapisz plik (Ctrl+O, Enter) i zamknij (Ctrl+X).

**Krok 3.13: Uruchom instalację**

```bash
sudo ./install_vm03.sh
```

**Co się dzieje podczas instalacji:**
- Instaluje Python i JupyterLab
- Instaluje biblioteki do analizy danych i uczenia maszynowego
- Konfiguruje JupyterLab

**Krok 3.14: Sprawdź instalację**

```bash
./health_check.sh
```

**Krok 3.15: Uruchom JupyterLab**

```bash
# Aktywuj środowisko wirtualne
source ~/th_timmy/venv/bin/activate

# Uruchom JupyterLab
jupyter lab --ip=0.0.0.0 --port=8888
```

**Zapisz token, który się pojawi!** Będziesz go potrzebował do logowania.

**Przykład wyjścia:**
```
[I 2025-01-12 10:00:00.000 LabApp] http://VM-03_IP:8888/lab?token=abc123def456...
```

**Aby zatrzymać JupyterLab:** Naciśnij Ctrl+C w terminalu.

#### Instalacja VM-04 (Zarządzanie)

**Krok 3.16: Zaloguj się na VM-04**

```bash
ssh twoja_nazwa_uzytkownika@<VM-04_IP>
```

**Krok 3.17: Przejdź do katalogu projektu**

```bash
cd ~/th_timmy/hosts/vm04-orchestrator
```

**Krok 3.18: Utwórz plik konfiguracyjny dla n8n**

```bash
# Skopiuj przykładowy plik
cp config.example.yml config.yml

# Otwórz w edytorze
nano config.yml
```

**Co musisz ustawić:**

1. **`basic_auth_user`** - Nazwa użytkownika do logowania w n8n
   ```yaml
   basic_auth_user: "admin"
   ```

2. **`basic_auth_password`** - Hasło do logowania w n8n (zapisz je!)
   ```yaml
   basic_auth_password: "TwojeSilneHaslo123!"
   ```

Zapisz plik (Ctrl+O, Enter) i zamknij (Ctrl+X).

**Krok 3.19: Uruchom instalację**

```bash
sudo ./install_vm04.sh
```

**Co się dzieje podczas instalacji:**
- Instaluje Docker
- Pobiera i uruchamia n8n w kontenerze Docker
- Konfiguruje dostęp sieciowy

**Krok 3.20: Sprawdź instalację**

```bash
./health_check.sh
```

**Krok 3.21: Sprawdź, czy n8n działa**

```bash
# Sprawdź status kontenera Docker
docker ps

# Powinieneś zobaczyć kontener "n8n" w stanie "Up"
```

**Krok 3.22: Otwórz n8n w przeglądarce**

Otwórz przeglądarkę i przejdź do:
```
http://<VM-04_IP>:5678
```

Zaloguj się używając:
- **Nazwa użytkownika:** Ta, którą ustawiłeś w `config.yml`
- **Hasło:** To, które ustawiłeś w `config.yml`

---

## Konfiguracja systemu

### Konfiguracja n8n workflows

Po zalogowaniu się do n8n, musisz zaimportować gotowe workflows (przepływy pracy).

#### Krok 4.1: Importuj Management Dashboard

1. W n8n, kliknij **"Workflows"** w menu po lewej stronie
2. Kliknij **"Import from File"** (lub ikonę importu)
3. Przejdź do katalogu: `~/th_timmy/hosts/vm04-orchestrator/n8n-workflows/`
4. Wybierz plik: `management-dashboard.json`
5. Kliknij **"Import"**

**Powtórz to dla pozostałych workflows:**
- `testing-management.json` - Zarządzanie testami
- `deployment-management.json` - Zarządzanie wdrożeniami
- `hardening-management.json` - Zarządzanie zabezpieczeniami
- `playbook-manager.json` - Zarządzanie playbookami
- `hunt-selection-form.json` - Formularz wyboru huntów

#### Krok 4.2: Aktywuj workflows

1. Po zaimportowaniu, każdy workflow będzie widoczny na liście
2. Kliknij na workflow, aby go otworzyć
3. Kliknij przycisk **"Active"** (w prawym górnym rogu), aby go aktywować
4. Workflow jest teraz aktywny i będzie działał automatycznie

---

## Weryfikacja instalacji

### Test połączeń

Na dowolnej maszynie (najlepiej VM-04), uruchom testy połączeń:

```bash
cd ~/th_timmy
./hosts/shared/test_connections.sh
```

**Co powinieneś zobaczyć:**
- ✅ Wszystkie testy ping powinny być "PASS"
- ✅ Testy portów powinny być "PASS"
- ⚠️ Testy SSH mogą pokazać "WARN" (to normalne, jeśli nie masz skonfigurowanych kluczy SSH)

### Test przepływu danych

```bash
# Ustaw hasło do bazy danych jako zmienną środowiskową
export POSTGRES_PASSWORD="TwojeHasloDoBazyDanych"

# Uruchom test przepływu danych
./hosts/shared/test_data_flow.sh
```

**Co powinieneś zobaczyć:**
- ✅ Testy zapisu do bazy danych powinny być "PASS"
- ✅ Testy odczytu z bazy danych powinny być "PASS"
- ✅ Testy n8n powinny być "PASS"

---

## Dostępne narzędzia i ich użycie

System zawiera wiele narzędzi do zarządzania i monitorowania. Poniżej znajdziesz szczegółowy opis każdego narzędzia.

### 1. Management Dashboard (n8n)

**Co to jest:** Główny panel zarządzania systemem, dostępny przez przeglądarkę.

**Gdzie jest:** http://<VM-04_IP>:5678

**Do czego służy:**
- Monitorowanie statusu wszystkich maszyn
- Wyświetlanie metryk systemowych (CPU, RAM, dysk)
- Zarządzanie konfiguracją
- Synchronizacja repozytorium
- Szybkie akcje (health checks, testy)

**Jak używać:**

1. **Zaloguj się do n8n:**
   - Otwórz przeglądarkę
   - Przejdź do: `http://<VM-04_IP>:5678`
   - Zaloguj się używając nazwy użytkownika i hasła z `config.yml`

2. **Otwórz Management Dashboard:**
   - W n8n, znajdź workflow "Management Dashboard"
   - Kliknij na niego, aby otworzyć
   - Kliknij przycisk "Active", aby go aktywować (jeśli nie jest aktywny)

3. **Dostęp do dashboardu:**
   - Dashboard jest dostępny przez webhook
   - W workflow znajdź węzeł "Dashboard UI"
   - Kliknij na niego i skopiuj URL webhooka
   - Otwórz ten URL w przeglądarce

4. **Używanie dashboardu:**
   - **System Overview:** Widzisz status wszystkich 4 maszyn
     - 🟢 Zielony = maszyna działa prawidłowo
     - 🟡 Żółty = maszyna ma problemy, ale działa
     - 🔴 Czerwony = maszyna nie działa
   - **Metryki:** Widzisz użycie CPU, RAM i dysku dla każdej maszyny
   - **Synchronizacja repozytorium:** Kliknij przycisk "Sync Repository", aby zsynchronizować kod na wszystkich maszynach
   - **Health Checks:** Kliknij przycisk "Refresh Status", aby sprawdzić status wszystkich maszyn

**Przykładowe użycie:**

```
1. Otwórz dashboard w przeglądarce
2. Sprawdź status maszyn - wszystkie powinny być zielone
3. Jeśli któraś maszyna jest żółta lub czerwona:
   - Kliknij na nią, aby zobaczyć szczegóły
   - Sprawdź metryki - może być problem z pamięcią lub dyskiem
   - Kliknij "Run Health Check", aby uruchomić szczegółowe sprawdzenie
```

### 2. Testing Management Interface

**Co to jest:** Interfejs do zarządzania testami systemu.

**Gdzie jest:** W n8n, workflow "Testing Management"

**Do czego służy:**
- Uruchamianie testów połączeń między maszynami
- Testowanie przepływu danych
- Sprawdzanie zdrowia maszyn
- Przeglądanie wyników testów

**Jak używać:**

1. **Otwórz Testing Management:**
   - W n8n, znajdź workflow "Testing Management"
   - Kliknij na niego
   - Upewnij się, że jest aktywny

2. **Dostęp do interfejsu:**
   - Znajdź węzeł "Testing Dashboard"
   - Skopiuj URL webhooka
   - Otwórz w przeglądarce

3. **Uruchamianie testów:**
   - **Connection Tests:** Testuje połączenia między maszynami
     - Kliknij "Run Connection Tests"
     - Poczekaj na wyniki (może zająć 1-2 minuty)
   - **Data Flow Tests:** Testuje przepływ danych przez system
     - Kliknij "Run Data Flow Tests"
     - Upewnij się, że hasło do bazy danych jest ustawione
   - **Health Checks:** Sprawdza zdrowie wszystkich maszyn
     - Kliknij "Run Health Checks"
     - Zobaczysz szczegółowe informacje o każdej maszynie

**Kiedy używać:**
- Po instalacji systemu (weryfikacja, że wszystko działa)
- Po zmianach w konfiguracji
- Gdy coś nie działa (diagnostyka)
- Regularnie (np. raz w tygodniu) jako kontrola

### 3. Deployment Management Interface

**Co to jest:** Interfejs do zarządzania wdrożeniami i instalacjami.

**Gdzie jest:** W n8n, workflow "Deployment Management"

**Do czego służy:**
- Sprawdzanie statusu instalacji na maszynach
- Uruchamianie instalacji zdalnie
- Przeglądanie logów instalacji
- Weryfikacja wdrożeń

**Jak używać:**

1. **Otwórz Deployment Management:**
   - W n8n, znajdź workflow "Deployment Management"
   - Kliknij na niego
   - Upewnij się, że jest aktywny

2. **Dostęp do interfejsu:**
   - Znajdź węzeł "Deployment Dashboard"
   - Skopiuj URL webhooka
   - Otwórz w przeglądarce

3. **Sprawdzanie statusu instalacji:**
   - Kliknij "Get Installation Status"
   - Zobaczysz status instalacji na każdej maszynie:
     - ✅ Installed - maszyna jest zainstalowana
     - ❌ Not Installed - maszyna nie jest zainstalowana
     - ⚠️ Unknown - nie można sprawdzić statusu

4. **Uruchamianie instalacji:**
   - Wybierz maszynę z listy
   - Kliknij "Run Installation"
   - Podaj parametry (ścieżka do projektu, itp.)
   - Kliknij "Start"
   - Monitoruj postęp w logach

**Kiedy używać:**
- Podczas pierwszej instalacji systemu
- Gdy musisz ponownie zainstalować maszynę
- Gdy aktualizujesz oprogramowanie
- Gdy sprawdzasz, czy wszystko jest zainstalowane

### 4. Hardening Management Interface

**Co to jest:** Interfejs do zarządzania zabezpieczeniami maszyn.

**Gdzie jest:** W n8n, workflow "Hardening Management"

**Do czego służy:**
- Sprawdzanie statusu zabezpieczeń maszyn
- Uruchamianie procesu zabezpieczania (hardening)
- Porównywanie przed/po zabezpieczeniu
- Przeglądanie raportów zabezpieczeń

**Jak używać:**

1. **Otwórz Hardening Management:**
   - W n8n, znajdź workflow "Hardening Management"
   - Kliknij na niego
   - Upewnij się, że jest aktywny

2. **Dostęp do interfejsu:**
   - Znajdź węzeł "Hardening Dashboard"
   - Skopiuj URL webhooka
   - Otwórz w przeglądarce

3. **Sprawdzanie statusu zabezpieczeń:**
   - Kliknij "Get Hardening Status"
   - Zobaczysz status dla każdej maszyny:
     - ✅ Hardened - maszyna jest zabezpieczona
     - ⚠️ Partial - maszyna jest częściowo zabezpieczona
     - ❌ Not Hardened - maszyna nie jest zabezpieczona

4. **Uruchamianie zabezpieczania:**
   - **WAŻNE:** Przed uruchomieniem, wykonaj testy, aby mieć punkt odniesienia
   - Wybierz maszynę
   - Kliknij "Run Hardening"
   - Wybierz opcję "Capture Before State" (zapisz stan przed)
   - Kliknij "Start"
   - Poczekaj na zakończenie (może zająć 5-10 minut)

5. **Porównywanie przed/po:**
   - Po zakończeniu zabezpieczania, możesz porównać wyniki
   - Kliknij "Compare Before/After"
   - Wybierz ID zabezpieczania
   - Zobaczysz różnice

**Kiedy używać:**
- Po instalacji systemu (zabezpieczenie przed użyciem)
- Gdy chcesz zwiększyć bezpieczeństwo
- Gdy musisz spełnić wymagania bezpieczeństwa
- Regularnie (np. raz na kwartał) jako kontrola

**UWAGA:** Po zabezpieczeniu, niektóre porty mogą być zablokowane. Upewnij się, że masz dostęp do maszyn przez SSH!

### 5. Playbook Manager

**Co to jest:** Interfejs do zarządzania playbookami (skryptami analizy zagrożeń).

**Gdzie jest:** W n8n, workflow "Playbook Manager"

**Do czego służy:**
- Przeglądanie dostępnych playbooków
- Tworzenie nowych playbooków
- Edycja istniejących playbooków
- Walidacja playbooków
- Testowanie playbooków

**Jak używać:**

1. **Otwórz Playbook Manager:**
   - W n8n, znajdź workflow "Playbook Manager"
   - Kliknij na niego
   - Upewnij się, że jest aktywny

2. **Dostęp do interfejsu:**
   - Znajdź węzeł "Playbook Dashboard"
   - Skopiuj URL webhooka
   - Otwórz w przeglądarce

3. **Przeglądanie playbooków:**
   - Kliknij "List Playbooks"
   - Zobaczysz listę wszystkich dostępnych playbooków
   - Każdy playbook ma:
     - Nazwę
     - Opis
     - Status (valid/invalid)
     - Datę ostatniej modyfikacji

4. **Tworzenie nowego playbooka:**
   - Kliknij "Create New Playbook"
   - Wypełnij formularz:
     - Nazwa playbooka
     - Opis
     - MITRE ATT&CK Technique ID (np. T1566)
     - Zapytania dla różnych narzędzi (Splunk, Sentinel, itp.)
   - Kliknij "Create"
   - System automatycznie zwaliduje playbook

5. **Edycja playbooka:**
   - Wybierz playbook z listy
   - Kliknij "Edit"
   - Zmień potrzebne pola
   - Kliknij "Save"
   - System zwaliduje zmiany

**Kiedy używać:**
- Gdy chcesz stworzyć nowy playbook do analizy konkretnego zagrożenia
- Gdy musisz zaktualizować istniejący playbook
- Gdy chcesz sprawdzić, czy playbook jest poprawny
- Gdy chcesz zobaczyć, jakie playbooki są dostępne

### 6. Hunt Selection Form

**Co to jest:** Formularz do wyboru huntów (polowań na zagrożenia) i narzędzi.

**Gdzie jest:** W n8n, workflow "Hunt Selection Form"

**Do czego służy:**
- Wybór technik MITRE ATT&CK do analizy
- Wybór dostępnych narzędzi (Splunk, Sentinel, itp.)
- Generowanie zapytań dla wybranych huntów
- Uruchamianie analizy

**Jak używać:**

1. **Otwórz Hunt Selection Form:**
   - W n8n, znajdź workflow "Hunt Selection Form"
   - Kliknij na niego
   - Upewnij się, że jest aktywny

2. **Dostęp do formularza:**
   - Znajdź węzeł "Hunt Selection Form"
   - Skopiuj URL webhooka
   - Otwórz w przeglądarce

3. **Wypełnianie formularza:**
   - **Wybierz techniki MITRE ATT&CK:**
     - Zaznacz checkboxy przy technikach, które chcesz analizować
     - Możesz wybrać wiele technik
   - **Wybierz dostępne narzędzia:**
     - Zaznacz narzędzia, które masz dostępne (Splunk, Sentinel, Defender, itp.)
   - **Wybierz tryb ingestu:**
     - Manual - ręczne wgranie danych
     - API - automatyczne pobieranie przez API
   - Kliknij "Generate Queries"

4. **Generowanie zapytań:**
   - System automatycznie wygeneruje zapytania dla wybranych technik i narzędzi
   - Zobaczysz listę zapytań
   - Możesz je skopiować i użyć w swoich narzędziach

5. **Uruchamianie analizy:**
   - Po wykonaniu zapytań w swoich narzędziach, wgraj wyniki
   - Kliknij "Start Analysis"
   - System automatycznie przetworzy dane i wygeneruje raport

**Kiedy używać:**
- Gdy chcesz przeprowadzić threat hunting
- Gdy chcesz sprawdzić konkretne techniki MITRE ATT&CK
- Gdy potrzebujesz zapytań dla swoich narzędzi SIEM/EDR
- Gdy chcesz zautomatyzować proces analizy

### 7. JupyterLab (Analiza danych)

**Co to jest:** Interaktywne środowisko do analizy danych i tworzenia raportów.

**Gdzie jest:** http://<VM-03_IP>:8888

**Do czego służy:**
- Analiza danych z bazy danych
- Tworzenie wizualizacji
- Pisanie i wykonywanie skryptów Python
- Tworzenie raportów
- Eksperymentowanie z danymi

**Jak używać:**

1. **Uruchom JupyterLab:**
   - Zaloguj się na VM-03 przez SSH
   - Uruchom:
     ```bash
     cd ~/th_timmy
     source venv/bin/activate
     jupyter lab --ip=0.0.0.0 --port=8888
     ```
   - Skopiuj token, który się pojawi

2. **Otwórz JupyterLab w przeglądarce:**
   - Otwórz przeglądarkę
   - Przejdź do: `http://<VM-03_IP>:8888`
   - Wklej token, gdy zostaniesz poproszony

3. **Podstawowe operacje:**
   - **Utwórz nowy notebook:**
     - Kliknij "New" → "Python 3"
     - Zostanie utworzony nowy notebook
   - **Połącz się z bazą danych:**
     ```python
     import psycopg2
     
     conn = psycopg2.connect(
         host="<VM-02_IP>",
         port=5432,
         database="threat_hunting",
         user="threat_hunter",
         password="TwojeHaslo"
     )
     ```
   - **Wykonaj zapytanie:**
     ```python
     import pandas as pd
     
     query = "SELECT * FROM normalized_logs LIMIT 100"
     df = pd.read_sql(query, conn)
     df.head()
     ```

**Kiedy używać:**
- Gdy chcesz przeanalizować dane ręcznie
- Gdy chcesz stworzyć własne wizualizacje
- Gdy chcesz eksperymentować z danymi
- Gdy chcesz napisać własne skrypty analizy

### 8. Narzędzia wiersza poleceń

System zawiera również narzędzia, które możesz używać z linii poleceń (terminala).

#### 8.1. Health Check

**Co to jest:** Skrypt sprawdzający zdrowie maszyny.

**Gdzie jest:** Na każdej maszynie: `~/th_timmy/hosts/vmXX-*/health_check.sh`

**Jak używać:**

```bash
# Na dowolnej maszynie
cd ~/th_timmy/hosts/vm01-ingest  # (lub vm02, vm03, vm04)
./health_check.sh
```

**Co sprawdza:**
- Czy wszystkie wymagane programy są zainstalowane
- Czy serwisy działają (PostgreSQL, JupyterLab, Docker)
- Czy konfiguracja jest poprawna
- Czy połączenia sieciowe działają

#### 8.2. Test Connections

**Co to jest:** Skrypt testujący połączenia między maszynami.

**Gdzie jest:** `~/th_timmy/hosts/shared/test_connections.sh`

**Jak używać:**

```bash
# Na dowolnej maszynie
cd ~/th_timmy
./hosts/shared/test_connections.sh
```

**Co sprawdza:**
- Czy maszyny mogą się pingować (podstawowa łączność)
- Czy porty są otwarte (SSH, PostgreSQL, JupyterLab, n8n)
- Czy można połączyć się z bazą danych
- Czy serwisy są dostępne

#### 8.3. Test Data Flow

**Co to jest:** Skrypt testujący przepływ danych przez system.

**Gdzie jest:** `~/th_timmy/hosts/shared/test_data_flow.sh`

**Jak używać:**

```bash
# Na dowolnej maszynie
cd ~/th_timmy
export POSTGRES_PASSWORD="TwojeHasloDoBazyDanych"
./hosts/shared/test_data_flow.sh
```

**Co sprawdza:**
- Czy można zapisać dane do bazy danych
- Czy można odczytać dane z bazy danych
- Czy n8n jest dostępne
- Czy przepływ danych działa end-to-end

---

## Rozwiązywanie problemów

### Problem: Nie mogę się zalogować przez SSH

**Możliwe przyczyny:**
- Błędny adres IP
- Błędna nazwa użytkownika
- Port SSH (22) jest zablokowany przez firewall
- Maszyna jest wyłączona

**Rozwiązanie:**
1. Sprawdź adres IP maszyny
2. Sprawdź, czy maszyna jest włączona
3. Sprawdź ustawienia firewall
4. Spróbuj użyć innego klienta SSH (PuTTY, Windows Terminal)

### Problem: Instalacja się nie powiodła

**Możliwe przyczyny:**
- Brak dostępu do internetu
- Brak uprawnień administratora (sudo)
- Błędna konfiguracja
- Niewystarczające zasoby (pamięć, dysk)

**Rozwiązanie:**
1. Sprawdź logi instalacji (zostaną wyświetlone w terminalu)
2. Sprawdź, czy masz dostęp do internetu: `ping 8.8.8.8`
3. Sprawdź uprawnienia: `sudo -v`
4. Sprawdź miejsce na dysku: `df -h`
5. Sprawdź pamięć: `free -h`

### Problem: Baza danych nie działa

**Możliwe przyczyny:**
- PostgreSQL nie jest uruchomiony
- Błędne hasło
- Port jest zablokowany przez firewall
- Baza danych nie została utworzona

**Rozwiązanie:**
1. Sprawdź status PostgreSQL: `sudo systemctl status postgresql`
2. Jeśli nie działa, uruchom: `sudo systemctl start postgresql`
3. Sprawdź hasło w `config.yml`
4. Sprawdź firewall: `sudo ufw status`
5. Sprawdź logi: `sudo journalctl -u postgresql -n 50`

### Problem: JupyterLab nie otwiera się w przeglądarce

**Możliwe przyczyny:**
- JupyterLab nie jest uruchomiony
- Port 8888 jest zablokowany
- Błędny adres IP
- Błędny token

**Rozwiązanie:**
1. Sprawdź, czy JupyterLab działa: `ps aux | grep jupyter`
2. Jeśli nie działa, uruchom ponownie (patrz sekcja "Instalacja VM-03")
3. Sprawdź firewall: `sudo ufw status`
4. Sprawdź adres IP: `ip addr show`
5. Użyj tokenu z terminala (gdy uruchamiasz JupyterLab)

### Problem: n8n nie działa

**Możliwe przyczyny:**
- Kontener Docker nie jest uruchomiony
- Port 5678 jest zablokowany
- Błędna konfiguracja

**Rozwiązanie:**
1. Sprawdź status kontenera: `docker ps`
2. Jeśli nie działa, uruchom: `cd ~/th_timmy/hosts/vm04-orchestrator && docker compose up -d`
3. Sprawdź logi: `docker compose logs n8n`
4. Sprawdź firewall: `sudo ufw status`
5. Sprawdź konfigurację w `config.yml`

### Problem: Testy nie przechodzą

**Możliwe przyczyny:**
- Maszyny nie mogą się komunikować
- Serwisy nie działają
- Błędna konfiguracja

**Rozwiązanie:**
1. Sprawdź połączenia sieciowe: `ping <adres_IP>`
2. Sprawdź, czy serwisy działają (PostgreSQL, JupyterLab, n8n)
3. Sprawdź konfigurację w `configs/config.yml`
4. Sprawdź logi testów (zostaną zapisane w `test_results/`)

### Problem: Nie mogę się zalogować do n8n

**Możliwe przyczyny:**
- Błędna nazwa użytkownika lub hasło
- n8n nie jest uruchomiony
- Port jest zablokowany

**Rozwiązanie:**
1. Sprawdź konfigurację w `hosts/vm04-orchestrator/config.yml`
2. Sprawdź, czy n8n działa: `docker ps`
3. Sprawdź logi: `docker compose logs n8n`
4. Spróbuj zresetować hasło (jeśli masz dostęp do kontenera)

---

## Następne kroki

Po pomyślnej instalacji i weryfikacji systemu, możesz:

1. **Zabezpieczyć system:**
   - Uruchom hardening na wszystkich maszynach
   - Użyj Hardening Management Interface w n8n

2. **Skonfigurować automatyczne zadania:**
   - Skonfiguruj automatyczne health checks
   - Skonfiguruj automatyczną synchronizację repozytorium

3. **Stworzyć pierwszy playbook:**
   - Użyj Playbook Manager w n8n
   - Stwórz playbook dla konkretnej techniki MITRE ATT&CK

4. **Przeprowadzić pierwszy hunt:**
   - Użyj Hunt Selection Form
   - Wybierz techniki do analizy
   - Wygeneruj zapytania
   - Wykonaj analizę

5. **Zapoznać się z dokumentacją:**
   - Przeczytaj dokumentację w katalogu `docs/`
   - Zapoznaj się z przykładami playbooków
   - Naucz się używać JupyterLab do analizy

---

## Wsparcie

Jeśli napotkasz problemy, które nie są opisane w tym przewodniku:

1. **Sprawdź dokumentację:**
   - `docs/PROJECT_STATUS.md` - Status projektu i znane problemy
   - `docs/TESTING.md` - Przewodnik testowania
   - `docs/CONFIGURATION.md` - Przewodnik konfiguracji

2. **Sprawdź logi:**
   - Logi instalacji są wyświetlane w terminalu
   - Logi serwisów: `sudo journalctl -u <nazwa_serwisu>`
   - Logi Docker: `docker compose logs`

3. **Uruchom testy diagnostyczne:**
   - `./health_check.sh` na każdej maszynie
   - `./hosts/shared/test_connections.sh`
   - `./hosts/shared/test_data_flow.sh`

---

## Podsumowanie

Ten przewodnik poprowadził Cię przez:
- ✅ Przygotowanie środowiska
- ✅ Instalację na wszystkich maszynach
- ✅ Konfigurację systemu
- ✅ Weryfikację instalacji
- ✅ Użycie wszystkich dostępnych narzędzi
- ✅ Rozwiązywanie problemów

System jest teraz gotowy do użycia! Możesz rozpocząć threat hunting i analizę danych.

**Powodzenia!** 🎉

