#!/usr/bin/env python3
"""
Script to create a temporary public URL for testing with Claude Custom Connectors
This uses a simple HTTP tunnel service to expose your local server
"""

import subprocess
import sys
import time
import requests

def check_server_running():
    """Check if the local server is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    print("🚀 Setting up temporary public URL for Claude testing")
    print("=" * 50)

    # Check if local server is running
    if not check_server_running():
        print("❌ Local server is not running on port 8000")
        print("Start your server first with: python claude_connector_server.py")
        return

    print("✅ Local server detected on port 8000")
    print()

    # Instructions for using different tunnel services
    print("To test with Claude Custom Connectors, you need to expose your local server.")
    print("Here are a few options:")
    print()

    print("🌐 Option 1: Using ngrok (free, requires signup)")
    print("   1. Install ngrok: https://ngrok.com/download")
    print("   2. Run: ngrok http 8000")
    print("   3. Use the HTTPS URL (e.g., https://abcd1234.ngrok.io)")
    print("   4. Add '/mcp' to the end for Claude (e.g., https://abcd1234.ngrok.io/mcp)")
    print()

    print("🌐 Option 2: Using Cloudflare Tunnel (free)")
    print("   1. Install cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/")
    print("   2. Run: cloudflared tunnel --url http://localhost:8000")
    print("   3. Use the provided URL + '/mcp'")
    print()

    print("🌐 Option 3: Using localtunnel (npm required)")
    print("   1. Install: npm install -g localtunnel")
    print("   2. Run: lt --port 8000")
    print("   3. Use the provided URL + '/mcp'")
    print()

    print("📋 Test checklist once you have a public URL:")
    print("✓ Add integration in Claude with your-url/mcp")
    print("✓ Click Connect to test OAuth flow")
    print("✓ Verify tools appear in Claude")
    print("✓ Test a transaction query")
    print()

    print("🔍 Your local server supports:")
    print("✓ Dynamic Client Registration (RFC 7591)")
    print("✓ OAuth 2.1 with PKCE")
    print("✓ Proper WWW-Authenticate headers")
    print("✓ Refresh token support")
    print("✓ MCP 2025-06-18 specification")

if __name__ == "__main__":
    main()