# Hytale Coordinate Finder: How It Works

This document serves as a technical deep-dive into the memory architecture of `HytaleClient.exe` that we discovered during the development of this prototype. It explains exactly how we extract player and world data in real-time.

## The Chromium (CEF) UI Discovery
One of the most significant discoveries was realizing why standard memory scanners (like Cheat Engine) fail to find in-game text, such as block names (e.g., `Soil_Grass`) or the F7 debug menu text. 

Hytale does not render its UI natively within the main game client. Instead, it uses an embedded Chromium web browser (CEF / HTML / JavaScript) for its user interface. Because of this, all UI strings and text are passed via IPC to a completely separate background process (like a `cef_process.exe`). Scanning `HytaleClient.exe` for UI text will always fail because the text literally isn't there!

## 1. Player Position & Orientation Hook
To find the player's exact position and camera rotation, we hooked the game engine's internal position update function.

- **Hook Address:** `HytaleClient.exe + 0x42808C`
- **Target Register:** `RBX` (Points to the Player Data Structure)

By exploring the memory surrounding the `RBX` pointer, we successfully mapped out the following offsets:
* `RBX + 0x24` = Player X Coordinate (32-bit Float)
* `RBX + 0x28` = Player Y Coordinate (32-bit Float)
* `RBX + 0x2C` = Player Z Coordinate (32-bit Float)
* `RBX + 0x3C` = Camera Pitch (32-bit Float, stored in Radians)
* `RBX + 0x40` = Camera Yaw (32-bit Float, stored in Radians)

*Note: The game engine calculates rotation purely in Radians. We multiply these values by `(180 / PI)` in our Python script to convert them into readable Degrees that perfectly match the F7 menu.*

## 2. Target Block (Raycast) Hook
To find the exact block the player's crosshair is currently looking at, we hooked into the game's raycast collision function.

- **Hook Address:** `HytaleClient.exe + 0x6F31AE`
- **Target Register:** `RCX` (Points to the Target Block Bounding Box)

By mapping the memory surrounding the `RCX` pointer, we extracted the targeted block's coordinates:
* `RCX + 0x00` = Target Block X Coordinate (32-bit Float)
* `RCX + 0x04` = Target Block Y Coordinate (32-bit Float)
* `RCX + 0x08` = Target Block Z Coordinate (32-bit Float)

### The Missing Block ID
During memory analysis, we discovered that the Raycast Bounding Box structure (pointed to by `RCX`) **does not** contain the actual Block ID (e.g., the ID for Grass vs. Marble). The structure we hooked purely defines the 3D geometry (X, Y, Z coordinates) for the raycast collision.

Because we have the exact Target Block coordinates, the easiest solution for server mods is to simply pass the `X, Y, Z` coordinates directly to the server. Since the server holds the master copy of the world, it can instantly look up the Block ID at those coordinates without the client needing to figure it out!
