#!/bin/bash

# Email Dispatcher Installation Script
# This script will install dependencies and set up the environment

set -e

echo "🚀 Email Dispatcher Installation Script"
echo "======================================"

# Check Python version
echo "📋 Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✅ Python $PYTHON_VERSION found"
else
    echo "❌ Python 3 not found. Please install Python 3.8+ first."
    exit 1
fi

# Check pip
echo "📦 Checking pip..."
if command -v pip3 &> /dev/null; then
    echo "✅ pip3 found"
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    echo "✅ pip found"
    PIP_CMD="pip"
else
    echo "❌ pip not found. Please install pip first."
    exit 1
fi

# Install dependencies
echo "📥 Installing dependencies..."
$PIP_CMD install -r requirements.txt

# Verify installation
echo "🔍 Verifying installation..."
python3 -c "
try:
    import faker
    import socks
    print('✅ Dependencies installed successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p data
mkdir -p templates

# Check if config exists
if [ ! -f "email_config.ini" ]; then
    echo "📝 No configuration file found."
    echo "💡 Run the interactive setup wizard:"
    echo "   python3 run_interactive.py"
else
    echo "✅ Configuration file found"
fi

# Check if data files exist
if [ ! -f "data/leads.txt" ]; then
    echo "📝 Creating sample leads file..."
    echo "test@example.com" > data/leads.txt
    echo "✅ Created data/leads.txt with sample data"
fi

if [ ! -f "data/placeholders.txt" ]; then
    echo "📝 Creating sample placeholders file..."
    cat > data/placeholders.txt << EOF
company=Acme Corporation
product=Widget Pro
offer=50% off
EOF
    echo "✅ Created data/placeholders.txt with sample data"
fi

if [ ! -f "templates/message.html" ]; then
    echo "📝 Creating sample template..."
    cat > templates/message.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Email from {company}</title>
</head>
<body>
    <h1>Hello {recipient}!</h1>
    <p>Welcome to {company}. We have a special offer: {offer} on {product}!</p>
    <p>Best regards,<br>{full_name}</p>
</body>
</html>
EOF
    echo "✅ Created templates/message.html with sample template"
fi

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "📚 Next steps:"
echo "1. Configure your email settings:"
echo "   python3 run_interactive.py"
echo ""
echo "2. Test your configuration:"
echo "   python3 main.py --dry-run"
echo ""
echo "3. View help:"
echo "   python3 main.py --help"
echo ""
echo "📖 For detailed documentation, see README.md"
echo ""
echo "Happy emailing! 🚀"

