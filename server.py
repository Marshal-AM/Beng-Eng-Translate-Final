#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import http.server
import json
import os
import signal
import socketserver
import subprocess
import sys
from pathlib import Path
import time
import socket

# Store active processes
active_processes = {}

# Store process logs
process_logs = {}

# Get the directory of this script
SCRIPT_DIR = Path(__file__).parent.absolute()
BOT_SCRIPT = SCRIPT_DIR / "bot.py"

class ServerRequestHandler(http.server.SimpleHTTPRequestHandler):
    def _set_response_headers(self, content_type="application/json"):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_response_headers()
        self.wfile.write(b'{}')

    def do_GET(self):
        # Serve static files
        if self.path == '/':
            self.path = '/index.html'
        
        try:
            # Check if file exists
            file_to_open = SCRIPT_DIR / self.path.lstrip('/')
            if file_to_open.exists():
                # Determine content type
                if self.path.endswith('.html'):
                    content_type = 'text/html'
                elif self.path.endswith('.js'):
                    content_type = 'application/javascript'
                elif self.path.endswith('.css'):
                    content_type = 'text/css'
                elif self.path.endswith('.json'):
                    content_type = 'application/json'
                elif self.path.endswith('.proto'):
                    content_type = 'application/protobuf'
                else:
                    content_type = 'application/octet-stream'
                
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                
                with open(file_to_open, 'rb') as file:
                    self.wfile.write(file.read())
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'404 - File Not Found')
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f'500 - Server Error: {str(e)}'.encode())

    def do_POST(self):
        if self.path == '/start-bot':
            self._start_bot()
        elif self.path == '/stop-bot':
            self._stop_bot()
        elif self.path == '/bot-logs':
            self._get_bot_logs()
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode())

    def _start_bot(self):
        try:
            # Check if port 8765 is in use
            def is_port_in_use(port):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    return s.connect_ex(('localhost', port)) == 0
            
            if is_port_in_use(8765):
                print("Port 8765 is in use, attempting to free it...")
                # Try to kill any process using port 8765
                if sys.platform == 'win32':
                    subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], capture_output=True)
                else:
                    try:
                        result = subprocess.run(['lsof', '-ti', ':8765'], capture_output=True, text=True)
                        if result.stdout:
                            port_pids = result.stdout.strip().split('\n')
                            for port_pid in port_pids:
                                try:
                                    os.kill(int(port_pid), signal.SIGKILL)
                                    print(f"Killed process {port_pid} using port 8765")
                                except ProcessLookupError:
                                    pass
                    except FileNotFoundError:
                        subprocess.run(['pkill', '-f', 'bot.py'], capture_output=True)
                
                # Wait a moment for the port to be freed
                time.sleep(1)
            
            # Check if Google Cloud credentials exist
            creds_path = SCRIPT_DIR / "creds.json"
            if not creds_path.exists():
                print(f"Google Cloud credentials file not found at {creds_path}")
                self._set_response_headers()
                self.wfile.write(json.dumps({
                    "success": False, 
                    "error": f"Google Cloud credentials file not found at {creds_path}. Please create this file with your Google Cloud credentials."
                }).encode())
                return
            
            # Check if .env file exists (for OpenAI API key)
            env_path = SCRIPT_DIR / ".env"
            if not env_path.exists():
                print(f".env file not found at {env_path}")
                self._set_response_headers()
                self.wfile.write(json.dumps({
                    "success": False, 
                    "error": f".env file not found at {env_path}. Please create this file with your OpenAI API key."
                }).encode())
                return

            # Start the bot.py process
            print(f"Starting bot.py from {SCRIPT_DIR}")
            process = subprocess.Popen(
                [sys.executable, str(BOT_SCRIPT)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=SCRIPT_DIR
            )
            
            pid = process.pid
            active_processes[pid] = process
            process_logs[pid] = {"stdout": [], "stderr": []}
            
            # Start non-blocking log reading threads
            def read_output(pipe, log_type, pid):
                for line in iter(pipe.readline, ''):
                    if pid in process_logs:
                        process_logs[pid][log_type].append(line.strip())
                pipe.close()
            
            import threading
            stdout_thread = threading.Thread(
                target=read_output,
                args=(process.stdout, "stdout", pid),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=read_output,
                args=(process.stderr, "stderr", pid),
                daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()
            
            # Poll the process to see if it's still running after a short delay
            time.sleep(0.5)
            if process.poll() is not None:
                # Process exited immediately
                output, error = process.communicate()
                print(f"Bot process exited immediately with code {process.returncode}")
                print(f"STDOUT: {output}")
                print(f"STDERR: {error}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False, 
                    "error": f"Bot failed to start (exit code {process.returncode}): {error}"
                }).encode())
                return
            
            print(f"Started bot.py process with PID: {pid}")
            
            self._set_response_headers()
            self.wfile.write(json.dumps({"success": True, "pid": pid}).encode())
            
        except Exception as e:
            print(f"Error starting bot.py: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

    def _stop_bot(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        pid = data.get('pid')
        force = data.get('force', False)
        force_port = data.get('force_port')
        
        try:
            if force_port:
                # Kill any process using the specified port
                if sys.platform == 'win32':
                    # On Windows
                    subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], capture_output=True)
                else:
                    # On Unix/Linux
                    try:
                        # Find process using port
                        result = subprocess.run(['lsof', '-ti', f':{force_port}'], capture_output=True, text=True)
                        if result.stdout:
                            port_pids = result.stdout.strip().split('\n')
                            for port_pid in port_pids:
                                try:
                                    os.kill(int(port_pid), signal.SIGKILL)
                                    print(f"Force killed process {port_pid} using port {force_port}")
                                except ProcessLookupError:
                                    pass
                    except FileNotFoundError:
                        # If lsof is not available, try a more aggressive approach
                        subprocess.run(['pkill', '-f', 'bot.py'], capture_output=True)
                
                self._set_response_headers()
                self.wfile.write(json.dumps({"success": True}).encode())
                return
            
            if not pid or pid not in active_processes:
                self._set_response_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Process not found"}).encode())
                return
            
            process = active_processes[pid]
            
            if force:
                # Force kill immediately
                if sys.platform == 'win32':
                    process.kill()
                else:
                    os.kill(pid, signal.SIGKILL)
                print(f"Force killed bot process with PID: {pid}")
            else:
                # Try graceful termination first
                if sys.platform == 'win32':
                    process.terminate()
                else:
                    os.kill(pid, signal.SIGTERM)
                    
                # Give it a moment to terminate
                try:
                    process.wait(timeout=3)
                    print(f"Successfully terminated bot process with PID: {pid}")
                except subprocess.TimeoutExpired:
                    # If it doesn't terminate, force kill
                    if sys.platform == 'win32':
                        process.kill()
                    else:
                        os.kill(pid, signal.SIGKILL)
                    print(f"Force killed bot process with PID: {pid}")
            
            del active_processes[pid]
            # Keep the logs in process_logs for viewing even after stopping
            
            self._set_response_headers()
            self.wfile.write(json.dumps({"success": True}).encode())
            
        except Exception as e:
            print(f"Error stopping bot.py (PID {pid}): {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

    def _get_bot_logs(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            pid = data.get('pid')
        else:
            pid = None
            
        if pid and pid in process_logs:
            logs = process_logs[pid]
            self._set_response_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "pid": pid,
                "stdout": logs["stdout"],
                "stderr": logs["stderr"]
            }).encode())
        elif not pid and process_logs:
            # Return logs for the most recently started process
            latest_pid = max(process_logs.keys())
            logs = process_logs[latest_pid]
            self._set_response_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "pid": latest_pid,
                "stdout": logs["stdout"],
                "stderr": logs["stderr"]
            }).encode())
        else:
            self._set_response_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "error": "No bot logs available"
            }).encode())


def cleanup():
    """Clean up any running processes when the server stops"""
    for pid, process in list(active_processes.items()):
        try:
            if sys.platform == 'win32':
                process.kill()
            else:
                os.kill(pid, signal.SIGKILL)
            print(f"Killed process {pid} during cleanup")
        except:
            pass


def main():
    try:
        port = 8000
        handler = ServerRequestHandler
        
        print(f"Starting server on port {port}...")
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"Server started at http://localhost:{port}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped by user.")
    finally:
        cleanup()


if __name__ == "__main__":
    main() 