"""
Main entry point for EchoAI FastAPI application.

This script starts the FastAPI server with proper environment configuration
and handles all the necessary setup for the voice chat system.
"""

from src.api.main import run_server

def main():
    """Main function to start the FastAPI server."""   
    run_server()

if __name__ == "__main__":
    main() 