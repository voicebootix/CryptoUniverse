#!/usr/bin/env python3
"""
Deploy the opportunity discovery fix to production.

This script will:
1. Commit the changes
2. Push to the repository
3. Trigger a Render deployment
"""

import subprocess
import os
import time

def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Success")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} - Failed")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - Exception: {str(e)}")
        return False

def main():
    print("🚀 Deploying Opportunity Discovery Fix")
    print("=====================================")
    
    # Check git status
    if not run_command("git status --porcelain", "Checking git status"):
        return
    
    # Add the changed file
    if not run_command("git add app/services/user_opportunity_discovery.py", "Adding changed files"):
        return
    
    # Commit the changes
    commit_message = """Fix opportunity discovery returning zero results

- Lowered signal strength thresholds for all strategies:
  - Spot momentum: 6.0 -> 4.0
  - Pairs trading: 5.0 -> 3.0  
  - Mean reversion: 2.0 -> 1.5 std deviations
  - Breakout probability: 0.75 -> 0.6
- Added fallback opportunities when no signals qualify
- Improved signal analysis logging

This ensures users see opportunities even with moderate market signals.
"""
    
    if not run_command(f'git commit -m "{commit_message}"', "Committing changes"):
        print("\n⚠️  If commit failed due to no changes, the fix might already be committed.")
    
    # Get current branch
    result = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True)
    branch = result.stdout.strip()
    print(f"\n📌 Current branch: {branch}")
    
    # Push to origin
    print("\n⚠️  About to push to remote repository...")
    print("This will trigger an automatic deployment on Render.")
    
    if run_command(f"git push origin {branch}", "Pushing to remote"):
        print("\n✅ Changes pushed successfully!")
        print("\n🎯 What happens next:")
        print("1. Render will detect the push and start building")
        print("2. The build usually takes 5-10 minutes")
        print("3. Once deployed, the new thresholds will be active")
        print("\n📊 To verify the fix after deployment:")
        print("   ./test_opportunity_api_fixed.sh")
    else:
        print("\n❌ Push failed. You may need to:")
        print("1. Set up git credentials")
        print("2. Pull latest changes: git pull origin main")
        print("3. Resolve any conflicts")
        print("4. Try pushing again")

if __name__ == "__main__":
    main()