# Plan Implementacji PHASE1-01: Rozszerzenie struktury playbooków o zapytania w YAML

## Cel
Rozszerzenie struktury playbooków o zapytania w YAML, aby każdy playbook zawierał zapytania per narzędzie i per tryb (manual/API), ułatwiając pracę osobom nietechnicznym.

## Założenia

### 1. User-Friendly Design
- **Proste nazewnictwo**: Czytelne nazwy narzędzi i trybów
- **Opisy**: Każde zapytanie ma opis co robi i jak używać
- **Przykłady**: Konkretne przykłady użycia
- **Walidacja**: Automatyczna walidacja struktury

### 2. Struktura Zapytań
- **Per narzędzie**: Każde narzędzie (Microsoft Defender, Splunk, Sentinel, etc.) ma swoje zapytania
- **Per tryb**: Dwa tryby wykonania:
  - **manual**: Zapytanie do ręcznego wykonania w interfejsie narzędzia
  - **api**: Zapytanie do automatycznego wykonania przez API
- **Metadane**: Każde zapytanie zawiera:
  - Nazwę i opis
  - Parametry (time_range, filters, etc.)
  - Oczekiwane pola wynikowe
  - Instrukcje użycia

### 3. Integracja z Systemem
- **Synchronizacja**: Playbooki synchronizowane przez PHASE0-02 (repo sync)
- **Query Generator**: Przygotowanie do PHASE1-02 (Query Generator)
- **Dashboard**: Przygotowanie do integracji z Management Dashboard

## Struktura metadata.yml

### Obecna struktura (bazowa)
```yaml
playbook:
  id: "TEMPLATE-playbook-name"
  name: "Playbook Name"
  version: "1.0.0"
  author: "Your Name"
  created: "2025-01-XX"
  updated: "2025-01-XX"

mitre:
  technique_id: "T####"
  technique_name: "Technique Name"
  tactic: "Tactic Name"
  sub_techniques: []

hypothesis: |
  Your hypothesis statement here.

data_sources:
  - name: "Source Name"
    type: "EDR|SIEM|Cloud|OS"
    required: true
```

### Rozszerzona struktura (z zapytaniami)
```yaml
playbook:
  id: "TEMPLATE-playbook-name"
  name: "Playbook Name"
  version: "1.0.0"
  author: "Your Name"
  created: "2025-01-XX"
  updated: "2025-01-XX"

mitre:
  technique_id: "T####"
  technique_name: "Technique Name"
  tactic: "Tactic Name"
  sub_techniques: []

hypothesis: |
  Your hypothesis statement here.

data_sources:
  - name: "Microsoft Defender"
    type: "EDR"
    required: true
    queries:
      manual:
        - name: "Basic Detection Query"
          description: "Query to detect suspicious process execution"
          file: "queries/microsoft_defender_manual.kql"
          parameters:
            time_range: "7d"
            severity: "high"
          expected_fields:
            - TimeGenerated
            - DeviceName
            - ProcessName
            - ProcessCommandLine
          instructions: |
            1. Open Microsoft Defender Advanced Hunting
            2. Paste the query from queries/microsoft_defender_manual.kql
            3. Adjust time_range parameter if needed
            4. Click "Run query"
            5. Export results as CSV
      api:
        - name: "API Detection Query"
          description: "Query for automated execution via Defender API"
          file: "queries/microsoft_defender_api.kql"
          parameters:
            time_range: "7d"
            severity: "high"
          api_endpoint: "https://api.security.microsoft.com/v1.0/advancedHunting/run"
          api_method: "POST"
          expected_fields:
            - TimeGenerated
            - DeviceName
            - ProcessName
            - ProcessCommandLine
          instructions: |
            This query is designed for automated execution via Microsoft Defender API.
            Use the query_generator service to execute this query programmatically.
```

## Funkcjonalności

### 1. Metadata z Zapytaniami
- **Sekcja data_sources**: Rozszerzona o zapytania per narzędzie
- **Tryby wykonania**: manual i api dla każdego narzędzia
- **Metadane zapytań**: Nazwa, opis, parametry, instrukcje

### 2. Przykładowe Zapytania
- **Microsoft Defender**: KQL queries (manual i API)
- **Microsoft Sentinel**: KQL queries (manual i API)
- **Splunk**: SPL queries (manual i API)
- **Elasticsearch**: JSON queries (manual i API)
- **Generic SIEM**: Text-based queries (manual)

### 3. Dokumentacja
- **README.md**: Zaktualizowany z opisem struktury zapytań
- **Przykłady**: Konkretne przykłady użycia
- **Instrukcje**: Krok po kroku jak używać zapytań

## Plan Implementacji

### Krok 1: Utworzenie metadata.yml z rozszerzoną strukturą
- Rozszerzenie sekcji data_sources o queries
- Dodanie trybów manual i api
- Dodanie metadanych dla każdego zapytania

### Krok 2: Utworzenie przykładowych zapytań
- Microsoft Defender (manual + API)
- Microsoft Sentinel (manual + API)
- Splunk (manual + API)
- Elasticsearch (manual + API)
- Generic SIEM (manual)

### Krok 3: Aktualizacja dokumentacji
- README.md playbook template
- Przykłady użycia
- Instrukcje dla użytkowników nietechnicznych

### Krok 4: Walidacja
- Sprawdzenie struktury YAML
- Sprawdzenie dostępności plików zapytań
- Testowanie czytelności dla użytkowników nietechnicznych

## Korzyści

1. **Dla użytkowników nietechnicznych**:
   - Proste instrukcje krok po kroku
   - Gotowe zapytania do skopiowania
   - Opisy co każde zapytanie robi

2. **Dla systemu**:
   - Przygotowanie do Query Generator (PHASE1-02)
   - Automatyczne wykrywanie dostępnych zapytań
   - Integracja z Management Dashboard

3. **Dla deweloperów**:
   - Standaryzowana struktura
   - Łatwe rozszerzanie o nowe narzędzia
   - Walidacja struktury

## Następne kroki (po PHASE1-01)

- PHASE1-02: Query Generator - automatyczne generowanie zapytań
- PHASE1-04: n8n UI - formularz wyboru hunt z zapytaniami
- PHASE1-07: Playbook Management Interface - zarządzanie playbookami z dashboardu

