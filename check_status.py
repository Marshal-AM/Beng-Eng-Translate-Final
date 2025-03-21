#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

def check_credential_files():
    """Check if all required credential files exist and are properly formatted."""
    print("\n=== Checking Credential Files ===\n")
    
    script_dir = Path(__file__).parent.absolute()
    
    # Check .env file for OpenAI API key
    env_path = script_dir / ".env"
    if not env_path.exists():
        print("❌ .env file not found")
        print("   Create a .env file with your OpenAI API key:\n")
        print("   OPENAI_API_KEY=your_openai_api_key_here\n")
    else:
        print("✅ .env file found")
        load_dotenv(env_path)
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("❌ OPENAI_API_KEY not found in .env file")
        elif openai_key == "your_openai_api_key_here":
            print("❌ OPENAI_API_KEY is set to the default value. Please update it.")
        else:
            masked_key = openai_key[:6] + "..." + openai_key[-4:]
            print(f"✅ OPENAI_API_KEY found: {masked_key}")
    
    # Check Google Cloud credentials file
    creds_path = script_dir / "creds.json"
    if not creds_path.exists():
        print("❌ creds.json not found")
        print("   Create a creds.json file with your Google Cloud credentials")
    else:
        print("✅ creds.json file found")
        try:
            with open(creds_path, 'r') as f:
                creds_data = json.load(f)
            
            # Check required fields
            required_fields = ["type", "project_id", "private_key", "client_email"]
            missing_fields = [field for field in required_fields if field not in creds_data]
            
            if missing_fields:
                print(f"❌ Missing fields in creds.json: {', '.join(missing_fields)}")
            else:
                print("✅ creds.json contains all required fields")
                
                # Check for default placeholder values
                if creds_data.get("project_id") == "your-project-id":
                    print("❌ Google Cloud project_id is set to the default value. Please update it.")
                else:
                    print(f"✅ Google Cloud project_id: {creds_data.get('project_id')}")
                
                client_email = creds_data.get("client_email", "")
                if "your-service-account" in client_email:
                    print("❌ Service account email is set to the default value. Please update it.")
                else:
                    print(f"✅ Service account email: {client_email}")
        except json.JSONDecodeError:
            print("❌ creds.json is not valid JSON")
        except Exception as e:
            print(f"❌ Error reading creds.json: {str(e)}")
    
    print("\n=== Port Availability Check ===\n")
    
    # Check if ports 8000 and 8765 are available
    import socket
    
    def check_port(port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("localhost", port))
            s.close()
            return True
        except:
            return False
    
    if check_port(8000):
        print("✅ Port 8000 is available for the HTTP server")
    else:
        print("❌ Port 8000 is already in use. The HTTP server may not start properly.")
    
    if check_port(8765):
        print("✅ Port 8765 is available for the WebSocket server")
    else:
        print("❌ Port 8765 is already in use. The WebSocket server may not start properly.")
    
    print("\n=== Python Dependencies Check ===\n")
    
    try:
        import pipecat
        print(f"✅ Pipecat library installed (version: {pipecat.__version__})")
    except ImportError:
        print("❌ Pipecat library not installed. Please install it with 'pip install pipecat-ai'")
    
    try:
        import websockets
        print("✅ Websockets library installed")
    except ImportError:
        print("❌ Websockets library not installed. Please install it with 'pip install websockets'")
    
    try:
        import google.cloud.speech
        print("✅ Google Cloud Speech library installed")
    except ImportError:
        print("❌ Google Cloud Speech library not installed. Please install it with 'pip install google-cloud-speech'")
    
    try:
        import google.cloud.texttospeech
        print("✅ Google Cloud Text-to-Speech library installed")
    except ImportError:
        print("❌ Google Cloud Text-to-Speech library not installed. Please install it with 'pip install google-cloud-texttospeech'")
    
    print("\n=== Summary ===\n")
    print("After fixing any issues above, try running the application with:")
    print("  python server.py")
    print("\nOr using the provided launcher script:")
    print("  ./run.sh (on macOS/Linux)")
    print("  run.bat (on Windows)")
    print("\nThen visit http://localhost:8000 in your browser")

if __name__ == "__main__":
    print("\n=== Voice Translation App Status Check ===\n")
    print("This script checks if your environment is properly set up to run the Voice Translation application.")
    check_credential_files() 