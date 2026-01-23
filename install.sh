#!/bin/bash

# Exit on any error
set -e

# Define source and destination directories
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install-extras"
CLAUDE_DEST_DIR="$HOME/.claude"
ANTIGRAVITY_DEST_DIR="$HOME/.antigravity"

# --- Claude Installation ---
CLAUDE_SKILLS_DEST="$CLAUDE_DEST_DIR/skills"
CLAUDE_AGENTS_DEST="$CLAUDE_DEST_DIR/agents"
CLAUDE_COMMANDS_DEST="$CLAUDE_DEST_DIR/commands"

echo "Installing for Claude..."

# Create destination directories if they don't exist
mkdir -p "$CLAUDE_SKILLS_DEST"
mkdir -p "$CLAUDE_AGENTS_DEST"
mkdir -p "$CLAUDE_COMMANDS_DEST"

# Copy skill
echo "Installing omni-search-engine skill..."
cp -R "$SOURCE_DIR/omni-search-engine" "$CLAUDE_SKILLS_DEST/"

# Copy agents
echo "Installing agents..."
cp "$SOURCE_DIR/agents/"* "$CLAUDE_AGENTS_DEST/"

# Copy commands
echo "Installing commands..."
cp "$SOURCE_DIR/commands/"* "$CLAUDE_COMMANDS_DEST/"

echo "Claude installation complete."

# --- Antigravity Installation ---
# The user mentioned antigravity, but the file structure doesn't show any antigravity-specific files.
# Adding a placeholder section in case this is needed later.
# For now, it will just create the directory.

ANTIGRAVITY_SKILLS_DEST="$ANTIGRAVITY_DEST_DIR/skills"
ANTIGRAVITY_AGENTS_DEST="$ANTIGRAVITY_DEST_DIR/agents"
ANTIGRAVITY_COMMANDS_DEST="$ANTIGRAVITY_DEST_DIR/commands"

echo "Installing for Antigravity..."

mkdir -p "$ANTIGRAVITY_SKILLS_DEST"
mkdir -p "$ANTIGRAVITY_AGENTS_DEST"
mkdir -p "$ANTIGRAVITY_COMMANDS_DEST"

# Example of what copying might look like if there were antigravity files.
# if [ -d "$SOURCE_DIR/antigravity/skills" ]; then
#     cp -R "$SOURCE_DIR/antigravity/skills/"* "$ANTIGRAVITY_SKILLS_DEST/"
# fi
# if [ -d "$SOURCE_DIR/antigravity/agents" ]; then
#     cp "$SOURCE_DIR/antigravity/agents/"* "$ANTIGRAVITY_AGENTS_DEST/"
# fi
# if [ -d "$SOURCE_DIR/antigravity/commands" ]; then
#     cp "$SOURCE_DIR/antigravity/commands/"* "$ANTIGRAVITY_COMMANDS_DEST/"
# fi


echo "Antigravity installation complete."

echo "Installation finished successfully!"
