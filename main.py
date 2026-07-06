"""Entry point for the Garg Dental Operations Toolkit desktop app.

Run with: python3 main.py
"""
from app.app_shell import main
from app.logging_setup import configure_logging

if __name__ == "__main__":
    configure_logging()
    main()
