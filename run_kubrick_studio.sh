#!/bin/bash
# Kubrick Studio Launcher Script
# Run this to start your personal video editing studio

set -e

echo "╔═══════════════════════════════════════════════════════╗"
echo "║         KUBRICK STUDIO - Starting Up...              ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

# Check if FFmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg not found. Please install FFmpeg first."
    echo "   macOS: brew install ffmpeg"
    echo "   Linux: sudo apt install ffmpeg"
    echo "   Windows: Download from ffmpeg.org"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
fi

# Install dependencies if needed
if ! python3 -c "import kubrick" 2>/dev/null; then
    echo "📦 Installing Kubrick dependencies..."
    pip install -e ".[all]" --quiet
fi

# Launch the studio
echo ""
python3 kubrick_studio.py
