#!/bin/bash
# SENTINEL Platform - Complex Installation Script
# Requires multiple dependencies and configuration steps

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REQUIRED_PYTHON_VERSION="3.10"
REQUIRED_NODE_VERSION="18"
REQUIRED_DOCKER_VERSION="24"
REQUIRED_RAM_GB=16

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SENTINEL PLATFORM INSTALLATION${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to compare versions
version_ge() {
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

echo -e "${YELLOW}[1/10] Verifying Python version...${NC}"
if ! command_exists python3; then
    echo -e "${RED}ERROR: Python 3 is not installed!${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
if ! version_ge "$PYTHON_VERSION" "$REQUIRED_PYTHON_VERSION"; then
    echo -e "${RED}ERROR: Python $REQUIRED_PYTHON_VERSION or higher is required!${NC}"
    echo "Current version: $PYTHON_VERSION"
    exit 1
fi

echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

echo -e "${YELLOW}[2/10] Verifying Node.js version...${NC}"
if ! command_exists node; then
    echo -e "${RED}ERROR: Node.js is not installed!${NC}"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt "$REQUIRED_NODE_VERSION" ]; then
    echo -e "${RED}ERROR: Node.js $REQUIRED_NODE_VERSION or higher is required!${NC}"
    echo "Current version: $(node --version)"
    exit 1
fi

echo -e "${GREEN}✓ Node.js $(node --version)${NC}"

echo -e "${YELLOW}[3/10] Verifying Docker installation...${NC}"
if ! command_exists docker; then
    echo -e "${RED}ERROR: Docker is not installed!${NC}"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

DOCKER_VERSION=$(docker --version | awk '{print $3}' | cut -d',' -f1 | cut -d'.' -f1)
if [ "$DOCKER_VERSION" -lt "$REQUIRED_DOCKER_VERSION" ]; then
    echo -e "${RED}ERROR: Docker $REQUIRED_DOCKER_VERSION or higher is required!${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}ERROR: Docker Compose is not installed!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker $(docker --version)${NC}"
echo -e "${GREEN}✓ Docker Compose $(docker-compose --version)${NC}"

echo -e "${YELLOW}[4/10] Checking system resources...${NC}"
TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "0")
TOTAL_RAM_GB=$((TOTAL_RAM_KB / 1024 / 1024))

if [ "$TOTAL_RAM_GB" -lt "$REQUIRED_RAM_GB" ] && [ "$TOTAL_RAM_GB" -gt 0 ]; then
    echo -e "${RED}WARNING: Insufficient RAM detected!${NC}"
    echo "Required: ${REQUIRED_RAM_GB}GB, Available: ${TOTAL_RAM_GB}GB"
    echo "System may not run optimally."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
elif [ "$TOTAL_RAM_GB" -gt 0 ]; then
    echo -e "${GREEN}✓ RAM: ${TOTAL_RAM_GB}GB${NC}"
fi

echo -e "${YELLOW}[5/10] Checking required Python packages...${NC}"
REQUIRED_PACKAGES=(
    "cryptography"
    "fastapi"
    "sqlalchemy"
    "kafka-python"
    "torch"
    "numpy"
    "redis"
    "psycopg2-binary"
)

MISSING_PACKAGES=0
for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import ${package//-/_}" 2>/dev/null; then
        MISSING_PACKAGES=$((MISSING_PACKAGES + 1))
    fi
done

if [ $MISSING_PACKAGES -gt 0 ]; then
    echo -e "${YELLOW}Installing Python dependencies (this may take 10-15 minutes)...${NC}"
    pip3 install -r requirements.txt
fi

echo -e "${GREEN}✓ Python packages verified${NC}"

echo -e "${YELLOW}[6/10] Checking environment configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠  IMPORTANT: Edit .env file with your configuration!${NC}"
    echo ""
    echo "Required configurations:"
    echo "  - JWT_SECRET_KEY (generate with: openssl rand -hex 32)"
    echo "  - Database passwords"
    echo "  - API keys for data sources (15+ keys required)"
    echo ""
    echo "Data source API keys needed:"
    echo "  - OPENSKY_USERNAME & OPENSKY_PASSWORD"
    echo "  - NASA_API_KEY"
    echo "  - OTX_API_KEY (AlienVault)"
    echo "  - ABUSEIPDB_KEY"
    echo "  - MARINETRAFFIC_API_KEY"
    echo "  - And 10+ more..."
    echo ""
    read -p "Press Enter after editing .env file..."
fi

# Verify critical env vars
source .env 2>/dev/null || true
if [ -z "$JWT_SECRET_KEY" ] || [ "$JWT_SECRET_KEY" = "change-me-to-a-secure-random-string" ]; then
    echo -e "${RED}ERROR: JWT_SECRET_KEY not configured in .env!${NC}"
    echo "Generate with: openssl rand -hex 32"
    exit 1
fi

echo -e "${GREEN}✓ Environment configuration found${NC}"

echo -e "${YELLOW}[7/10] Checking API keys configuration...${NC}"
REQUIRED_API_KEYS=(
    "OPENSKY_USERNAME"
    "NASA_API_KEY"
    "OTX_API_KEY"
)

MISSING_API_KEYS=0
for key in "${REQUIRED_API_KEYS[@]}"; do
    if [ -z "${!key}" ]; then
        echo -e "${RED}   Missing: $key${NC}"
        MISSING_API_KEYS=$((MISSING_API_KEYS + 1))
    fi
done

if [ $MISSING_API_KEYS -gt 0 ]; then
    echo -e "${YELLOW}⚠  WARNING: $MISSING_API_KEYS required API keys not configured${NC}"
    echo "Platform will have limited functionality."
    echo "See SETUP_REALTIME.md for API key registration instructions."
    read -p "Continue with limited functionality? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ Required API keys configured${NC}"
fi

echo -e "${YELLOW}[8/10] Installing frontend dependencies...${NC}"
if [ -d "src/frontend" ]; then
    cd src/frontend
    if [ ! -d "node_modules" ]; then
        echo "Installing npm packages (this may take 5-10 minutes)..."
        npm install
    fi
    cd ../..
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
fi

echo -e "${YELLOW}[9/10] Building Docker images...${NC}"
echo "This may take 15-25 minutes depending on your system..."
docker-compose build --parallel 2>&1 | grep -E "Building|Successfully|ERROR" || true

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo -e "${RED}ERROR: Docker build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker images built${NC}"

echo -e "${YELLOW}[10/10] Running pre-flight checks...${NC}"

# Check Docker daemon
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}ERROR: Docker daemon is not running!${NC}"
    exit 1
fi

# Check ports availability
REQUIRED_PORTS=(80 8000 5432 9092 9200 6379)
for port in "${REQUIRED_PORTS[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}ERROR: Port $port is already in use!${NC}"
        echo "Please stop any services using this port."
        exit 1
    fi
done

echo -e "${GREEN}✓ All ports available${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}INSTALLATION COMPLETED SUCCESSFULLY${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Start the platform:"
echo -e "   ${BLUE}docker-compose up -d${NC}"
echo ""
echo "2. Check service status:"
echo -e "   ${BLUE}docker-compose ps${NC}"
echo ""
echo "3. View logs:"
echo -e "   ${BLUE}docker-compose logs -f${NC}"
echo ""
echo "4. Access the dashboard:"
echo -e "   ${BLUE}http://localhost${NC}"
echo ""
echo "5. API Documentation:"
echo -e "   ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "${YELLOW}NOTE: First startup may take several minutes.${NC}"
echo -e "${YELLOW}NOTE: Many features require API keys to be configured.${NC}"
echo ""

# Create a marker file to indicate successful installation
touch .installation_complete
echo "$(date)" > .installation_complete

echo "Installation script completed at: $(date)"
