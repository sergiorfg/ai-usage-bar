#!/bin/bash
# Double-click to build a standalone "AI Usage Bar.app" (bundles Python inside).
# The resulting app needs NOTHING installed to run — just drag it to Applications.
cd "$(dirname "$0")"
APP_NAME="AI Usage Bar"
BUNDLE_ID="com.bouzlabs.aiusagebar"

BASEPY=$(command -v python3 || command -v python)
if [ -z "$BASEPY" ]; then
  echo "Python 3 is needed ONCE to build the app. Install from https://www.python.org/downloads/ and retry."
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

echo "Setting up a temporary build environment..."
BUILDVENV=".buildvenv"
"$BASEPY" -m venv "$BUILDVENV"
PY="$BUILDVENV/bin/python"
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet rumps pyinstaller

echo "Building $APP_NAME.app (this can take a minute)..."
rm -rf build "dist/$APP_NAME.app"
"$PY" -m PyInstaller --noconfirm --clean --windowed \
  --name "$APP_NAME" \
  --osx-bundle-identifier "$BUNDLE_ID" \
  usage_bar.py

PLIST="dist/$APP_NAME.app/Contents/Info.plist"
if [ -f "$PLIST" ]; then
  # Menu-bar only (no Dock icon)
  /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$PLIST"
fi

if [ -d "dist/$APP_NAME.app" ]; then
  echo ""
  echo "✅ Done -> dist/$APP_NAME.app"
  echo "   1. Drag it into your Applications folder."
  echo "   2. First launch: right-click the app -> Open -> Open (Gatekeeper, only once)."
  echo "   3. To start it at login: System Settings -> General -> Login Items -> +"
  open dist
else
  echo "❌ Build failed. See the output above."
fi
echo ""
read -n 1 -s -r -p "Press any key to close..."
