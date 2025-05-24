#!/usr/bin/env python3
"""
AIFEED Launcher Script
This script provides commands to run the AIFEED dashboard,
refresh data without launching the dashboard, or perform setup.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from utils import logger

def get_project_root():
    """Returns the absolute path to the project root directory."""
    return Path(__file__).parent.absolute()

def setup_environment():
    """Set up the environment by creating .env if it doesn't exist."""
    env_example_path = get_project_root() / ".env.example"
    env_path = get_project_root() / ".env"
    
    if not env_path.exists() and env_example_path.exists():
        logger.info("Creating .env file from .env.example...")
        with open(env_example_path, 'r') as example_file:
            content = example_file.read()
        
        with open(env_path, 'w') as env_file:
            env_file.write(content)
        
        logger.info(".env file created. Please edit it to add your API keys.")
    elif not env_example_path.exists():
        logger.error("Error: .env.example file not found.")
    else:
        logger.info(".env file already exists.")

def install_dependencies():
    """Install required dependencies."""
    requirements_path = get_project_root() / "requirements.txt"
    
    if requirements_path.exists():
        logger.info("Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_path)])
        logger.info("Dependencies installed successfully.")
    else:
        logger.error("Error: requirements.txt file not found.")

def refresh_data():
    """Refresh data without launching the dashboard."""
    from data_manager import DataManager
    
    logger.info("Refreshing data...")
    manager = DataManager()
    result = manager.refresh_data()
    if result.get('status') == 'success':
        logger.info("Data refresh completed successfully.")
    else:
        logger.error("Data refresh encountered issues.")

def run_scheduler():
    """Start the background data refresh scheduler."""
    scheduler_script_path = get_project_root() / "scheduler.py"
    if scheduler_script_path.exists():
        logger.info("Starting AIFEED background scheduler...")
        try:
            # Import and run the scheduler
            import subprocess
            subprocess.run([sys.executable, str(scheduler_script_path)])
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user.")
        except Exception as e:
            logger.error(f"Error running scheduler: {e}", exc_info=True)
    else:
        logger.error("Error: scheduler.py file not found.")

def clear_database():
    """Delete and re-initialize the database (USE WITH CAUTION)."""
    from utils import DB_PATH, initialize_db
    
    if DB_PATH.exists():
        confirm = input(f"Are you sure you want to DELETE the database at {DB_PATH}? This will remove all stored data! (yes/no): ")
        if confirm.lower() == 'yes':
            try:
                os.remove(DB_PATH)
                logger.info("Database deleted successfully.")
                # Re-initialize empty database
                initialize_db()
                logger.info("Empty database initialized.")
            except Exception as e:
                logger.error(f"Failed to delete database: {e}", exc_info=True)
        else:
            logger.info("Database deletion cancelled.")
    else:
        logger.info("Database file not found. Nothing to delete.")

def backup_data():
    """Create a backup of the current database."""
    from utils import DB_PATH
    import shutil
    from datetime import datetime
    
    if DB_PATH.exists():
        backup_name = f"aifeed_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = get_project_root() / backup_name
        try:
            shutil.copy2(DB_PATH, backup_path)
            logger.info(f"Database backed up to: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to backup database: {e}", exc_info=True)
    else:
        logger.info("Database file not found. Nothing to backup.")

def show_stats():
    """Display statistics about the current database."""
    from data_manager import DataManager
    from utils import get_db_connection
    
    try:
        manager = DataManager()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get item counts by type
        cursor.execute("SELECT content_type, COUNT(*) as count FROM items GROUP BY content_type")
        counts = cursor.fetchall()
        
        # Get total items
        cursor.execute("SELECT COUNT(*) as total FROM items")
        total = cursor.fetchone()['total']
        
        # Get bookmarked count
        cursor.execute("SELECT COUNT(*) as bookmarked FROM items WHERE bookmarked = 1")
        bookmarked = cursor.fetchone()['bookmarked']
        
        # Get latest update
        cursor.execute("SELECT MAX(processed_at) as last_update FROM items")
        last_update = cursor.fetchone()['last_update']
        
        conn.close()
        
        logger.info("=== AIFEED Database Statistics ===")
        logger.info(f"Total items: {total}")
        logger.info(f"Bookmarked items: {bookmarked}")
        logger.info(f"Last update: {last_update}")
        logger.info("\nItems by type:")
        for row in counts:
            logger.info(f"  {row['content_type']}: {row['count']}")
            
    except Exception as e:
        logger.error(f"Error getting statistics: {e}", exc_info=True)

def run_tests():
    """Run the test suite."""
    import subprocess
    
    tests_path = get_project_root() / "tests"
    if tests_path.exists():
        logger.info("Running AIFEED test suite...")
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", str(tests_path), "-v"
            ], capture_output=True, text=True)
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
                
            if result.returncode == 0:
                logger.info("All tests passed!")
            else:
                logger.error(f"Tests failed with return code {result.returncode}")
                
        except Exception as e:
            logger.error(f"Error running tests: {e}", exc_info=True)
    else:
        logger.error("Tests directory not found.")

def run_dashboard():
    """Launch the Streamlit dashboard."""
    app_path = get_project_root() / "app.py"
    
    if app_path.exists():
        logger.info("Launching AIFEED dashboard...")
        # Change working directory to project root to ensure all paths work correctly
        os.chdir(get_project_root())
        subprocess.run(["streamlit", "run", str(app_path)])
    else:
        logger.error("Error: app.py file not found.")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="AIFEED - AI Intelligence Dashboard")
    
    # Add commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run the AIFEED dashboard")
    
    # Refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Refresh data without launching the dashboard")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up the environment and install dependencies")
    
    # Scheduler command
    scheduler_parser = subparsers.add_parser("scheduler", help="Start the background data refresh scheduler")
    
    # Database management commands
    clear_db_parser = subparsers.add_parser("clear-db", help="Delete and re-initialize the database (USE WITH CAUTION)")
    backup_parser = subparsers.add_parser("backup", help="Create a backup of the current database")
    stats_parser = subparsers.add_parser("stats", help="Display database statistics")
    
    # Testing command
    test_parser = subparsers.add_parser("test", help="Run the test suite")
    
    args = parser.parse_args()
    
    # Process commands
    if args.command == "run":
        run_dashboard()
    elif args.command == "refresh":
        refresh_data()
    elif args.command == "setup":
        setup_environment()
        install_dependencies()
    elif args.command == "scheduler":
        run_scheduler()
    elif args.command == "clear-db":
        clear_database()
    elif args.command == "backup":
        backup_data()
    elif args.command == "stats":
        show_stats()
    elif args.command == "test":
        run_tests()
    else:
        # Default to running the dashboard if no command is specified
        run_dashboard()

if __name__ == "__main__":
    main()