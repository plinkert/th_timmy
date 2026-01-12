# Management Dashboard - n8n Workflow

## Opis

Management Dashboard to podstawowy workflow n8n do zarządzania systemem Threat Hunting Lab. Dashboard zapewnia centralny interfejs do monitorowania i zarządzania wszystkimi komponentami systemu.

## Funkcjonalności

### 1. System Overview
- **Status wszystkich 4 VM** - wyświetlanie statusu zdrowia każdego VM w formie kart z kolorami:
  - 🟢 Zielony - VM zdrowy (healthy)
  - 🟡 Żółty - VM w stanie degraded
  - 🔴 Czerwony - VM niezdrowy (unhealthy)
- **Metryki systemowe** - wyświetlanie metryk dla każdego VM:
  - CPU usage (%)
  - Memory usage (%)
  - Disk usage (%)
- **Automatyczne odświeżanie** - status jest automatycznie odświeżany co 5 minut

### 2. Health Monitoring
- **Automatyczne health checks** - scheduled trigger uruchamia health checks co 5 minut
- **Integracja z Health Monitor Service** - używa `HealthMonitor` (PHASE0-04) do sprawdzania zdrowia VM
- **Alerty** - automatyczne alerty w przypadku problemów ze zdrowiem VM

### 3. Repository Sync
- **Przycisk synchronizacji** - ręczne uruchomienie synchronizacji repozytorium
- **Synchronizacja do wszystkich VM** - używa `RepoSyncService` (PHASE0-02)
- **Status synchronizacji** - wyświetlanie wyniku operacji synchronizacji

### 4. Configuration Management
- **Wyświetlanie konfiguracji** - możliwość przeglądania centralnej konfiguracji
- **Edycja konfiguracji** - możliwość aktualizacji konfiguracji przez dashboard
- **Walidacja** - automatyczna walidacja przed zapisem zmian
- **Backup** - automatyczne tworzenie backupu przed zmianami

### 5. Quick Actions
- **Health Checks** - ręczne uruchomienie health check dla wybranego VM
- **Testy połączeń** - testowanie łączności między VM
- **Status serwisów** - sprawdzanie statusu serwisów (PostgreSQL, JupyterLab, n8n, Docker)

## Instalacja

### 1. Import workflow do n8n

1. Zaloguj się do n8n (domyślnie: http://VM04_IP:5678)
2. Przejdź do **Workflows** → **Import from File**
3. Wybierz plik `management-dashboard.json`
4. Kliknij **Import**

### 2. Konfiguracja

Po zaimportowaniu workflow, skonfiguruj następujące elementy:

#### API Endpoints

Workflow wymaga, aby API serwisy były dostępne. Upewnij się, że:

1. **Remote Execution API** jest uruchomione:
   ```bash
   # Na VM04
   cd /home/thadmin/th_timmy
   uvicorn automation-scripts.api.remote_api:app --host 0.0.0.0 --port 8000
   ```

2. **Health Monitor Service** jest dostępny przez API (można dodać endpointy w przyszłości)

3. **Repository Sync Service** jest dostępny przez API (można dodać endpointy w przyszłości)

#### Konfiguracja Webhook URLs

Workflow używa webhooków n8n. Po aktywacji workflow, n8n wygeneruje unikalne URL-e dla każdego webhooka. Zaktualizuj je w dashboard UI jeśli potrzebne.

#### Konfiguracja Authentication

Jeśli API wymaga autentykacji (API key), skonfiguruj ją w węzłach HTTP Request:
1. Otwórz węzeł HTTP Request
2. W sekcji **Authentication** wybierz **Header Auth**
3. Ustaw:
   - **Name**: `Authorization`
   - **Value**: `Bearer YOUR_API_KEY`

## Użycie

### Dostęp do Dashboard

1. Aktywuj workflow w n8n
2. Otwórz webhook URL dla "Dashboard UI" (np. `http://VM04_IP:5678/webhook/dashboard`)
3. Dashboard zostanie wyświetlony w przeglądarce

### Automatyczne Health Checks

Workflow automatycznie uruchamia health checks co 5 minut. Możesz zmienić interwał w węźle "Schedule Health Check":
- Otwórz węzeł
- Zmień wartość `minutesInterval` w parametrach

### Ręczne operacje

#### Synchronizacja repozytorium

1. Kliknij przycisk **"Sync Repository"** w dashboard
2. Lub wyślij POST request do webhooka:
   ```bash
   curl -X POST http://VM04_IP:5678/webhook/sync-repository \
     -H "Content-Type: application/json" \
     -d '{}'
   ```

#### Sprawdzenie statusu zdrowia

1. Kliknij przycisk **"Refresh Status"** w dashboard
2. Lub wyślij POST request do webhooka:
   ```bash
   curl -X POST http://VM04_IP:5678/webhook/get-health-status \
     -H "Content-Type: application/json" \
     -d '{"vm_id": "vm01"}'
   ```

## Integracja z serwisami

Dashboard integruje się z następującymi serwisami:

### PHASE0-01: Remote Execution Service
- **Endpoint**: `POST /execute-command`
- **Użycie**: Wykonywanie komend na zdalnych VM
- **Przykład**: Health checks, testy połączeń

### PHASE0-02: Repository Sync Service
- **Funkcja**: `sync_repository_to_all_vms()`
- **Użycie**: Synchronizacja repozytorium Git na wszystkich VM
- **Status**: Obecnie przez bezpośrednie wywołanie (można dodać API endpoint)

### PHASE0-03: Configuration Manager
- **Funkcje**: `get_config()`, `update_config()`, `validate_config()`
- **Użycie**: Zarządzanie konfiguracją systemu
- **Status**: Obecnie przez bezpośrednie wywołanie (można dodać API endpoint)

### PHASE0-04: Health Monitor
- **Funkcje**: `check_vm_health()`, `get_health_status_all()`, `collect_metrics()`
- **Użycie**: Monitoring zdrowia VM i zbieranie metryk
- **Status**: Obecnie przez bezpośrednie wywołanie (można dodać API endpoint)

## Struktura workflow

Workflow składa się z następujących węzłów:

1. **Schedule Health Check** - Trigger uruchamiający się co 5 minut
2. **Get All VM Status** - Zbieranie statusu wszystkich VM
3. **Set VM Status** - Przygotowanie danych statusu
4. **Dashboard UI** - Webhook wyświetlający interfejs użytkownika
5. **Get Health Status** - Webhook do ręcznego sprawdzania statusu
6. **Sync Repository** - Webhook do synchronizacji repozytorium
7. **Execute Command** - Wykonywanie komend przez API
8. **Respond nodes** - Odpowiedzi HTTP dla webhooków

## Rozszerzanie

### Dodawanie nowych funkcji

1. Dodaj nowy webhook node dla nowej funkcji
2. Dodaj HTTP Request node do komunikacji z API
3. Dodaj przycisk w dashboard UI
4. Zaktualizuj JavaScript w dashboard do obsługi nowej funkcji

### Dodawanie nowych metryk

1. Rozszerz węzeł "Get All VM Status" o nowe metryki
2. Zaktualizuj template HTML w "Respond Dashboard" o wyświetlanie nowych metryk

## Troubleshooting

### Dashboard nie ładuje się

1. Sprawdź, czy workflow jest aktywowany w n8n
2. Sprawdź, czy webhook URL jest poprawny
3. Sprawdź logi n8n pod kątem błędów

### Health checks nie działają

1. Sprawdź, czy API jest uruchomione i dostępne
2. Sprawdź konfigurację authentication w węzłach HTTP Request
3. Sprawdź, czy VM są dostępne przez SSH

### Synchronizacja repozytorium nie działa

1. Sprawdź, czy repozytorium Git jest skonfigurowane na wszystkich VM
2. Sprawdź uprawnienia SSH do zdalnych VM
3. Sprawdź logi w n8n i w serwisach

## Bezpieczeństwo

⚠️ **UWAGA**: Dashboard obecnie nie ma pełnej autentykacji. W środowisku produkcyjnym:

1. Skonfiguruj n8n z Basic Auth lub OAuth
2. Dodaj API key authentication do wszystkich endpointów
3. Ogranicz dostęp do dashboard tylko dla autoryzowanych użytkowników
4. Użyj HTTPS zamiast HTTP

## Testing Management Workflow

### Instalacja

1. Importuj workflow `testing-management.json` do n8n
2. Aktywuj workflow
3. Dostęp do dashboard: `http://VM04_IP:5678/webhook/testing-dashboard`

### Funkcjonalności

- **Connection Tests**: Uruchamianie `test_connections.sh` zdalnie
- **Data Flow Tests**: Uruchamianie `test_data_flow.sh` zdalnie
- **Health Checks**: Uruchamianie `health_check.sh` na wszystkich VM
- **Test Results**: Wyświetlanie wyników testów w dashboardzie
- **Test History**: Historia wszystkich testów

### Webhook Endpoints

- `POST /webhook/run-connection-tests` - Uruchom testy połączeń
- `POST /webhook/run-data-flow-tests` - Uruchom testy przepływu danych
- `POST /webhook/run-health-checks` - Uruchom health checks na wszystkich VM
- `GET /webhook/test-results` - Pobierz wyniki testów
- `GET /webhook/test-history` - Pobierz historię testów
- `GET /webhook/testing-dashboard` - Dashboard zarządzania testami

## Deployment Management Workflow

### Instalacja

1. Importuj workflow `deployment-management.json` do n8n
2. Aktywuj workflow
3. Dostęp do dashboard: `http://VM04_IP:5678/webhook/deployment-dashboard`

### Funkcjonalności

- **Installation Status**: Status instalacji na wszystkich VM
- **Run Installation**: Uruchamianie `install_vmXX.sh` zdalnie
- **Installation Logs**: Wyświetlanie logów instalacji
- **Deployment Verification**: Weryfikacja po instalacji

### Webhook Endpoints

- `GET /webhook/installation-status` - Pobierz status instalacji wszystkich VM
- `POST /webhook/run-installation` - Uruchom instalację na wybranym VM
- `GET /webhook/installation-logs` - Pobierz logi instalacji
- `POST /webhook/verify-deployment` - Zweryfikuj deployment na VM
- `GET /webhook/deployment-dashboard` - Dashboard zarządzania deploymentem

### Użycie

#### Sprawdzenie statusu instalacji

```bash
curl http://VM04_IP:5678/webhook/installation-status
```

#### Uruchomienie instalacji

```bash
curl -X POST http://VM04_IP:5678/webhook/run-installation \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "vm01"}'
```

#### Weryfikacja deploymentu

```bash
curl -X POST http://VM04_IP:5678/webhook/verify-deployment \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "vm01"}'
```

## Przyszłe ulepszenia

- [ ] Dodanie API endpointów dla wszystkich serwisów
- [ ] Pełna autentykacja i autoryzacja
- [ ] Więcej metryk i wykresów
- [ ] Historia zmian i logi
- [ ] Powiadomienia (email, Slack, etc.)
- [ ] Automatyczne akcje naprawcze
- [ ] Eksport raportów
- [ ] Zaplanowane testy (scheduled tests)
- [ ] Porównywanie wyników testów (before/after)

## Wsparcie

W przypadku problemów:
1. Sprawdź dokumentację n8n: https://docs.n8n.io
2. Sprawdź logi n8n: `docker logs n8n`
3. Sprawdź logi serwisów w `logs/` directory
4. Sprawdź wyniki testów w `test_results/` directory

