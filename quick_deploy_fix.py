#!/usr/bin/env python3
"""
Quick deployment fix script for production issues.
"""
import subprocess
import sys
import os

def run_command(cmd):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ SUCCESS: {cmd}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ FAILED: {cmd}")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main deployment fix."""
    print("🚀 Starting quick deployment fix...")
    
    # Change to project directory
    os.chdir(os.path.dirname(__file__))
    
    # Add all changes
    if not run_command("git add -A"):
        sys.exit(1)
    
    # Commit changes
    if not run_command('git commit -m "PRODUCTION FIX: API endpoints, database imports, frontend null-safe"'):
        print("⚠️  No changes to commit or commit failed")
    
    # Push to deploy
    if not run_command("git push origin main"):
        sys.exit(1)
    
    print("🎉 Deployment fix completed! Check render logs in 2-3 minutes.")

if __name__ == "__main__":
    main()
