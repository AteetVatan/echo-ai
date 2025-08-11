#!/usr/bin/env python3
"""
Development startup script for EchoAI Voice Chat System.

This script sets up the development environment and starts the FastAPI backend
with proper configuration for frontend integration.
"""

import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

def setup_environment():
    """Setup development environment."""
    print(" Setting up EchoAI development environment...")
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("  No .env file found. Creating from template...")
        if Path("env.example").exists():
            subprocess.run(["cp", "env.example", ".env"])
            print(" Created .env from env.example")
            print("  Please edit .env with your actual API keys before continuing")
            return False
        else:
            print(" No env.example found. Please create .env file manually")
            return False
    
    print(" Environment file found")
    return True

def check_dependencies():
    """Check if required dependencies are installed."""
    print(" Checking dependencies...")
    
    try:
        import fastapi
        import uvicorn
        print(" FastAPI and Uvicorn available")
    except ImportError:
        print(" FastAPI or Uvicorn not installed")
        print(" Run: pip install -r requirements.txt")
        return False
    
    return True

def start_backend():
    """Start the FastAPI backend server."""
    print("Starting FastAPI backend...")
    
    # Set development environment variables
    os.environ["DEBUG"] = "True"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    try:
        # Start the backend server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "src.api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "debug"
        ])
    except KeyboardInterrupt:
        print("\n Backend server stopped")
    except Exception as e:
        print(f" Failed to start backend: {e}")

def open_frontend():
    """Open the frontend in browser."""
    print("Opening frontend in browser...")
    
    # Wait a moment for server to start
    time.sleep(2)
    
    try:
        webbrowser.open("http://localhost:8000/frontend")
        print("Frontend opened in browser")
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
        print("Please open: http://localhost:8000/frontend")

def main():
    """Main development startup function."""
    print("=" * 60)
    print("EchoAI Voice Chat - Development Environment")
    print("=" * 60)
    
    # # Setup environment
    # if not setup_environment():
    #     print("\n Environment setup failed. Please fix and try again.")
    #     return
    
    # # Check dependencies
    # if not check_dependencies():
    #     print("\n Dependency check failed. Please install requirements.")
    #     return
    
    print("\n Environment ready!")
    print("\n Development URLs:")
    print("   Backend API: http://localhost:8000")
    print("   Frontend:   http://localhost:8000/frontend")
    print("   API Docs:   http://localhost:8000/docs")
    print("\n Features:")
    print("   • Hot reload enabled")
    print("   • Debug logging enabled")
    print("   • CORS configured for development")
    print("   • Static file serving for frontend")
    
    # Start backend
    try:
        start_backend()
    except KeyboardInterrupt:
        print("\n Development session ended")

if __name__ == "__main__":
    main()
