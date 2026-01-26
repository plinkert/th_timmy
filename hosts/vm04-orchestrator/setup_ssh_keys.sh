#!/bin/bash

# Skrypt do automatycznego tworzenia i konfigurowania kluczy SSH dla VM01-VM03
# Uruchamiany na VM04 (orchestrator)
# Autor: Auto-generated
# Data: 2026-01-26

# set -e  # Wyłączone - pozwalamy na kontynuację przy błędach w pętli
set -u   # Sprawdzaj nieużywane zmienne
set -o pipefail  # Sprawdzaj błędy w pipeline

# Kolory dla lepszej czytelności
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Ścieżki
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_FILE="$PROJECT_ROOT/configs/config.yml"

# Użyj HOME użytkownika, który uruchomił skrypt (nie root jeśli uruchomiony z sudo)
# Bezpieczne sprawdzenie SUDO_USER (może być niezdefiniowane)
if [ -n "${SUDO_USER:-}" ]; then
    REAL_USER="$SUDO_USER"
    REAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    REAL_USER="${USER:-$(whoami)}"
    REAL_HOME="$HOME"
fi

SSH_DIR="$REAL_HOME/.ssh"
SSH_KEYS_DIR="$SSH_DIR/th_timmy_keys"

# Funkcje pomocnicze
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# Funkcja do zmiany właściciela plików (jeśli skrypt uruchomiony z sudo)
fix_file_ownership() {
    local file_or_dir="$1"
    if [ -n "${SUDO_USER:-}" ] && [ -e "$file_or_dir" ]; then
        # Jeśli jesteśmy root (przez sudo), możemy użyć chown bezpośrednio
        if [ "$(id -u)" -eq 0 ]; then
            chown -R "$REAL_USER:$REAL_USER" "$file_or_dir" 2>/dev/null || {
                log_warning "Nie można zmienić właściciela $file_or_dir na $REAL_USER"
            }
        fi
    fi
}

# Sprawdź czy plik konfiguracyjny istnieje
if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Plik konfiguracyjny nie istnieje: $CONFIG_FILE"
    exit 1
fi

log_info "Używam pliku konfiguracyjnego: $CONFIG_FILE"

# Informacja o ścieżkach SSH
if [ -n "${SUDO_USER:-}" ]; then
    log_warning "Uwaga: Skrypt uruchomiony z sudo. Używam katalogu SSH użytkownika: $SSH_DIR"
    log_warning "Pliki będą tworzone z właścicielem: $REAL_USER"
else
    log_info "Używam katalogu SSH: $SSH_DIR"
fi

# Sprawdź czy możemy tworzyć pliki w katalogu SSH
if [ ! -w "$SSH_DIR" ] && [ ! -w "$(dirname "$SSH_DIR")" ]; then
    log_error "Brak uprawnień do zapisu w katalogu SSH: $SSH_DIR"
    log_error "Uruchom skrypt jako użytkownik, który ma dostęp do ~/.ssh/"
    exit 1
fi

# Sprawdź czy Python i PyYAML są dostępne
if ! command -v python3 &> /dev/null; then
    log_error "python3 nie jest zainstalowany. Zainstaluj go: sudo apt-get install python3"
    exit 1
fi

# Sprawdź czy PyYAML jest dostępny
if ! python3 -c "import yaml" 2>/dev/null; then
    log_warning "PyYAML nie jest zainstalowany. Próbuję zainstalować..."
    if command -v pip3 &> /dev/null; then
        pip3 install --user pyyaml 2>/dev/null || {
            log_error "Nie można zainstalować PyYAML. Zainstaluj ręcznie: pip3 install pyyaml"
            exit 1
        }
    else
        log_error "pip3 nie jest dostępny. Zainstaluj PyYAML ręcznie: pip3 install pyyaml"
        exit 1
    fi
fi

# Funkcja do parsowania YAML i wyciągnięcia informacji o VM
parse_vm_config() {
    local vm_id=$1
    local exit_code=0
    local output
    
    output=$(python3 << EOF 2>&1
import yaml
import sys

try:
    with open('$CONFIG_FILE', 'r') as f:
        config = yaml.safe_load(f)
    
    vms = config.get('vms', {})
    vm = vms.get('$vm_id', {})
    
    if not vm:
        print(f"ERROR: VM $vm_id nie znaleziony w konfiguracji", file=sys.stderr)
        sys.exit(1)
    
    ip = vm.get('ip', '')
    ssh_user = vm.get('ssh_user', 'thadmin')
    ssh_port = vm.get('ssh_port', 22)
    enabled = vm.get('enabled', True)
    
    if not enabled:
        print(f"ERROR: VM $vm_id jest wyłączony w konfiguracji", file=sys.stderr)
        sys.exit(1)
    
    if not ip:
        print(f"ERROR: Brak adresu IP dla VM $vm_id", file=sys.stderr)
        sys.exit(1)
    
    print(f"{ip}|{ssh_user}|{ssh_port}")
except Exception as e:
    print(f"ERROR: Błąd parsowania YAML: {e}", file=sys.stderr)
    sys.exit(1)
EOF
)
    exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        echo "$output" >&2
        return $exit_code
    fi
    
    echo "$output"
    return 0
}

# Funkcja do generowania klucza SSH
generate_ssh_key() {
    local vm_id=$1
    local key_file="$SSH_KEYS_DIR/id_ed25519_${vm_id}"
    
    if [ -f "${key_file}" ]; then
        log_warning "Klucz już istnieje dla $vm_id: ${key_file}"
        if [ -t 0 ]; then
            # Tylko jeśli jest interaktywny terminal
            read -p "Czy chcesz nadpisać istniejący klucz? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Pomijam generowanie klucza dla $vm_id"
                return 0
            fi
        else
            # Tryb nieinteraktywny - nie nadpisuj
            log_info "Tryb nieinteraktywny - pomijam generowanie klucza dla $vm_id (klucz już istnieje)"
            return 0
        fi
        # Backup starego klucza
        if [ -f "${key_file}" ]; then
            mv "${key_file}" "${key_file}.backup.$(date +%Y%m%d_%H%M%S)" || true
        fi
        if [ -f "${key_file}.pub" ]; then
            mv "${key_file}.pub" "${key_file}.pub.backup.$(date +%Y%m%d_%H%M%S)" || true
        fi
    fi
    
    log_step "Generowanie klucza SSH dla $vm_id..."
    
    # Utwórz katalog jeśli nie istnieje
    mkdir -p "$SSH_KEYS_DIR"
    chmod 700 "$SSH_KEYS_DIR"
    fix_file_ownership "$SSH_KEYS_DIR"
    
    # Generuj klucz ed25519 (zalecany, bezpieczny i szybki)
    if ssh-keygen -t ed25519 -f "${key_file}" -N "" -C "th_timmy_${vm_id}_$(date +%Y%m%d)"; then
        chmod 600 "${key_file}"
        chmod 644 "${key_file}.pub"
        # Zmień właściciela na właściwego użytkownika (jeśli uruchomione z sudo)
        fix_file_ownership "${key_file}"
        fix_file_ownership "${key_file}.pub"
        log_success "Klucz wygenerowany: ${key_file}"
        return 0
    else
        log_error "Błąd podczas generowania klucza dla $vm_id"
        return 1
    fi
}

# Funkcja do kopiowania klucza publicznego na host
copy_public_key() {
    local vm_id=$1
    local ip=$2
    local ssh_user=$3
    local ssh_port=$4
    local key_file="$SSH_KEYS_DIR/id_ed25519_${vm_id}.pub"
    
    if [ ! -f "$key_file" ]; then
        log_error "Klucz publiczny nie istnieje: $key_file"
        return 1
    fi
    
    log_step "Kopiowanie klucza publicznego na $vm_id ($ssh_user@$ip:$ssh_port)..."
    
    # Sprawdź czy ssh-copy-id jest dostępny
    if command -v ssh-copy-id &> /dev/null; then
        # Użyj ssh-copy-id (najprostsze rozwiązanie)
        if ssh-copy-id -i "$key_file" -p "$ssh_port" "$ssh_user@$ip" 2>/dev/null; then
            log_success "Klucz skopiowany używając ssh-copy-id"
            return 0
        else
            log_warning "ssh-copy-id nie zadziałał, próbuję ręcznie..."
        fi
    fi
    
    # Ręczne kopiowanie klucza (jeśli ssh-copy-id nie działa)
    log_info "Próba ręcznego kopiowania klucza..."
    
    # Sprawdź czy możemy połączyć się przez SSH (może wymagać hasła)
    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p "$ssh_port" "$ssh_user@$ip" "mkdir -p ~/.ssh && chmod 700 ~/.ssh" 2>/dev/null; then
        # Skopiuj klucz publiczny
        if cat "$key_file" | ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p "$ssh_port" "$ssh_user@$ip" "cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"; then
            log_success "Klucz skopiowany ręcznie"
            return 0
        fi
    fi
    
    # Alternatywnie, użyj sshpass jeśli dostępny (dla automatycznego wprowadzania hasła)
    if command -v sshpass &> /dev/null && [ -t 0 ]; then
        log_info "Używam sshpass do kopiowania klucza..."
        read -sp "Wprowadź hasło dla $ssh_user@$ip: " password
        echo
        if [ -n "$password" ] && sshpass -p "$password" ssh-copy-id -i "$key_file" -p "$ssh_port" -o StrictHostKeyChecking=no "$ssh_user@$ip" 2>/dev/null; then
            log_success "Klucz skopiowany używając sshpass"
            return 0
        fi
    fi
    
    log_error "Nie udało się skopiować klucza na $vm_id"
    log_warning "Możesz skopiować klucz ręcznie:"
    log_warning "  cat $key_file | ssh -p $ssh_port $ssh_user@$ip 'cat >> ~/.ssh/authorized_keys'"
    return 1
}

# Funkcja do testowania połączenia SSH
test_ssh_connection() {
    local vm_id=$1
    local ip=$2
    local ssh_user=$3
    local ssh_port=$4
    local key_file="$SSH_KEYS_DIR/id_ed25519_${vm_id}"
    
    log_step "Testowanie połączenia SSH z $vm_id..."
    
    if ssh -i "$key_file" -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes -p "$ssh_port" "$ssh_user@$ip" "echo 'SSH connection successful'" 2>/dev/null; then
        log_success "Połączenie SSH działa poprawnie dla $vm_id"
        return 0
    else
        log_error "Nie można nawiązać połączenia SSH z $vm_id"
        return 1
    fi
}

# Funkcja do wymuszania logowania kluczami SSH i blokowania logowania hasłem
configure_ssh_server() {
    local vm_id=$1
    local ip=$2
    local ssh_user=$3
    local ssh_port=$4
    local key_file="$SSH_KEYS_DIR/id_ed25519_${vm_id}"
    
    log_step "Konfigurowanie serwera SSH na $vm_id (wymuszanie kluczy, blokowanie hasła)..."
    log_warning "UWAGA: Ta operacja wymaga uprawnień sudo na hoście docelowym!"
    log_warning "Po tej operacji logowanie hasłem będzie zablokowane - upewnij się, że klucz działa!"
    
    # Sprawdź czy możemy połączyć się używając klucza
    if ! ssh -i "$key_file" -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes -p "$ssh_port" "$ssh_user@$ip" "true" 2>/dev/null; then
        log_error "Nie można połączyć się z $vm_id używając klucza. Pomijam konfigurację serwera SSH."
        log_error "WAŻNE: Nie można wymusić kluczy, jeśli połączenie kluczem nie działa!"
        return 1
    fi
    
    # Sprawdź czy użytkownik ma uprawnienia sudo
    log_info "Sprawdzanie uprawnień sudo..."
    if ! ssh -i "$key_file" -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes -p "$ssh_port" "$ssh_user@$ip" "sudo -n true" 2>/dev/null; then
        log_warning "Użytkownik $ssh_user może nie mieć uprawnień sudo lub wymagane jest hasło."
        log_warning "Próba wykonania konfiguracji (może wymagać wprowadzenia hasła sudo)..."
    else
        log_success "Uprawnienia sudo potwierdzone"
    fi
    
    # Backup oryginalnego pliku konfiguracyjnego
    log_info "Tworzenie kopii zapasowej /etc/ssh/sshd_config..."
    ssh -i "$key_file" -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes -p "$ssh_port" "$ssh_user@$ip" \
        "sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || {
        log_warning "Nie można utworzyć kopii zapasowej (może brakować uprawnień sudo)"
    }
    
    # Modyfikuj konfigurację SSH
    log_info "Modyfikowanie konfiguracji SSH..."
    
    # Utwórz skrypt do wykonania na zdalnym hoście
    local remote_script=$(cat << 'REMOTE_SCRIPT_END'
#!/bin/bash
set -e

# Backup konfiguracji
SSHD_CONFIG="/etc/ssh/sshd_config"
BACKUP_FILE="${SSHD_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$SSHD_CONFIG" "$BACKUP_FILE"
echo "Backup utworzony: $BACKUP_FILE"

# Funkcja do ustawienia wartości w konfiguracji
set_ssh_option() {
    local option="$1"
    local value="$2"
    local config_file="$3"
    
    # Sprawdź czy opcja już istnieje (niezależnie od komentarza)
    if grep -qE "^[[:space:]]*#?[[:space:]]*${option}[[:space:]]+" "$config_file" 2>/dev/null; then
        # Zaktualizuj istniejącą opcję (usuń komentarz jeśli był)
        sed -i "s/^[[:space:]]*#\?[[:space:]]*${option}[[:space:]]*.*/${option} ${value}/" "$config_file"
        echo "Zaktualizowano: ${option} ${value}"
    else
        # Dodaj nową opcję na końcu pliku
        echo "${option} ${value}" >> "$config_file"
        echo "Dodano: ${option} ${value}"
    fi
}

# Ustaw opcje bezpieczeństwa SSH
set_ssh_option "PasswordAuthentication" "no" "$SSHD_CONFIG"
set_ssh_option "PubkeyAuthentication" "yes" "$SSHD_CONFIG"
set_ssh_option "ChallengeResponseAuthentication" "no" "$SSHD_CONFIG"
set_ssh_option "UsePAM" "no" "$SSHD_CONFIG"
set_ssh_option "PermitRootLogin" "no" "$SSHD_CONFIG"

# Opcjonalne: dodatkowe opcje bezpieczeństwa
set_ssh_option "X11Forwarding" "no" "$SSHD_CONFIG"
set_ssh_option "MaxAuthTries" "3" "$SSHD_CONFIG"
set_ssh_option "ClientAliveInterval" "300" "$SSHD_CONFIG"
set_ssh_option "ClientAliveCountMax" "2" "$SSHD_CONFIG"

# Sprawdź składnię konfiguracji przed przeładowaniem
echo "Sprawdzanie składni konfiguracji SSH..."
if sshd -t 2>/dev/null; then
    echo "Konfiguracja SSH jest poprawna"
    # Przeładuj konfigurację SSH (nie restartuj, aby nie przerwać połączenia)
    if command -v systemctl &> /dev/null; then
        systemctl reload sshd 2>/dev/null && echo "SSH przeładowany (systemctl)" || {
            echo "Nie można przeładować przez systemctl, próbuję service..."
            service ssh reload 2>/dev/null || service sshd reload 2>/dev/null || {
                echo "UWAGA: Nie można przeładować SSH. Może być wymagany restart: sudo systemctl restart sshd"
            }
        }
    else
        service ssh reload 2>/dev/null || service sshd reload 2>/dev/null || {
            echo "UWAGA: Nie można przeładować SSH. Może być wymagany restart."
        }
    fi
    echo "Konfiguracja SSH została zaktualizowana i przeładowana"
    exit 0
else
    echo "BŁĄD: Konfiguracja SSH zawiera błędy! Przywracam kopię zapasową..."
    cp "$BACKUP_FILE" "$SSHD_CONFIG"
    exit 1
fi
REMOTE_SCRIPT_END
)
    
    # Sprawdź czy sudo wymaga hasła
    local ssh_base_flags="-i $key_file -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes -p $ssh_port"
    local sudo_password=""
    local needs_password=false
    
    if ! ssh $ssh_base_flags "$ssh_user@$ip" "sudo -n true" 2>/dev/null; then
        needs_password=true
        log_warning "Sudo wymaga hasła na $vm_id"
        
        if [ -t 0 ]; then
            # Terminal dostępny - poproś o hasło
            read -sp "Wprowadź hasło sudo dla $ssh_user@$ip: " sudo_password
            echo
            if [ -z "$sudo_password" ]; then
                log_error "Hasło nie zostało wprowadzone. Pomijam konfigurację serwera SSH dla $vm_id"
                return 1
            fi
        else
            log_error "Sudo wymaga hasła, ale terminal nie jest dostępny (tryb nieinteraktywny)"
            log_error "Skonfiguruj sudo NOPASSWD dla $ssh_user na $ip lub uruchom skrypt w trybie interaktywnym"
            return 1
        fi
    else
        log_info "Sudo nie wymaga hasła, wykonuję konfigurację..."
    fi
    
    # Wykonaj skrypt z odpowiednim sposobem przekazania hasła sudo
    local ssh_output
    if [ "$needs_password" = true ] && [ -n "$sudo_password" ]; then
        # Utwórz tymczasowy skrypt na zdalnym hoście i wykonaj go z sudo
        # To pozwala uniknąć problemów z przekazywaniem hasła przez stdin
        local temp_script="/tmp/configure_ssh_$$.sh"
        
        # Przekaż skrypt na zdalny host i wykonaj z sudo -S
        ssh_output=$(ssh $ssh_base_flags "$ssh_user@$ip" bash << EOF 2>&1
cat > $temp_script << 'SCRIPT_END'
$remote_script
SCRIPT_END
chmod +x $temp_script
echo '$sudo_password' | sudo -S bash $temp_script
rm -f $temp_script
EOF
)
        local ssh_exit_code=$?
        
        # Wyczyść hasło z pamięci
        sudo_password=""
    else
        # Sudo nie wymaga hasła
        ssh_output=$(echo "$remote_script" | ssh $ssh_base_flags "$ssh_user@$ip" \
            "sudo bash" 2>&1)
        local ssh_exit_code=$?
    fi
    
    # Wyświetl output (pomijając puste linie i niektóre komunikaty)
    echo "$ssh_output" | grep -v "^$" | while IFS= read -r line; do
        if [[ "$line" =~ ^\[sudo\].*password ]] || [[ "$line" =~ ^sudo:.*password ]]; then
            # Pomijamy prompt sudo
            :
        elif [[ "$line" =~ ^Pseudo-terminal ]]; then
            # Pomijamy komunikaty o terminalu
            :
        else
            log_info "  $line"
        fi
    done
    
    if [ $ssh_exit_code -eq 0 ]; then
        log_success "Konfiguracja serwera SSH zaktualizowana na $vm_id"
        log_info "  - PasswordAuthentication: no"
        log_info "  - PubkeyAuthentication: yes"
        log_info "  - PermitRootLogin: no"
        
        # Testuj czy nadal możemy się połączyć (powinno działać tylko kluczem)
        log_info "Testowanie połączenia po zmianach..."
        sleep 2
        if ssh -i "$key_file" -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes -p "$ssh_port" "$ssh_user@$ip" "echo 'Connection test successful'" 2>/dev/null; then
            log_success "Połączenie kluczem SSH działa poprawnie"
            
            # Próba połączenia hasłem powinna się nie powieść
            log_info "Weryfikacja: próba połączenia hasłem powinna się nie powieść..."
            if ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no -p "$ssh_port" "$ssh_user@$ip" "true" 2>/dev/null; then
                log_warning "UWAGA: Logowanie hasłem nadal działa! Może być wymagany restart SSH."
            else
                log_success "Weryfikacja: logowanie hasłem jest zablokowane"
            fi
        else
            log_error "UWAGA: Nie można połączyć się po zmianach! Sprawdź konfigurację ręcznie."
            return 1
        fi
        return 0
    else
        log_error "Błąd podczas konfiguracji serwera SSH na $vm_id"
        return 1
    fi
}

# Funkcja do konfiguracji SSH config
configure_ssh_config() {
    local vm_id=$1
    local ip=$2
    local ssh_user=$3
    local ssh_port=$4
    local key_file="$SSH_KEYS_DIR/id_ed25519_${vm_id}"
    local ssh_config="$SSH_DIR/config"
    
    log_step "Konfigurowanie ~/.ssh/config dla $vm_id..."
    
    # Utwórz katalog .ssh jeśli nie istnieje
    mkdir -p "$SSH_DIR"
    chmod 700 "$SSH_DIR"
    fix_file_ownership "$SSH_DIR"
    
    # Utwórz plik config jeśli nie istnieje
    touch "$ssh_config"
    chmod 600 "$ssh_config"
    fix_file_ownership "$ssh_config"
    
    # Sprawdź czy wpis już istnieje
    if grep -q "Host $vm_id" "$ssh_config" 2>/dev/null; then
        log_warning "Wpis dla $vm_id już istnieje w ~/.ssh/config"
        if [ -t 0 ]; then
            # Tylko jeśli jest interaktywny terminal
            read -p "Czy chcesz zaktualizować istniejący wpis? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Pomijam konfigurację SSH config dla $vm_id"
                return 0
            fi
        else
            # Tryb nieinteraktywny - zaktualizuj automatycznie
            log_info "Tryb nieinteraktywny - aktualizuję istniejący wpis"
        fi
        # Usuń stary wpis (wszystkie linie od "Host $vm_id" do pustej linii lub następnego "Host")
        sed -i "/^Host $vm_id$/,/^Host /{ /^Host $vm_id$/!{ /^Host /!d; }; }" "$ssh_config" 2>/dev/null || true
        # Alternatywnie, usuń wszystkie linie od "Host $vm_id" do pustej linii
        sed -i "/^Host $vm_id$/,/^$/d" "$ssh_config" 2>/dev/null || true
    fi
    
    # Oblicz względną ścieżkę do klucza (używając ~ zamiast pełnej ścieżki)
    local relative_key_path="~/.ssh/th_timmy_keys/id_ed25519_${vm_id}"
    
    # Dodaj nowy wpis zgodnie z wymaganiami użytkownika
    # Port dodajemy tylko jeśli jest inny niż domyślny (22)
    if [ "$ssh_port" != "22" ]; then
        cat >> "$ssh_config" << EOF

Host $vm_id
    HostName $ip
    User $ssh_user
    Port $ssh_port
    IdentityFile $relative_key_path
    IdentitiesOnly yes
EOF
    else
        cat >> "$ssh_config" << EOF

Host $vm_id
    HostName $ip
    User $ssh_user
    IdentityFile $relative_key_path
    IdentitiesOnly yes
EOF
    fi
    
    # Zmień właściciela pliku config (jeśli uruchomione z sudo)
    fix_file_ownership "$ssh_config"
    
    log_success "Dodano wpis do ~/.ssh/config dla $vm_id"
    log_info "  Konfiguracja: Host $vm_id -> $ssh_user@$ip"
}

# Główna funkcja
main() {
    log_info "=========================================="
    log_info "Konfiguracja kluczy SSH dla VM01-VM03"
    log_info "=========================================="
    echo ""
    
    # Lista VM do konfiguracji (VM01-VM03)
    VMS=("vm01" "vm02" "vm03")
    
    # Liczniki
    SUCCESS_COUNT=0
    FAILED_COUNT=0
    FAILED_VMS=()
    
    # Iteruj przez wszystkie VM
    for VM_ID in "${VMS[@]}"; do
        log_info "=========================================="
        log_info "Konfiguracja dla: $VM_ID"
        log_info "=========================================="
        
        # Parsuj konfigurację
        VM_CONFIG=$(parse_vm_config "$VM_ID" 2>&1) || {
            log_error "Błąd parsowania konfiguracji dla $VM_ID"
            ((FAILED_COUNT++))
            FAILED_VMS+=("$VM_ID")
            echo ""
            continue
        }
        
        # Rozdziel informacje (format: IP|USER|PORT)
        IFS='|' read -r IP SSH_USER SSH_PORT <<< "$VM_CONFIG"
        
        log_info "IP: $IP"
        log_info "User: $SSH_USER"
        log_info "Port: $SSH_PORT"
        echo ""
        
        # Generuj klucz SSH
        if ! generate_ssh_key "$VM_ID"; then
            log_error "Nie udało się wygenerować klucza dla $VM_ID"
            ((FAILED_COUNT++))
            FAILED_VMS+=("$VM_ID")
            echo ""
            continue
        fi
        
        # Kopiuj klucz publiczny
        if ! copy_public_key "$VM_ID" "$IP" "$SSH_USER" "$SSH_PORT"; then
            log_error "Nie udało się skopiować klucza dla $VM_ID"
            ((FAILED_COUNT++))
            FAILED_VMS+=("$VM_ID")
            echo ""
            continue
        fi
        
        # Testuj połączenie
        if ! test_ssh_connection "$VM_ID" "$IP" "$SSH_USER" "$SSH_PORT"; then
            log_error "Test połączenia nie powiódł się dla $VM_ID"
            ((FAILED_COUNT++))
            FAILED_VMS+=("$VM_ID")
            echo ""
            continue
        fi
        
        # Konfiguruj serwer SSH (wymuszanie kluczy, blokowanie hasła)
        if ! configure_ssh_server "$VM_ID" "$IP" "$SSH_USER" "$SSH_PORT"; then
            log_warning "Nie udało się skonfigurować serwera SSH dla $VM_ID, ale kontynuuję..."
            # Nie traktujemy tego jako błąd krytyczny - może brakować uprawnień sudo
        fi
        
        # Konfiguruj SSH config lokalnie
        configure_ssh_config "$VM_ID" "$IP" "$SSH_USER" "$SSH_PORT" || {
            log_warning "Nie udało się skonfigurować SSH config dla $VM_ID, ale kontynuuję..."
        }
        
        log_success "Konfiguracja zakończona pomyślnie dla $VM_ID"
        ((SUCCESS_COUNT++))
        echo ""
    done
    
    # Podsumowanie
    log_info "=========================================="
    log_info "PODSUMOWANIE"
    log_info "=========================================="
    log_success "Sukces: $SUCCESS_COUNT VM"
    if [ $FAILED_COUNT -gt 0 ]; then
        log_error "Błędy: $FAILED_COUNT VM"
        log_error "Nieudane VM: ${FAILED_VMS[*]}"
        echo ""
        log_info "Możesz uruchomić skrypt ponownie, aby spróbować ponownie dla nieudanych VM."
        exit 1
    else
        # Na końcu upewnij się, że wszystkie pliki mają właściwego właściciela
        if [ -n "${SUDO_USER:-}" ]; then
            log_info "Korygowanie właściciela plików..."
            fix_file_ownership "$SSH_DIR"
            fix_file_ownership "$SSH_KEYS_DIR"
            log_success "Właściciel plików został skorygowany"
        fi
        
        log_success "Wszystkie konfiguracje zakończone pomyślnie!"
        echo ""
        log_info "=========================================="
        log_info "INFORMACJE O KONFIGURACJI"
        log_info "=========================================="
        log_info "Plik konfiguracyjny SSH został utworzony:"
        log_info "  $SSH_DIR/config"
        echo ""
        log_info "Możesz teraz łączyć się z hostami używając:"
        for VM_ID in "${VMS[@]}"; do
            log_info "  ssh $VM_ID"
        done
        echo ""
        log_info "Aby wyświetlić konfigurację, użyj:"
        log_info "  cat $SSH_DIR/config"
        log_info "lub"
        log_info "  nano $SSH_DIR/config"
        exit 0
    fi
}

# Uruchom główną funkcję
main
