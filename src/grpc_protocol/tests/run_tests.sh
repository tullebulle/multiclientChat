#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the root directory (3 levels up from tests)
ROOT_DIR="$( cd "$SCRIPT_DIR/../../.." && pwd )"

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Running Custom Protocol Test Suite ===${NC}\n"

# Change to the root directory and run tests as modules
cd "$ROOT_DIR"

# Run protocol tests
echo -e "${BLUE}Running Protocol Tests...${NC}"
python3 -m src.custom_protocol.tests.test_protocol -v
PROTOCOL_RESULT=$?

echo -e "\n${BLUE}Running Integration Tests...${NC}"
python3 -m src.custom_protocol.tests.test_integration -v
INTEGRATION_RESULT=$?

echo -e "\n${BLUE}=== Test Summary ===${NC}"
if [ $PROTOCOL_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Protocol Tests: PASSED${NC}"
else
    echo -e "${RED}✗ Protocol Tests: FAILED${NC}"
fi

if [ $INTEGRATION_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Integration Tests: PASSED${NC}"
else
    echo -e "${RED}✗ Integration Tests: FAILED${NC}"
fi

# Exit with failure if any test suite failed
if [ $PROTOCOL_RESULT -ne 0 ] || [ $INTEGRATION_RESULT -ne 0 ]; then
    exit 1
fi

exit 0 