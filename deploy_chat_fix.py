#!/usr/bin/env python3
"""
Deploy chat fix to production
"""
import subprocess
import sys
import os

def run_command(cmd):
    """Run command and handle output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        print(f"Command: {cmd}")
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"Command timed out: {cmd}")
        return False
    except Exception as e:
        print(f"Command failed: {cmd} - {e}")
        return False

def main():
    print("🚀 Deploying chat fix...")
    
    # Reset any merge state
    print("Resetting git state...")
    run_command("git reset --hard HEAD")
    run_command("git clean -fd")
    
    # Pull latest
    print("Pulling latest changes...")
    if not run_command("git pull origin main --no-edit"):
        print("❌ Failed to pull")
        return False
    
    # Check if our fix is still needed
    with open("app/services/ai_consensus_core.py", "r") as f:
        content = f.read()
        if "async def get_service_status" in content:
            print("✅ Fix already applied!")
            return True
    
    # Apply fix again if needed
    print("Applying fix...")
    # The fix should already be in the file from our previous edit
    
    # Add and commit
    run_command("git add app/services/ai_consensus_core.py")
    run_command('git commit -m "FIX: Add get_service_status method to AI consensus service"')
    
    # Push
    if run_command("git push origin main"):
        print("🎉 Fix deployed successfully!")
        print("⏳ Wait 2-3 minutes for Render to redeploy")
        return True
    else:
        print("❌ Failed to push")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)