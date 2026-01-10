#!/bin/bash
# Test runner script for Threat Hunting Lab tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Threat Hunting Lab - Test Runner ===${NC}\n"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Install it with: pip install pytest pytest-cov"
    exit 1
fi

# Check if config.yml exists
if [ ! -f "configs/config.yml" ]; then
    echo -e "${YELLOW}Warning: configs/config.yml not found${NC}"
    echo "Some tests may be skipped. Create config.yml from config.example.yml"
fi

# Parse arguments
TEST_TYPE="${1:-all}"
VERBOSE="${2:-}"

case "$TEST_TYPE" in
    unit)
        echo -e "${GREEN}Running unit tests...${NC}\n"
        pytest tests/unit/ $VERBOSE
        ;;
    integration)
        echo -e "${GREEN}Running integration tests...${NC}\n"
        pytest tests/integration/ $VERBOSE
        ;;
    api)
        echo -e "${GREEN}Running API tests...${NC}\n"
        pytest tests/integration/test_remote_api.py $VERBOSE
        ;;
    all)
        echo -e "${GREEN}Running all tests...${NC}\n"
        pytest tests/ $VERBOSE
        ;;
    coverage)
        echo -e "${GREEN}Running tests with coverage...${NC}\n"
        pytest --cov=automation-scripts --cov-report=html --cov-report=term tests/
        echo -e "\n${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    *)
        echo "Usage: $0 [unit|integration|api|all|coverage] [pytest-options]"
        echo ""
        echo "Examples:"
        echo "  $0 all                    # Run all tests"
        echo "  $0 unit -v                # Run unit tests with verbose output"
        echo "  $0 integration             # Run integration tests"
        echo "  $0 coverage                # Run tests with coverage report"
        exit 1
        ;;
esac

echo -e "\n${GREEN}=== Tests completed ===${NC}"

