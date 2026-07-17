# Hytale Coordinate Finder Prototype

This is a working prototype that automatically hooks into `HytaleClient.exe` to extract the player's live Position, Target Block coordinates, and Camera Orientation in real-time.

## How It Works
The script uses **Frida** to dynamically inject into the game's engine at runtime. It specifically hooks two functions:
1. `0x42808C` - Player Position and Camera Pitch/Yaw.
2. `0x6F31AE` - Target Block raycast coordinates.

The extracted floats are instantly formatted and displayed in a translucent, frameless PyQt6 overlay that sits on top of your screen.

## Requirements
- Python 3.9+
- `pip install frida PyQt6`

## How to Run
1. Launch `HytaleClient.exe` and enter a world.
2. Double-click `start.bat` (this runs the python script with administrator privileges, which is required for Frida to inject into the game).
3. The overlay will appear!

## Files
- `target_block_ui.py`: The main script that handles the PyQt6 UI and the Frida JavaScript injection payload.
- `memio.py` & `memio_win.py`: Helper scripts that securely locate the `HytaleClient.exe` process ID.
- `start.bat`: A simple batch file to quickly launch the UI.

## Using this for Chat Commands
Since this cleanly extracts the exact X, Y, Z coordinates of the block you are looking at, you can easily adapt this script to automatically type a command like `/spawnblock X Y Z` directly into the chat, allowing the server to handle the block spawning natively without needing to parse Block IDs client-side!
