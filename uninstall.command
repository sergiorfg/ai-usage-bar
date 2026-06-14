#!/bin/bash
# Double-click to remove AI Usage Bar's auto-start (does not delete the app files).
LABEL="com.usagebar.menubar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null
rm -f "$PLIST"

echo "Removed auto-start. The app will no longer launch at login."
echo "(If it is currently running, quit it from its menu: 'Salir'.)"
sleep 2
