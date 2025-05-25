#!/usr/bin/env python3
"""
Script to clear saved Kroger API tokens.
"""

import os
import sys
import glob

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kroger_api.token_storage import clear_token


def main():
    """Clear all saved Kroger API tokens"""
    # Find all token files
    token_files = glob.glob(".kroger_token*")
    
    if not token_files:
        print("No token files found.")
        return
    
    # Ask for confirmation
    print(f"Found {len(token_files)} token files:")
    for file in token_files:
        print(f"  - {file}")
    
    confirm = input("\nDo you want to delete these files? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Delete token files
    for file in token_files:
        clear_token(file)
    
    print(f"\nAll {len(token_files)} token files have been deleted.")


if __name__ == "__main__":
    main()
