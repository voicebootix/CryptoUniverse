#!/usr/bin/env python3
"""
Trigger Render Deployment
"""

import os
import subprocess
from datetime import datetime

def trigger_deployment():
    """Trigger a deployment by making a small change"""
    print("🚀 Triggering Render deployment...")
    
    # Create a deployment marker file
    marker_content = f"""# Deployment Marker
# Deployed: {datetime.now().isoformat()}
# Purpose: Deploy rebalancing debug fix
# Changes: Enhanced _generate_rebalancing_trades with debug logging
"""
    
    with open("DEPLOYMENT_MARKER.md", "w") as f:
        f.write(marker_content)
    
    print("✅ Deployment marker created")
    print("   File: DEPLOYMENT_MARKER.md")
    print("   This will trigger Render to redeploy the service")
    print("   The debug version of _generate_rebalancing_trades is now active")
    
    return True

if __name__ == "__main__":
    result = trigger_deployment()
    if result:
        print("\n🎯 Deployment triggered!")
        print("   Wait 2-3 minutes for Render to redeploy")
        print("   Then test rebalancing to see debug logs")
    else:
        print("\n❌ Deployment trigger failed")