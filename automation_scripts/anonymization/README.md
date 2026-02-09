# Deterministic Anonymization (Step 1.3)

HMAC-SHA256-based pseudonymization with mapping store for deanonymization. Same input always produces same pseudonym; authorized users can reverse via `MappingStore`.

## Modules

| Module | Purpose |
|--------|---------|
| `deterministic_anonymizer` | `DeterministicAnonymizer`, `create_anonymizer` – anonymize/deanonymize values, dicts, lists |
| `mapping_store` | `MappingStore`, `InMemoryMappingStore`, `SQLiteMappingStore` – store original↔pseudonym mappings |
| `../security` | `get_anonymization_secret`, `encrypt_mapping_value`, `decrypt_mapping_value` – HMAC key, AES-256 for mapping encryption |

## Usage

```python
from automation_scripts.anonymization import create_anonymizer

# Uses TH_ANONYMIZATION_PASSPHRASE or config
anon = create_anonymizer(db_path="/var/lib/th_timmy/anonymization.db")

# Single value
pseudo = anon.anonymize("192.168.1.100", "ip_address")
orig = anon.deanonymize(pseudo)  # "192.168.1.100"

# Dict (PII fields anonymized by default)
data = {"username": "alice", "ip_address": "10.0.0.1", "count": 42}
out = anon.anonymize_dict(data)

# List
items = ["ip1", "ip2"]
out = anon.anonymize_list(items, field_type="ip")
```

## Configuration

| Source | Variable | Description |
|--------|----------|-------------|
| Env | `TH_ANONYMIZATION_PASSPHRASE` | Passphrase; key derived via Scrypt |
| Env | `TH_ANONYMIZATION_SECRET` | Raw secret or base64 (32 bytes) |
| Env | `TH_ANONYMIZATION_SECRET_PATH` | Path to key file |
| Config | `anonymization.secret_path` | Path to key file |
| Config | `anonymization.secret` | Dev only; not for production |
| Config | `anonymization.mapping_db_path` | SQLite path for mapping store |

## Testing

```bash
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/test_mapping_store.py tests/unit/test_security.py tests/unit/test_deterministic_anonymizer.py -v
./tests/integration/run_anonymization_integration.sh
```

## Security

- HMAC-SHA256 for pseudonymization (deterministic, same input → same output)
- Mapping values can be encrypted with AES-256-GCM via `encrypt_mapping_value` / `decrypt_mapping_value`
- Secret must not be stored in repo; use env vars or secure key path
- Mapping store on VM01/VM02 only; access restricted per ANONYMIZATION.md
