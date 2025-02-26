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

echo -e "${BLUE}=== Running GRPC Protocol Test Suite ===${NC}\n"

# Change to the root directory and run tests as modules
cd "$ROOT_DIR"

# Run protocol tests
echo -e "${BLUE}Running Client-Side Tests...${NC}"
python3 -m src.grpc_protocol.tests.test_client -v
CLIENT_RESULT=$?

echo -e "${BLUE}Running Server-Side Tests...${NC}"
python3 -m src.grpc_protocol.tests.test_server -v
SERVER_RESULT=$?

echo -e "\n${BLUE}Running Integration Tests...${NC}"
python3 -m src.custom_protocol.tests.test_integration -v
INTEGRATION_RESULT=$?

echo -e "\n${BLUE}=== Test Summary ===${NC}"
if [ $CLIENT_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Client Tests: PASSED${NC}"
else
    echo -e "${RED}✗ Client Tests: FAILED${NC}"
fi

if [ $SERVER_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Server Tests: PASSED${NC}"
else
    echo -e "${RED}✗ Server Tests: FAILED${NC}"
fi

if [ $INTEGRATION_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Integration Tests: PASSED${NC}"
else
    echo -e "${RED}✗ Integration Tests: FAILED${NC}"
fi

# Exit with failure if any test suite failed
if [ $CLIENT_RESULT -ne 0 ] || [ $SERVER_RESULT -ne 0 ] || [ $INTEGRATION_RESULT -ne 0 ]; then
    exit 1
fi

exit 0 