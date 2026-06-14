#!/bin/bash
# Double-click to install (or reinstall) AI Usage Bar and start it at login.
cd "$(dirname "$0")"
DIR="$(pwd)"
LABEL="com.usagebar.menubar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

BASEPY=$(command -v python3 || command -v python)
if [ -z "$BASEPY" ]; then
  echo "Python 3 not found. Install it from https://www.python.org/downloads/ and retry."
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

# Isolated virtualenv (does not touch your system Python or conda)
VENV="$DIR/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  "$BASEPY" -m venv "$VENV"
fi
PY="$VENV/bin/python"
"$PY" -m pip install --quiet --upgrade pip >/dev/null 2>&1
"$PY" -c "import rumps" 2>/dev/null || "$PY" -m pip install --quiet rumps

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PY</string>
        <string>$DIR/usage_bar.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/ai-usage-bar.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/ai-usage-bar.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || {
  launchctl unload "$PLIST" 2>/dev/null
  launchctl load "$PLIST" 2>/dev/null
}

echo "Installed. Look at the top-right of your menu bar, next to the clock."
echo "It will also start automatically every time you log in."
echo "To remove it, run uninstall.command."
sleep 2
