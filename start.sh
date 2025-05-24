#!/bin/bash

# AIFEED Startup Script
# This script provides easy commands to start and manage your AI Intelligence Dashboard

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Function to print colored output
print_color() {
    printf "${1}${2}${NC}\n"
}

# Function to print the banner
print_banner() {
    print_color $CYAN "
╔══════════════════════════════════════════════════════════════╗
║                          🤖 AIFEED                          ║
║                 Your AI Intelligence Dashboard               ║
║                                                              ║
║  Aggregating and analyzing AI content from multiple sources ║
╚══════════════════════════════════════════════════════════════╝
    "
}

# Function to check if Python is available
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_color $RED "❌ Error: Python is not installed or not in PATH"
        print_color $YELLOW "Please install Python 3.7+ and try again"
        exit 1
    fi
}

# Function to check if conda is available
check_conda() {
    if command -v conda &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to check if we're in a conda environment
in_conda_env() {
    if [[ -n "$CONDA_DEFAULT_ENV" ]] && [[ "$CONDA_DEFAULT_ENV" != "base" ]]; then
        return 0
    else
        return 1
    fi
}

# Function to check if virtual environment exists
check_venv() {
    # Check for conda environment first
    if in_conda_env; then
        print_color $GREEN "✅ Using conda environment: $CONDA_DEFAULT_ENV"
        return 0
    elif [[ -d "venv" ]]; then
        print_color $GREEN "✅ Virtual environment found (venv)"
        return 0
    elif [[ -d ".venv" ]]; then
        print_color $GREEN "✅ Virtual environment found (.venv)"
        return 0
    else
        if check_conda; then
            print_color $YELLOW "⚠️  Using conda base environment (recommend creating dedicated env)"
        else
            print_color $YELLOW "⚠️  No virtual environment found"
        fi
        return 1
    fi
}

# Function to activate virtual environment
activate_venv() {
    if in_conda_env; then
        print_color $GREEN "✅ Using conda environment: $CONDA_DEFAULT_ENV"
    elif [[ -d "venv" ]]; then
        source venv/bin/activate
        print_color $GREEN "✅ Activated virtual environment (venv)"
    elif [[ -d ".venv" ]]; then
        source .venv/bin/activate
        print_color $GREEN "✅ Activated virtual environment (.venv)"
    else
        if check_conda; then
            print_color $YELLOW "ℹ️  Using conda base environment"
        else
            print_color $YELLOW "ℹ️  No virtual environment to activate"
        fi
    fi
}

# Function to create virtual environment
create_venv() {
    if check_conda; then
        print_color $BLUE "🔧 Conda detected. Creating conda environment for AIFEED..."
        conda create -n aifeed python=3.11 -y
        print_color $GREEN "✅ Conda environment 'aifeed' created"
        print_color $CYAN "To use it, run: conda activate aifeed"
        print_color $YELLOW "Or use './start.sh conda' to activate and run"
    else
        print_color $BLUE "🔧 Creating virtual environment..."
        $PYTHON_CMD -m venv venv
        source venv/bin/activate
        print_color $GREEN "✅ Virtual environment created and activated"
    fi
}

# Function to activate conda environment
activate_conda() {
    if check_conda; then
        print_color $BLUE "🔧 Activating conda environment 'aifeed'..."
        eval "$(conda shell.bash hook)"
        conda activate aifeed
        print_color $GREEN "✅ Activated conda environment: aifeed"
    else
        print_color $RED "❌ Conda not found"
        exit 1
    fi
}

# Function to install dependencies
install_deps() {
    print_color $BLUE "📦 Installing/updating dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    print_color $GREEN "✅ Dependencies installed successfully"
}

# Function to setup environment
setup_env() {
    print_color $BLUE "🔧 Setting up AIFEED environment..."
    
    # Check for .env file
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.example" ]]; then
            cp .env.example .env
            print_color $GREEN "✅ Created .env file from .env.example"
            print_color $YELLOW "⚠️  Please edit .env file to add your API keys!"
        else
            print_color $RED "❌ No .env.example file found"
            print_color $YELLOW "You'll need to create a .env file with your API keys"
        fi
    else
        print_color $GREEN "✅ .env file already exists"
    fi
    
    # Run setup command
    $PYTHON_CMD run.py setup
}

# Function to start the dashboard
start_dashboard() {
    print_color $BLUE "🚀 Starting AIFEED Dashboard..."
    print_color $CYAN "Dashboard will open in your web browser"
    print_color $YELLOW "Press Ctrl+C to stop the dashboard"
    echo
    $PYTHON_CMD run.py run
}

# Function to start the scheduler
start_scheduler() {
    print_color $BLUE "⏰ Starting AIFEED Background Scheduler..."
    print_color $CYAN "Scheduler will refresh data automatically every hour"
    print_color $YELLOW "Press Ctrl+C to stop the scheduler"
    echo
    $PYTHON_CMD run.py scheduler
}

# Function to refresh data once
refresh_data() {
    print_color $BLUE "🔄 Refreshing data from all sources..."
    $PYTHON_CMD run.py refresh
    print_color $GREEN "✅ Data refresh completed"
}

# Function to show database stats
show_stats() {
    print_color $BLUE "📊 Database Statistics:"
    $PYTHON_CMD run.py stats
}

# Function to backup database
backup_db() {
    print_color $BLUE "💾 Creating database backup..."
    $PYTHON_CMD run.py backup
    print_color $GREEN "✅ Database backup completed"
}

# Function to run tests
run_tests() {
    print_color $BLUE "🧪 Running test suite..."
    $PYTHON_CMD run.py test
}

# Function to show help
show_help() {
    print_color $CYAN "
📖 AIFEED Commands:

Basic Usage:
  ./start.sh                    - Quick start (setup + run dashboard)
  ./start.sh run                - Start the dashboard
  ./start.sh scheduler          - Start background scheduler

Setup & Management:
  ./start.sh setup              - Setup environment and dependencies
  ./start.sh install            - Install/update dependencies only
  ./start.sh refresh            - Refresh data once
  ./start.sh stats              - Show database statistics
  ./start.sh backup             - Backup database
  ./start.sh test               - Run tests

Development:
  ./start.sh dev                - Development mode (auto-reload)
  ./start.sh clean              - Clean cache and temporary files

Environment:
  ./start.sh venv               - Create virtual environment
  ./start.sh conda              - Create/use conda environment
  ./start.sh check              - Check system requirements

Other:
  ./start.sh help               - Show this help
  ./start.sh version            - Show version info
"
}

# Function to check system requirements
check_requirements() {
    print_color $BLUE "🔍 Checking system requirements..."
    
    # Check Python version
    if command -v $PYTHON_CMD &> /dev/null; then
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
        print_color $GREEN "✅ $PYTHON_VERSION"
    else
        print_color $RED "❌ Python not found"
    fi
    
    # Check pip
    if command -v pip &> /dev/null; then
        PIP_VERSION=$(pip --version 2>&1)
        print_color $GREEN "✅ $PIP_VERSION"
    else
        print_color $RED "❌ pip not found"
    fi
    
    # Check conda
    if check_conda; then
        CONDA_VERSION=$(conda --version 2>&1)
        print_color $GREEN "✅ $CONDA_VERSION"
        if in_conda_env; then
            print_color $GREEN "✅ Active conda environment: $CONDA_DEFAULT_ENV"
        else
            print_color $CYAN "ℹ️  In conda base environment"
        fi
    else
        print_color $YELLOW "⚠️  conda not found (will use venv)"
    fi
    
    # Check git
    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version 2>&1)
        print_color $GREEN "✅ $GIT_VERSION"
    else
        print_color $YELLOW "⚠️  git not found (optional)"
    fi
    
    # Check virtual environment
    if check_venv; then
        print_color $GREEN "✅ Virtual environment available"
    else
        print_color $YELLOW "⚠️  No virtual environment (will create one)"
    fi
    
    # Check .env file
    if [[ -f ".env" ]]; then
        print_color $GREEN "✅ .env file exists"
    else
        print_color $YELLOW "⚠️  .env file not found (will create from example)"
    fi
    
    # Check database
    if [[ -f "aifeed.db" ]]; then
        DB_SIZE=$(du -h aifeed.db | cut -f1)
        print_color $GREEN "✅ Database exists ($DB_SIZE)"
    else
        print_color $YELLOW "ℹ️  Database will be created on first run"
    fi
}

# Function to show version info
show_version() {
    print_color $BLUE "📋 AIFEED Version Information:"
    
    if [[ -f "README.md" ]]; then
        if grep -q "version" README.md; then
            VERSION=$(grep -i version README.md | head -1)
            print_color $GREEN "✅ $VERSION"
        fi
    fi
    
    print_color $CYAN "🗓  Last updated: $(date -r . 2>/dev/null || date)"
    
    if command -v git &> /dev/null && [[ -d ".git" ]]; then
        COMMIT=$(git rev-parse --short HEAD 2>/dev/null)
        if [[ $? -eq 0 ]]; then
            print_color $CYAN "📝 Git commit: $COMMIT"
        fi
    fi
}

# Function for development mode
dev_mode() {
    print_color $BLUE "🔧 Starting AIFEED in development mode..."
    print_color $YELLOW "Note: This will start the dashboard with auto-reload enabled"
    
    # Check if streamlit is available
    if command -v streamlit &> /dev/null; then
        streamlit run app.py --server.runOnSave true
    else
        print_color $RED "❌ Streamlit not found. Installing..."
        pip install streamlit
        streamlit run app.py --server.runOnSave true
    fi
}

# Function to clean cache and temporary files
clean_cache() {
    print_color $BLUE "🧹 Cleaning cache and temporary files..."
    
    # Remove Python cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    # Remove pytest cache
    rm -rf .pytest_cache 2>/dev/null || true
    
    # Remove any temporary files
    rm -rf temp/ tmp/ 2>/dev/null || true
    
    print_color $GREEN "✅ Cache cleaned"
}

# Main function
main() {
    print_banner
    
    # Check Python availability
    check_python
    
    # Parse command line arguments
    case "${1:-}" in
        "run")
            if check_venv; then
                activate_venv
            fi
            start_dashboard
            ;;
        "scheduler")
            if check_venv; then
                activate_venv
            fi
            start_scheduler
            ;;
        "setup")
            if ! check_venv; then
                create_venv
            else
                activate_venv
            fi
            install_deps
            setup_env
            ;;
        "install")
            if check_venv; then
                activate_venv
            fi
            install_deps
            ;;
        "refresh")
            if check_venv; then
                activate_venv
            fi
            refresh_data
            ;;
        "stats")
            if check_venv; then
                activate_venv
            fi
            show_stats
            ;;
        "backup")
            if check_venv; then
                activate_venv
            fi
            backup_db
            ;;
        "test")
            if check_venv; then
                activate_venv
            fi
            run_tests
            ;;
        "dev")
            if check_venv; then
                activate_venv
            fi
            dev_mode
            ;;
        "clean")
            clean_cache
            ;;
        "venv")
            create_venv
            ;;
        "conda")
            if check_conda; then
                if conda env list | grep -q "aifeed"; then
                    activate_conda
                    install_deps
                    start_dashboard
                else
                    create_venv
                    print_color $YELLOW "Please run: conda activate aifeed && ./start.sh install && ./start.sh run"
                fi
            else
                print_color $RED "❌ Conda not found"
                exit 1
            fi
            ;;
        "check")
            check_requirements
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        "version"|"-v"|"--version")
            show_version
            ;;
        "")
            # Default: Quick start
            print_color $YELLOW "🚀 Quick Start Mode"
            if ! check_venv; then
                if check_conda; then
                    print_color $CYAN "🐍 Conda detected! Recommend using: ./start.sh conda"
                    print_color $BLUE "Or continuing with regular venv setup..."
                fi
                print_color $BLUE "Setting up for first time..."
                create_venv
                if [[ ! -d "venv" ]] && [[ ! -d ".venv" ]]; then
                    print_color $YELLOW "Environment created. Please activate it and rerun:"
                    if check_conda; then
                        print_color $CYAN "conda activate aifeed && ./start.sh"
                    fi
                    exit 0
                fi
                install_deps
                setup_env
                print_color $GREEN "✅ Setup completed!"
                echo
            else
                activate_venv
            fi
            start_dashboard
            ;;
        *)
            print_color $RED "❌ Unknown command: $1"
            echo
            show_help
            exit 1
            ;;
    esac
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi