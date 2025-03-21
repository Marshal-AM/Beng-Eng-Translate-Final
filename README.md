# Websocket Server Translation App

This is an example that shows how to use `WebsocketServerTransport` to create a real-time voice translation application.

## Features

- Real-time translation from Bengali to English
- Beautiful, intuitive UI with status indicators
- Start and stop the translation service with a click
- Auto-cleanup of resources when the application closes

## Setup

```python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Required Credentials

To run this example, you need two credential files:

1. **`.env` File**: Contains your OpenAI API key for translation:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

2. **`creds.json` File**: Contains your Google Cloud Service Account credentials for speech-to-text and text-to-speech services. You can download this from the Google Cloud Console.

Both files should be placed in the `examples/websocket-server` directory.

## Running the Application

### Option 1: Using the provided launcher script (Recommended)

On macOS/Linux:
```bash
./run.sh
```

On Windows:
```
run.bat
```

This will start the HTTP server on port 8000. Visit `http://localhost:8000` in your browser to start using the application.

### Option 2: Manual setup

First, start the HTTP server:

```bash
python server.py
```

Then, visit `http://localhost:8000` in your browser to use the application.

The bot.py process will be automatically started when you click "Start Speaking" and stopped when you click "Stop".

### Checking Your Setup

You can verify that your environment is properly set up by running:

```bash
python check_status.py
```

This will check:
- If all required credential files exist and are formatted correctly
- If ports 8000 and 8765 are available
- If all required Python dependencies are installed

Fix any issues reported before trying to run the application.

## Troubleshooting

### WebSocket Connection Issues

If you see WebSocket connection errors in the browser console:

1. **Check Credentials**: Ensure your `creds.json` and `.env` files are properly set up
2. **Port Conflicts**: Make sure port 8765 is available (this is used by the WebSocket server)
3. **Look at Server Logs**: The server terminal will show detailed logs when starting the bot
4. **Browser Console**: Check for more specific error messages in the browser's developer console
5. **Test Bot Directly**: Run `python bot.py` directly to see if there are any errors

### Google Cloud API Issues

If the bot starts but quickly fails:

1. Ensure your Google Cloud credentials have access to Speech-to-Text and Text-to-Speech APIs
2. Verify that the Google Cloud project has these APIs enabled
3. Check the `creds.json` file path in `bot.py` matches your actual file location

## How it works

The system consists of the following components:

1. **HTTP Server (server.py)**: Serves the web UI and provides endpoints to start/stop the bot.py process
2. **Bot Server (bot.py)**: Implements the WebSocket server that handles:
   - Speech-to-Text conversion (from Bengali)
   - Translation to English
   - Text-to-Speech conversion
3. **Web UI (index.html)**: Provides a user-friendly interface to interact with the system

When you click "Start Speaking", the frontend makes a request to start the bot.py process, then establishes a WebSocket connection to send audio data and receive translated speech.
