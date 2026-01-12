# Plan Implementacji PHASE1-03: Deterministyczna anonimizacja z mapping table

## Cel
Implementacja deterministycznej anonimizacji danych PRZED AI z możliwością deterministycznej deanonymizacji poprzez mapping table.

## Założenia

### 1. Deterministyczna Anonimizacja
- **Ten sam input = ten sam output**: Ta sama wartość zawsze daje tę samą zanonimizowaną wartość
- **Bezpieczeństwo**: Zanonimizowane dane nie mogą być łatwo odwrócone bez mapping table
- **Konsystencja**: Ta sama wartość w różnych miejscach ma tę samą zanonimizowaną wartość

### 2. Mapping Table
- **Przechowywanie**: Mapping table przechowywana w bazie danych PostgreSQL na VM02
- **Struktura**: Tabela `anonymization_mapping` z kolumnami:
  - `id`: Primary key
  - `original_value`: Oryginalna wartość (może być hashowana dla bezpieczeństwa)
  - `anonymized_value`: Zanonimizowana wartość
  - `value_type`: Typ wartości (ip, email, username, hostname, etc.)
  - `created_at`: Timestamp utworzenia
  - `last_used`: Ostatnie użycie
- **Bezpieczeństwo**: Oryginalne wartości mogą być hashowane przed zapisem

### 3. User-Friendly Design
- **Proste API**: Łatwe w użyciu metody anonimizacji i deanonymizacji
- **Automatyczne zarządzanie**: Automatyczne tworzenie wpisów w mapping table
- **Wydajność**: Cache mapping table w pamięci dla szybkiego dostępu
- **Bezpieczeństwo**: Opcjonalne szyfrowanie mapping table

### 4. Integracja z Systemem
- **Przed AI**: Anonimizacja danych przed wysłaniem do AI
- **Po AI**: Deanonymizacja wyników AI przed raportowaniem
- **Baza danych**: Użycie istniejącej bazy na VM02

## Struktura Implementacji

### DeterministicAnonymizer Class

```python
class DeterministicAnonymizer:
    """
    Deterministyczna anonimizacja z mapping table.
    
    Features:
    - Deterministyczna anonimizacja (ten sam input = ten sam output)
    - Mapping table w bazie danych
    - Możliwość deanonymizacji
    - Cache dla wydajności
    """
    
    def __init__(self, db_config, use_cache=True):
        """Initialize with database connection"""
    
    def anonymize(self, value, value_type='generic'):
        """Anonimizuj wartość (deterministycznie)"""
    
    def deanonymize(self, anonymized_value, value_type='generic'):
        """Deanonymizuj wartość"""
    
    def anonymize_record(self, record, fields_to_anonymize):
        """Anonimizuj rekord"""
    
    def deanonymize_record(self, record, fields_to_anonymize):
        """Deanonymizuj rekord"""
    
    def anonymize_batch(self, records, fields_to_anonymize):
        """Anonimizuj wiele rekordów"""
    
    def get_mapping_stats(self):
        """Statystyki mapping table"""
```

### Security Module (DataAnonymizer)

```python
class DataAnonymizer:
    """
    Podstawowa anonimizacja (bez determinizmu).
    Używana jako fallback lub dla prostych przypadków.
    """
    
    def anonymize_ip(self, ip):
        """Anonimizuj IP (zero out last octet)"""
    
    def hash_user_id(self, user_id):
        """Hash user ID"""
    
    def tokenize_email(self, email):
        """Tokenize email"""
```

## Funkcjonalności

### 1. Deterministyczna Anonimizacja
- **Hash-based**: Użycie deterministycznego hasha (SHA256 z salt)
- **Mapping Table**: Przechowywanie mapowania w bazie danych
- **Cache**: Cache mapping table w pamięci dla wydajności

### 2. Typy Wartości
- **IP Address**: Anonimizacja adresów IP
- **Email**: Anonimizacja adresów email
- **Username**: Anonimizacja nazw użytkowników
- **Hostname**: Anonimizacja nazw hostów
- **Generic**: Ogólna anonimizacja dla innych wartości

### 3. Bezpieczeństwo
- **Hash Original Values**: Oryginalne wartości mogą być hashowane przed zapisem
- **Encryption**: Opcjonalne szyfrowanie mapping table
- **Access Control**: Kontrola dostępu do mapping table

### 4. Wydajność
- **Cache**: Cache mapping table w pamięci
- **Batch Operations**: Anonimizacja wielu wartości jednocześnie
- **Database Indexing**: Indeksy na mapping table dla szybkiego wyszukiwania

## Plan Implementacji

### Krok 1: Utworzenie DeterministicAnonymizer
- Klasa z metodami anonimizacji i deanonymizacji
- Integracja z bazą danych PostgreSQL
- Cache mapping table

### Krok 2: Utworzenie Security Module
- Podstawowy DataAnonymizer (bez determinizmu)
- Metody pomocnicze dla różnych typów danych

### Krok 3: Schema Database
- Tabela `anonymization_mapping` w bazie danych
- Indeksy dla wydajności
- Migracje schema

### Krok 4: Dokumentacja
- Dokumentacja użycia
- Przykłady
- Best practices

## Korzyści

1. **Dla AI**: Anonimizowane dane przed wysłaniem do AI
2. **Dla Raportowania**: Możliwość deanonymizacji wyników
3. **Dla Bezpieczeństwa**: Ochrona danych wrażliwych
4. **Dla Konsystencji**: Deterministyczna anonimizacja zapewnia spójność

## Następne kroki (po PHASE1-03)

- PHASE4-01: Deanonymization Service - pełna implementacja deanonymizacji
- PHASE4-02: Final Report Generator - użycie deanonymizacji w raportach

