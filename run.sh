#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Make all scripts executable
chmod +x "$SCRIPT_DIR/scripts/"*.sh

show_menu() {
    clear
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     Aetos Orchestrator Manager        ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}1)${NC} 🚀 Deploy and stream logs"
    echo -e "${GREEN}2)${NC} ▶️  Start container"
    echo -e "${GREEN}3)${NC} ⏸️  Stop container"
    echo -e "${GREEN}4)${NC} 📦 Deploy only"
    echo -e "${GREEN}5)${NC} 📋 Stream logs"
    echo -e "${GREEN}6)${NC} 🚪 Exit"
    echo ""
    echo -ne "${YELLOW}Select an option [1-6]: ${NC}"
}

deploy_and_logs() {
    echo -e "${BLUE}Deploying orchestrator...${NC}"
    "$SCRIPT_DIR/scripts/deploy.sh"
    
    echo ""
    echo -e "${BLUE}Waiting 10 seconds for container to start...${NC}"
    sleep 10
    
    echo -e "${BLUE}Streaming logs...${NC}"
    "$SCRIPT_DIR/scripts/logs.sh"
}

start_container() {
    echo -e "${BLUE}Starting container...${NC}"
    "$SCRIPT_DIR/scripts/start.sh"
    
    echo ""
    read -p "Press Enter to return to menu..."
}

stop_container() {
    echo -e "${BLUE}Stopping container...${NC}"
    "$SCRIPT_DIR/scripts/stop.sh"
    
    echo ""
    read -p "Press Enter to return to menu..."
}

deploy_only() {
    echo -e "${BLUE}Deploying orchestrator...${NC}"
    "$SCRIPT_DIR/scripts/deploy.sh"
    
    echo ""
    read -p "Press Enter to return to menu..."
}

stream_logs() {
    echo -e "${BLUE}Streaming logs...${NC}"
    "$SCRIPT_DIR/scripts/logs.sh"
}

# Main loop
while true; do
    show_menu
    read choice
    
    case $choice in
        1)
            deploy_and_logs
            ;;
        2)
            start_container
            ;;
        3)
            stop_container
            ;;
        4)
            deploy_only
            ;;
        5)
            stream_logs
            ;;
        6)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option. Please try again.${NC}"
            sleep 2
            ;;
    esac
done