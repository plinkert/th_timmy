# Przewodnik po Narzędziach - Threat Hunting Automation Lab

**Wersja**: 1.0  
**Dla**: Użytkowników nietechnicznych

Ten przewodnik opisuje wszystkie dostępne narzędzia w systemie, do czego służą i jak ich używać krok po kroku.

---

## Spis Treści

1. [Narzędzia zarządzania (n8n)](#narzędzia-zarządzania-n8n)
2. [Narzędzia analizy (JupyterLab)](#narzędzia-analizy-jupyterlab)
3. [Narzędzia wiersza poleceń](#narzędzia-wiersza-poleceń)
4. [Narzędzia serwisowe (API)](#narzędzia-serwisowe-api)
5. [Kiedy używać którego narzędzia?](#kiedy-używać-którego-narzędzia)

---

## Narzędzia zarządzania (n8n)

Wszystkie narzędzia zarządzania są dostępne przez n8n - platformę automatyzacji workflow. Dostęp do n8n: `http://<VM-04_IP>:5678`

### 1. Management Dashboard

**Co to jest:** Główny panel kontrolny całego systemu.

**Gdzie:** n8n → Workflow "Management Dashboard" → Webhook "Dashboard UI"

**Do czego służy:**
- Monitorowanie statusu wszystkich maszyn w czasie rzeczywistym
- Wyświetlanie metryk systemowych (CPU, RAM, dysk)
- Szybkie akcje (synchronizacja, health checks)
- Zarządzanie konfiguracją

**Jak używać - krok po kroku:**

1. **Zaloguj się do n8n:**
   ```
   Otwórz przeglądarkę → http://<VM-04_IP>:5678
   Wpisz nazwę użytkownika i hasło
   Kliknij "Sign In"
   ```

2. **Znajdź Management Dashboard:**
   ```
   W menu po lewej kliknij "Workflows"
   Znajdź "Management Dashboard" na liście
   Kliknij na niego, aby otworzyć
   ```

3. **Aktywuj workflow (jeśli nie jest aktywny):**
   ```
   W prawym górnym rogu znajdź przełącznik "Active"
   Kliknij, aby go włączyć (powinien być zielony)
   ```

4. **Otwórz dashboard:**
   ```
   W workflow znajdź węzeł "Dashboard UI" (zwykle na końcu)
   Kliknij na niego
   W sekcji "Webhook URL" skopiuj adres URL
   Otwórz ten URL w nowej karcie przeglądarki
   ```

5. **Używanie dashboardu:**
   - **System Overview:**
     - Widzisz 4 karty - po jednej dla każdej maszyny
     - Kolor karty oznacza status:
       - 🟢 Zielony = wszystko działa prawidłowo
       - 🟡 Żółty = są problemy, ale maszyna działa
       - 🔴 Czerwony = maszyna nie działa
   - **Metryki:**
     - Pod każdą kartą widzisz:
       - CPU Usage: użycie procesora (w %)
       - Memory Usage: użycie pamięci (w %)
       - Disk Usage: użycie dysku (w %)
   - **Przyciski akcji:**
     - "Sync Repository" - synchronizuje kod na wszystkich maszynach
     - "Refresh Status" - odświeża status wszystkich maszyn
     - "Run Health Check" - uruchamia szczegółowe sprawdzenie wybranej maszyny

**Przykład użycia:**

```
Scenariusz: Chcesz sprawdzić, czy wszystkie maszyny działają prawidłowo

1. Otwórz Management Dashboard
2. Sprawdź kolory kart - wszystkie powinny być zielone
3. Jeśli któraś karta jest żółta lub czerwona:
   a. Kliknij na nią
   b. Sprawdź metryki - może być problem z pamięcią lub dyskiem
   c. Kliknij "Run Health Check"
   d. Poczekaj na wyniki (1-2 minuty)
   e. Przeczytaj raport - pokaże, co jest nie tak
```

**Częstotliwość użycia:** Codziennie lub kilka razy dziennie, aby monitorować system.

---

### 2. Testing Management Interface

**Co to jest:** Interfejs do uruchamiania i zarządzania testami systemu.

**Gdzie:** n8n → Workflow "Testing Management" → Webhook "Testing Dashboard"

**Do czego służy:**
- Testowanie połączeń między maszynami
- Testowanie przepływu danych
- Sprawdzanie zdrowia maszyn
- Przeglądanie historii testów

**Jak używać - krok po kroku:**

1. **Otwórz Testing Management:**
   ```
   W n8n → Workflows → "Testing Management"
   Upewnij się, że workflow jest aktywny
   ```

2. **Otwórz dashboard testów:**
   ```
   Znajdź węzeł "Testing Dashboard"
   Skopiuj URL webhooka
   Otwórz w przeglądarce
   ```

3. **Uruchom testy połączeń:**
   ```
   Kliknij przycisk "Run Connection Tests"
   Poczekaj 1-2 minuty
   Zobaczysz wyniki:
     ✅ PASS - test przeszedł pomyślnie
     ❌ FAIL - test nie przeszedł
     ⚠️ WARN - test przeszedł, ale z ostrzeżeniami
   ```

4. **Uruchom testy przepływu danych:**
   ```
   PRZED uruchomieniem: Ustaw hasło do bazy danych
   W terminalu (na maszynie, z której uruchamiasz):
     export POSTGRES_PASSWORD="TwojeHaslo"
   
   W dashboardzie kliknij "Run Data Flow Tests"
   Poczekaj 2-3 minuty
   Sprawdź wyniki
   ```

5. **Uruchom health checks:**
   ```
   Kliknij "Run Health Checks"
   Wybierz maszynę (lub "All VMs")
   Poczekaj 2-5 minut
   Zobaczysz szczegółowy raport dla każdej maszyny
   ```

6. **Przeglądaj historię testów:**
   ```
   Kliknij "View Test History"
   Zobaczysz listę wszystkich wykonanych testów
   Możesz kliknąć na test, aby zobaczyć szczegóły
   ```

**Kiedy używać:**
- Po instalacji systemu (weryfikacja, że wszystko działa)
- Po zmianach w konfiguracji
- Gdy coś nie działa (diagnostyka)
- Regularnie (np. raz w tygodniu) jako kontrola prewencyjna

**Przykład użycia:**

```
Scenariusz: Po instalacji chcesz upewnić się, że wszystko działa

1. Otwórz Testing Management Dashboard
2. Kliknij "Run Connection Tests"
3. Sprawdź wyniki - wszystkie powinny być ✅ PASS
4. Jeśli są błędy:
   a. Zapisz, które testy nie przeszły
   b. Sprawdź konfigurację (adresy IP, porty)
   c. Sprawdź firewall
5. Kliknij "Run Data Flow Tests"
6. Sprawdź wyniki - powinny być ✅ PASS
7. Jeśli są błędy:
   a. Sprawdź, czy baza danych działa
   b. Sprawdź hasło do bazy danych
   c. Sprawdź logi
```

---

### 3. Deployment Management Interface

**Co to jest:** Interfejs do zarządzania instalacjami i wdrożeniami.

**Gdzie:** n8n → Workflow "Deployment Management" → Webhook "Deployment Dashboard"

**Do czego służy:**
- Sprawdzanie statusu instalacji na maszynach
- Uruchamianie instalacji zdalnie (bez logowania na maszynę)
- Przeglądanie logów instalacji
- Weryfikacja wdrożeń

**Jak używać - krok po kroku:**

1. **Otwórz Deployment Management:**
   ```
   W n8n → Workflows → "Deployment Management"
   Upewnij się, że workflow jest aktywny
   ```

2. **Otwórz dashboard:**
   ```
   Znajdź węzeł "Deployment Dashboard"
   Skopiuj URL webhooka
   Otwórz w przeglądarce
   ```

3. **Sprawdź status instalacji:**
   ```
   Kliknij "Get Installation Status"
   Zobaczysz tabelę z statusem dla każdej maszyny:
     ✅ Installed - maszyna jest zainstalowana
     ❌ Not Installed - maszyna nie jest zainstalowana
     ⚠️ Unknown - nie można sprawdzić
   ```

4. **Uruchom instalację na maszynie:**
   ```
   Wybierz maszynę z listy (np. "vm01")
   Kliknij "Run Installation"
   Wypełnij formularz:
     - Project Root: /home/twoja_nazwa_uzytkownika/th_timmy
     - Config File: (zostaw puste, jeśli używasz domyślnego)
   Kliknij "Start Installation"
   ```

5. **Monitoruj postęp:**
   ```
   Zobaczysz postęp instalacji w czasie rzeczywistym
   Możesz kliknąć "View Logs", aby zobaczyć szczegółowe logi
   Poczekaj na zakończenie (może zająć 10-20 minut)
   ```

6. **Zweryfikuj instalację:**
   ```
   Po zakończeniu kliknij "Verify Deployment"
   Wybierz maszynę
   System sprawdzi, czy instalacja się powiodła
   Zobaczysz raport weryfikacji
   ```

**Kiedy używać:**
- Podczas pierwszej instalacji systemu
- Gdy musisz ponownie zainstalować maszynę
- Gdy aktualizujesz oprogramowanie
- Gdy sprawdzasz, czy wszystko jest zainstalowane

**Przykład użycia:**

```
Scenariusz: Musisz ponownie zainstalować VM-01

1. Otwórz Deployment Management Dashboard
2. Kliknij "Get Installation Status"
3. Sprawdź status VM-01 - może być "Not Installed" lub "Unknown"
4. Kliknij "Run Installation"
5. Wybierz "vm01" z listy
6. Wypełnij formularz:
   - Project Root: /home/user/th_timmy
7. Kliknij "Start Installation"
8. Monitoruj postęp - zobaczysz logi w czasie rzeczywistym
9. Po zakończeniu kliknij "Verify Deployment"
10. Sprawdź raport - powinien pokazać ✅ wszystkie testy PASS
```

---

### 4. Hardening Management Interface

**Co to jest:** Interfejs do zarządzania zabezpieczeniami maszyn.

**Gdzie:** n8n → Workflow "Hardening Management" → Webhook "Hardening Dashboard"

**Do czego służy:**
- Sprawdzanie statusu zabezpieczeń maszyn
- Uruchamianie procesu zabezpieczania (hardening)
- Porównywanie stanu przed/po zabezpieczeniu
- Przeglądanie raportów zabezpieczeń

**Jak używać - krok po kroku:**

1. **Otwórz Hardening Management:**
   ```
   W n8n → Workflows → "Hardening Management"
   Upewnij się, że workflow jest aktywny
   ```

2. **Otwórz dashboard:**
   ```
   Znajdź węzeł "Hardening Dashboard"
   Skopiuj URL webhooka
   Otwórz w przeglądarce
   ```

3. **Sprawdź status zabezpieczeń:**
   ```
   Kliknij "Get Hardening Status"
   Zobaczysz status dla każdej maszyny:
     ✅ Hardened - maszyna jest w pełni zabezpieczona
     ⚠️ Partial - maszyna jest częściowo zabezpieczona
     ❌ Not Hardened - maszyna nie jest zabezpieczona
     ❓ Unknown - nie można sprawdzić statusu
   ```

4. **PRZED uruchomieniem hardeningu - wykonaj testy:**
   ```
   WAŻNE: Zawsze wykonaj testy przed hardeningiem!
   
   W Testing Management Dashboard:
   1. Kliknij "Run Connection Tests"
   2. Kliknij "Run Data Flow Tests"
   3. Zapisz wyniki - będą punktem odniesienia
   ```

5. **Uruchom hardening:**
   ```
   W Hardening Dashboard:
   1. Wybierz maszynę (np. "vm01")
   2. Kliknij "Run Hardening"
   3. WAŻNE: Zaznacz "Capture Before State"
      (zapisze stan przed zabezpieczeniem)
   4. Kliknij "Start"
   5. Poczekaj 5-10 minut (zależy od maszyny)
   ```

6. **Porównaj przed/po:**
   ```
   Po zakończeniu:
   1. Kliknij "Compare Before/After"
   2. Wybierz ID zabezpieczenia (zostanie wyświetlone po zakończeniu)
   3. Wybierz maszynę
   4. Kliknij "Compare"
   5. Zobaczysz różnice:
      - Co zostało zmienione
      - Jakie porty zostały zamknięte
      - Jakie ustawienia zostały zmienione
   ```

7. **Zweryfikuj, że wszystko działa:**
   ```
   Po hardeningu:
   1. Wróć do Testing Management Dashboard
   2. Uruchom testy ponownie
   3. Porównaj wyniki z testami sprzed hardeningu
   4. Wszystkie testy powinny nadal przechodzić
   ```

**Kiedy używać:**
- Po instalacji systemu (zabezpieczenie przed użyciem)
- Gdy chcesz zwiększyć bezpieczeństwo
- Gdy musisz spełnić wymagania bezpieczeństwa (np. compliance)
- Regularnie (np. raz na kwartał) jako kontrola

**UWAGA:** Po zabezpieczeniu, niektóre porty mogą być zablokowane. Upewnij się, że masz dostęp do maszyn przez SSH!

**Przykład użycia:**

```
Scenariusz: Chcesz zabezpieczyć wszystkie maszyny po instalacji

1. PRZED hardeningiem:
   a. Otwórz Testing Management Dashboard
   b. Uruchom wszystkie testy
   c. Zapisz wyniki (zrób screenshot lub zapisz w notatniku)

2. Otwórz Hardening Management Dashboard

3. Dla każdej maszyny (vm01, vm02, vm03, vm04):
   a. Kliknij "Get Hardening Status"
   b. Sprawdź status - prawdopodobnie będzie "Not Hardened"
   c. Kliknij "Run Hardening"
   d. Zaznacz "Capture Before State"
   e. Kliknij "Start"
   f. Poczekaj na zakończenie (5-10 minut)
   g. Zapisz ID zabezpieczenia

4. PO hardeningu wszystkich maszyn:
   a. Wróć do Testing Management Dashboard
   b. Uruchom wszystkie testy ponownie
   c. Porównaj wyniki - powinny być takie same jak przed hardeningiem
   d. Jeśli testy nie przechodzą:
      - Sprawdź firewall (może być zbyt restrykcyjny)
      - Sprawdź logi hardeningu
      - Skontaktuj się z administratorem

5. Porównaj przed/po:
   a. W Hardening Dashboard kliknij "Compare Before/After"
   b. Wybierz ID zabezpieczenia
   c. Zobacz, co zostało zmienione
```

---

### 5. Playbook Manager

**Co to jest:** Interfejs do zarządzania playbookami (skryptami analizy zagrożeń).

**Gdzie:** n8n → Workflow "Playbook Manager" → Webhook "Playbook Dashboard"

**Do czego służy:**
- Przeglądanie dostępnych playbooków
- Tworzenie nowych playbooków
- Edycja istniejących playbooków
- Walidacja playbooków (sprawdzanie, czy są poprawne)
- Testowanie playbooków

**Co to jest playbook?**
Playbook to gotowy skrypt do analizy konkretnego zagrożenia. Zawiera:
- Opis zagrożenia (np. "Phishing emails")
- Technikę MITRE ATT&CK (np. T1566)
- Zapytania dla różnych narzędzi (Splunk, Sentinel, itp.)
- Logikę analizy

**Jak używać - krok po kroku:**

1. **Otwórz Playbook Manager:**
   ```
   W n8n → Workflows → "Playbook Manager"
   Upewnij się, że workflow jest aktywny
   ```

2. **Otwórz dashboard:**
   ```
   Znajdź węzeł "Playbook Dashboard"
   Skopiuj URL webhooka
   Otwórz w przeglądarce
   ```

3. **Przeglądaj dostępne playbooki:**
   ```
   Kliknij "List Playbooks"
   Zobaczysz tabelę z wszystkimi playbookami:
     - Nazwa
     - Opis
     - MITRE Technique ID
     - Status (Valid/Invalid)
     - Data ostatniej modyfikacji
   ```

4. **Zobacz szczegóły playbooka:**
   ```
   Kliknij na playbook w tabeli
   Zobaczysz szczegóły:
     - Pełny opis
     - Wszystkie zapytania
     - Konfiguracja
   ```

5. **Utwórz nowy playbook:**
   ```
   Kliknij "Create New Playbook"
   Wypełnij formularz:
     
     Nazwa: "Phishing Detection"
     Opis: "Detects phishing emails and malicious links"
     MITRE Technique ID: "T1566"
     
     Zapytania:
       Splunk: "index=security sourcetype=email | search ..."
       Sentinel: "EmailEvents | where ..."
       Defender: "DeviceEvents | where ..."
   
   Kliknij "Create"
   System automatycznie zwaliduje playbook
   ```

6. **Edytuj istniejący playbook:**
   ```
   Wybierz playbook z listy
   Kliknij "Edit"
   Zmień potrzebne pola
   Kliknij "Save"
   System zwaliduje zmiany
   ```

7. **Zweryfikuj playbook:**
   ```
   Wybierz playbook
   Kliknij "Validate"
   System sprawdzi:
     - Czy struktura jest poprawna
     - Czy zapytania są poprawne
     - Czy wszystkie wymagane pola są wypełnione
   Zobaczysz raport walidacji
   ```

**Kiedy używać:**
- Gdy chcesz stworzyć nowy playbook do analizy konkretnego zagrożenia
- Gdy musisz zaktualizować istniejący playbook
- Gdy chcesz sprawdzić, czy playbook jest poprawny
- Gdy chcesz zobaczyć, jakie playbooki są dostępne

**Przykład użycia:**

```
Scenariusz: Chcesz stworzyć playbook do wykrywania ransomware

1. Otwórz Playbook Manager Dashboard
2. Kliknij "Create New Playbook"
3. Wypełnij formularz:
   - Nazwa: "Ransomware Detection"
   - Opis: "Detects ransomware activity based on file encryption patterns"
   - MITRE Technique ID: "T1486" (Data Encrypted for Impact)
4. Dodaj zapytania dla swoich narzędzi:
   - Splunk: (zapytanie do Splunka)
   - Sentinel: (zapytanie do Sentinel)
   - Defender: (zapytanie do Defender)
5. Kliknij "Create"
6. System zwaliduje playbook
7. Jeśli są błędy, popraw je i zapisz ponownie
8. Playbook jest teraz gotowy do użycia!
```

---

### 6. Hunt Selection Form

**Co to jest:** Formularz do wyboru huntów (polowań na zagrożenia) i generowania zapytań.

**Gdzie:** n8n → Workflow "Hunt Selection Form" → Webhook "Hunt Selection Form"

**Do czego służy:**
- Wybór technik MITRE ATT&CK do analizy
- Wybór dostępnych narzędzi (Splunk, Sentinel, itp.)
- Automatyczne generowanie zapytań dla wybranych huntów
- Uruchamianie analizy

**Jak używać - krok po kroku:**

1. **Otwórz Hunt Selection Form:**
   ```
   W n8n → Workflows → "Hunt Selection Form"
   Upewnij się, że workflow jest aktywny
   ```

2. **Otwórz formularz:**
   ```
   Znajdź węzeł "Hunt Selection Form"
   Skopiuj URL webhooka
   Otwórz w przeglądarce
   ```

3. **Wypełnij formularz:**
   
   **Krok 3.1: Wybierz techniki MITRE ATT&CK**
   ```
   Zobaczysz listę technik MITRE ATT&CK
   Zaznacz checkboxy przy technikach, które chcesz analizować
   Przykłady:
     ☑ T1566 - Phishing
     ☑ T1059 - Command and Scripting Interpreter
     ☑ T1078 - Valid Accounts
   
   Możesz wybrać wiele technik
   ```

   **Krok 3.2: Wybierz dostępne narzędzia**
   ```
   Zaznacz narzędzia, które masz dostępne:
     ☑ Splunk
     ☑ Microsoft Sentinel
     ☑ Microsoft Defender
     ☑ Generic SIEM
   
   Wybierz tylko te, które rzeczywiście masz
   ```

   **Krok 3.3: Wybierz tryb ingestu**
   ```
   Wybierz, jak chcesz wgrać dane:
     ○ Manual - ręczne wgranie plików CSV/JSON
     ● API - automatyczne pobieranie przez API
   
   Jeśli nie masz API, wybierz "Manual"
   ```

4. **Wygeneruj zapytania:**
   ```
   Kliknij "Generate Queries"
   System automatycznie wygeneruje zapytania dla:
     - Każdej wybranej techniki
     - Każdego wybranego narzędzia
   
   Zobaczysz listę zapytań
   Każde zapytanie ma:
     - Nazwę (np. "T1566 - Splunk Query")
     - Zapytanie (gotowe do skopiowania)
     - Opis
   ```

5. **Skopiuj i użyj zapytań:**
   ```
   Dla każdego zapytania:
   1. Kliknij "Copy" obok zapytania
   2. Otwórz swoje narzędzie (Splunk, Sentinel, itp.)
   3. Wklej zapytanie
   4. Uruchom zapytanie
   5. Zapisz wyniki (eksportuj do CSV lub JSON)
   ```

6. **Wgraj wyniki i uruchom analizę:**
   ```
   Po wykonaniu wszystkich zapytań:
   1. W formularzu kliknij "Upload Results"
   2. Wybierz pliki z wynikami (CSV lub JSON)
   3. Kliknij "Upload"
   4. System automatycznie:
      - Zanonimizuje dane
      - Przetworzy dane
      - Zmapuje dane do odpowiednich playbooków
   5. Kliknij "Start Analysis"
   6. System uruchomi analizę
   7. Poczekaj na wyniki (może zająć kilka minut)
   ```

7. **Przeglądaj wyniki:**
   ```
   Po zakończeniu analizy:
   1. Zobaczysz podsumowanie:
      - Ile znalezisk (findings) zostało znalezionych
      - Jakie techniki zostały wykryte
      - Poziom zagrożenia
   2. Kliknij "View Details", aby zobaczyć szczegóły
   3. Możesz eksportować wyniki do raportu
   ```

**Kiedy używać:**
- Gdy chcesz przeprowadzić threat hunting
- Gdy chcesz sprawdzić konkretne techniki MITRE ATT&CK
- Gdy potrzebujesz gotowych zapytań dla swoich narzędzi SIEM/EDR
- Gdy chcesz zautomatyzować proces analizy

**Przykład użycia:**

```
Scenariusz: Chcesz sprawdzić, czy w Twojej sieci są aktywności phishingowe

1. Otwórz Hunt Selection Form
2. Wypełnij formularz:
   - Techniki: ☑ T1566 (Phishing)
   - Narzędzia: ☑ Splunk, ☑ Microsoft Sentinel
   - Tryb: ○ Manual (nie masz API)
3. Kliknij "Generate Queries"
4. Zobaczysz 2 zapytania:
   - "T1566 - Splunk Query"
   - "T1566 - Sentinel Query"
5. Skopiuj zapytanie Splunk:
   a. Otwórz Splunk
   b. Wklej zapytanie
   c. Uruchom
   d. Eksportuj wyniki do CSV
6. Skopiuj zapytanie Sentinel:
   a. Otwórz Microsoft Sentinel
   b. Wklej zapytanie
   c. Uruchom
   d. Eksportuj wyniki do CSV
7. W formularzu kliknij "Upload Results"
8. Wybierz oba pliki CSV
9. Kliknij "Upload"
10. Kliknij "Start Analysis"
11. Poczekaj na wyniki
12. Przeglądaj znaleziska - system pokaże, co znalazł
```

---

## Narzędzia analizy (JupyterLab)

### JupyterLab

**Co to jest:** Interaktywne środowisko do analizy danych i tworzenia raportów.

**Gdzie:** http://<VM-03_IP>:8888

**Do czego służy:**
- Analiza danych z bazy danych
- Tworzenie wizualizacji (wykresy, grafiki)
- Pisanie i wykonywanie skryptów Python
- Tworzenie raportów
- Eksperymentowanie z danymi

**Jak używać - krok po kroku:**

1. **Uruchom JupyterLab:**
   ```
   Zaloguj się na VM-03 przez SSH
   W terminalu wpisz:
     cd ~/th_timmy
     source venv/bin/activate
     jupyter lab --ip=0.0.0.0 --port=8888
   ```

2. **Skopiuj token:**
   ```
   W terminalu zobaczysz coś takiego:
     [I 2025-01-12 10:00:00.000 LabApp] 
     http://VM-03_IP:8888/lab?token=abc123def456...
   
   Skopiuj token (część po "token=")
   ```

3. **Otwórz JupyterLab w przeglądarce:**
   ```
   Otwórz przeglądarkę
   Przejdź do: http://<VM-03_IP>:8888
   Wklej token, gdy zostaniesz poproszony
   Kliknij "Log in"
   ```

4. **Podstawowe operacje:**
   
   **Utwórz nowy notebook:**
   ```
   W JupyterLab kliknij "New" (w prawym górnym rogu)
   Wybierz "Python 3"
   Zostanie utworzony nowy notebook
   ```

   **Połącz się z bazą danych:**
   ```
   W pierwszej komórce notebooka wpisz:
   
   import psycopg2
   import pandas as pd
   
   conn = psycopg2.connect(
       host="<VM-02_IP>",
       port=5432,
       database="threat_hunting",
       user="threat_hunter",
       password="TwojeHasloDoBazyDanych"
   )
   
   Naciśnij Shift+Enter, aby wykonać komórkę
   ```

   **Wykonaj zapytanie SQL:**
   ```
   W nowej komórce wpisz:
   
   query = "SELECT * FROM normalized_logs LIMIT 100"
   df = pd.read_sql(query, conn)
   df.head()
   
   Naciśnij Shift+Enter
   Zobaczysz pierwsze 100 wierszy danych w tabeli
   ```

   **Stwórz wizualizację:**
   ```
   W nowej komórce wpisz:
   
   import matplotlib.pyplot as plt
   
   # Przykład: wykres liczby zdarzeń w czasie
   df['timestamp'] = pd.to_datetime(df['timestamp'])
   df.groupby(df['timestamp'].dt.date).size().plot()
   plt.title('Liczba zdarzeń w czasie')
   plt.show()
   
   Naciśnij Shift+Enter
   Zobaczysz wykres
   ```

   **Zapisz notebook:**
   ```
   Kliknij "File" → "Save"
   Lub naciśnij Ctrl+S
   ```

**Kiedy używać:**
- Gdy chcesz przeanalizować dane ręcznie
- Gdy chcesz stworzyć własne wizualizacje
- Gdy chcesz eksperymentować z danymi
- Gdy chcesz napisać własne skrypty analizy
- Gdy chcesz stworzyć niestandardowe raporty

**Przykład użycia:**

```
Scenariusz: Chcesz przeanalizować, ile zdarzeń phishingowych było w ostatnim tygodniu

1. Uruchom JupyterLab (patrz wyżej)
2. Utwórz nowy notebook
3. Połącz się z bazą danych (patrz wyżej)
4. Wykonaj zapytanie:
   
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
   
5. Stwórz wykres:
   
   df.plot(x='date', y='count', kind='bar')
   plt.title('Zdarzenia phishingowe w ostatnim tygodniu')
   plt.xlabel('Data')
   plt.ylabel('Liczba zdarzeń')
   plt.show()
   
6. Zapisz notebook
```

---

## Narzędzia wiersza poleceń

Te narzędzia są dostępne z terminala (linii poleceń) na każdej maszynie.

### Health Check

**Co to jest:** Skrypt sprawdzający zdrowie maszyny.

**Gdzie:** Na każdej maszynie: `~/th_timmy/hosts/vmXX-*/health_check.sh`

**Jak używać:**

```bash
# Na VM-01
cd ~/th_timmy/hosts/vm01-ingest
./health_check.sh

# Na VM-02
cd ~/th_timmy/hosts/vm02-database
./health_check.sh

# Na VM-03
cd ~/th_timmy/hosts/vm03-analysis
./health_check.sh

# Na VM-04
cd ~/th_timmy/hosts/vm04-orchestrator
./health_check.sh
```

**Co sprawdza:**
- ✅ Czy wszystkie wymagane programy są zainstalowane
- ✅ Czy serwisy działają (PostgreSQL, JupyterLab, Docker)
- ✅ Czy konfiguracja jest poprawna
- ✅ Czy połączenia sieciowe działają

**Kiedy używać:**
- Po instalacji (weryfikacja)
- Gdy coś nie działa (diagnostyka)
- Regularnie (kontrola)

---

### Test Connections

**Co to jest:** Skrypt testujący połączenia między maszynami.

**Gdzie:** `~/th_timmy/hosts/shared/test_connections.sh`

**Jak używać:**

```bash
# Na dowolnej maszynie
cd ~/th_timmy
./hosts/shared/test_connections.sh
```

**Co sprawdza:**
- ✅ Czy maszyny mogą się pingować
- ✅ Czy porty są otwarte (SSH, PostgreSQL, JupyterLab, n8n)
- ✅ Czy można połączyć się z bazą danych
- ✅ Czy serwisy są dostępne

**Kiedy używać:**
- Po instalacji (weryfikacja połączeń)
- Gdy masz problemy z połączeniem
- Regularnie (kontrola)

---

### Test Data Flow

**Co to jest:** Skrypt testujący przepływ danych przez system.

**Gdzie:** `~/th_timmy/hosts/shared/test_data_flow.sh`

**Jak używać:**

```bash
# Na dowolnej maszynie
cd ~/th_timmy

# Ustaw hasło do bazy danych
export POSTGRES_PASSWORD="TwojeHasloDoBazyDanych"

# Uruchom test
./hosts/shared/test_data_flow.sh
```

**Co sprawdza:**
- ✅ Czy można zapisać dane do bazy danych
- ✅ Czy można odczytać dane z bazy danych
- ✅ Czy n8n jest dostępne
- ✅ Czy przepływ danych działa end-to-end

**Kiedy używać:**
- Po instalacji (weryfikacja przepływu danych)
- Gdy masz problemy z danymi
- Regularnie (kontrola)

---

## Narzędzia serwisowe (API)

Te narzędzia są dostępne przez API (interfejs programistyczny). Są używane głównie przez n8n workflows, ale możesz ich też używać bezpośrednio.

### Dashboard API

**Co to jest:** API do zarządzania systemem.

**Gdzie:** http://<VM-04_IP>:8000 (jeśli uruchomione)

**Do czego służy:**
- Pobieranie statusu systemu
- Zarządzanie konfiguracją
- Synchronizacja repozytorium
- Uruchamianie health checks

**Jak używać:**

```bash
# Przykład: Pobierz status systemu
curl http://<VM-04_IP>:8000/api/system/overview

# Przykład: Uruchom health check
curl -X POST http://<VM-04_IP>:8000/api/health/check \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "vm01"}'
```

**Uwaga:** To narzędzie jest głównie używane przez n8n workflows. Jeśli nie jesteś programistą, prawdopodobnie nie będziesz go używać bezpośrednio.

---

## Kiedy używać którego narzędzia?

### Codzienne monitorowanie

**Użyj:** Management Dashboard
- Sprawdź status wszystkich maszyn
- Sprawdź metryki (CPU, RAM, dysk)
- Uruchom synchronizację repozytorium, jeśli potrzebne

### Weryfikacja po instalacji

**Użyj:**
1. Testing Management Interface - uruchom wszystkie testy
2. Management Dashboard - sprawdź status
3. Health Check (wiersz poleceń) - sprawdź każdą maszynę

### Zabezpieczanie systemu

**Użyj:**
1. Testing Management Interface - wykonaj testy PRZED hardeningiem
2. Hardening Management Interface - uruchom hardening
3. Testing Management Interface - wykonaj testy PO hardeningu
4. Porównaj wyniki

### Przeprowadzanie threat huntingu

**Użyj:**
1. Hunt Selection Form - wybierz techniki i wygeneruj zapytania
2. Wykonaj zapytania w swoich narzędziach SIEM/EDR
3. Hunt Selection Form - wgraj wyniki i uruchom analizę
4. JupyterLab - przeanalizuj wyniki szczegółowo (opcjonalnie)

### Tworzenie nowego playbooka

**Użyj:**
1. Playbook Manager - utwórz nowy playbook
2. Wypełnij formularz
3. System zwaliduje playbook
4. Jeśli są błędy, popraw je

### Diagnostyka problemów

**Użyj:**
1. Management Dashboard - sprawdź status maszyn
2. Testing Management Interface - uruchom testy
3. Health Check (wiersz poleceń) - sprawdź szczegóły
4. Sprawdź logi (wiersz poleceń)

---

## Podsumowanie

Ten przewodnik opisał wszystkie dostępne narzędzia w systemie. Pamiętaj:

- **Management Dashboard** - codzienne monitorowanie
- **Testing Management** - weryfikacja i diagnostyka
- **Deployment Management** - instalacje i wdrożenia
- **Hardening Management** - zabezpieczanie
- **Playbook Manager** - zarządzanie playbookami
- **Hunt Selection Form** - threat hunting
- **JupyterLab** - analiza danych
- **Narzędzia wiersza poleceń** - zaawansowane operacje

Wszystkie narzędzia są zaprojektowane tak, aby były łatwe w użyciu, nawet dla osób nietechnicznych. Jeśli masz pytania, sprawdź dokumentację lub skontaktuj się z administratorem systemu.

**Powodzenia!** 🎉

