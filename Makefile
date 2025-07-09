# Verba MVP - Makefile for development and execution
# Usage: make <target>

.PHONY: help install test local-test clean lint format setup-env

# Default target
help:
	@echo "🎯 Verba MVP - Available Commands"
	@echo "================================="
	@echo "make install         - Install dependencies"
	@echo "make setup-env       - Set up environment file"
	@echo "make test           - Run tests"
	@echo "make test-coverage  - Run tests with coverage"
	@echo "make lint           - Check code quality"
	@echo "make format         - Format code"
	@echo "make local-test     - Run local pipeline test"
	@echo "make clean          - Clean temporary files"
	@echo "make docs           - Generate documentation"
	@echo ""
	@echo "Examples:"
	@echo "  make local-test URL=https://youtu.be/abc123"
	@echo "  make local-test URL=https://youtu.be/abc123 TITLE='Weekly Meeting'"
	@echo "  make test-coverage"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Set up environment file
setup-env:
	@echo "🔧 Setting up environment file..."
	@if [ ! -f .env ]; then \
		echo "Creating .env file from template..."; \
		echo "# Azure OpenAI Configuration" > .env; \
		echo "AZURE_OPENAI_KEY=your_azure_openai_key_here" >> .env; \
		echo "AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/" >> .env; \
		echo "AZURE_OPENAI_DEPLOYMENT=gpt-4o" >> .env; \
		echo "AZURE_OPENAI_API_VERSION=2024-02-01" >> .env; \
		echo "" >> .env; \
		echo "# Azure Translator Configuration" >> .env; \
		echo "AZURE_TRANSLATOR_KEY=your_azure_translator_key_here" >> .env; \
		echo "AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com" >> .env; \
		echo "AZURE_TRANSLATOR_REGION=eastus" >> .env; \
		echo "" >> .env; \
		echo "# Email Configuration (optional)" >> .env; \
		echo "SMTP_SERVER=smtp.gmail.com" >> .env; \
		echo "SMTP_PORT=587" >> .env; \
		echo "SMTP_USERNAME=your_email@gmail.com" >> .env; \
		echo "SMTP_PASSWORD=your_app_password" >> .env; \
		echo "" >> .env; \
		echo "# Performance Settings" >> .env; \
		echo "MAX_TOKENS_PER_CHUNK=7500" >> .env; \
		echo "MAX_PROCESSING_TIME=180" >> .env; \
		echo "✅ .env file created. Please edit it with your actual credentials."; \
	else \
		echo "⚠️  .env file already exists. Remove it first if you want to recreate it."; \
	fi

# Run tests
test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v
	@echo "✅ Tests completed"

# Run tests with coverage
test-coverage:
	@echo "🧪 Running tests with coverage..."
	python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing -v
	@echo "✅ Tests with coverage completed"
	@echo "📊 Coverage report generated in htmlcov/"

# Check code quality
lint:
	@echo "🔍 Checking code quality..."
	python -m flake8 src/ scripts/ tests/ --max-line-length=100 --ignore=E501,W503
	python -m mypy src/ --ignore-missing-imports
	@echo "✅ Code quality check completed"

# Format code
format:
	@echo "🎨 Formatting code..."
	python -m black src/ scripts/ tests/ --line-length=100
	@echo "✅ Code formatting completed"

# Run local pipeline test
local-test:
	@echo "🚀 Running local pipeline test..."
	@if [ -z "$(URL)" ]; then \
		echo "❌ Error: URL parameter is required"; \
		echo "Usage: make local-test URL=https://youtu.be/abc123"; \
		exit 1; \
	fi
	@echo "📺 Video URL: $(URL)"
	@if [ -n "$(TITLE)" ]; then \
		echo "📝 Title: $(TITLE)"; \
		python scripts/run_local.py "$(URL)" --title "$(TITLE)"; \
	else \
		python scripts/run_local.py "$(URL)"; \
	fi
	@echo "✅ Local test completed"

# Clean temporary files
clean:
	@echo "🧹 Cleaning temporary files..."
	rm -rf tmp/
	rm -rf output/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup completed"

# Generate documentation
docs:
	@echo "📚 Generating documentation..."
	@echo "Creating project documentation..."
	@mkdir -p docs
	@echo "# Verba MVP - Documentation" > docs/README.md
	@echo "" >> docs/README.md
	@echo "## Project Structure" >> docs/README.md
	@echo "" >> docs/README.md
	@echo "\`\`\`" >> docs/README.md
	@tree -I '__pycache__|*.pyc|.git|.venv|venv|env|ENV|htmlcov|.pytest_cache|tmp|output' >> docs/README.md 2>/dev/null || find . -type f -name "*.py" | head -20 >> docs/README.md
	@echo "\`\`\`" >> docs/README.md
	@echo "" >> docs/README.md
	@echo "## Modules" >> docs/README.md
	@echo "" >> docs/README.md
	@for file in src/*/*.py; do \
		if [ -f "$$file" ]; then \
			echo "### $$file" >> docs/README.md; \
			echo "" >> docs/README.md; \
			echo "\`\`\`python" >> docs/README.md; \
			head -20 "$$file" >> docs/README.md; \
			echo "\`\`\`" >> docs/README.md; \
			echo "" >> docs/README.md; \
		fi \
	done
	@echo "✅ Documentation generated in docs/"

# Development setup
dev-setup: install setup-env
	@echo "🔧 Setting up development environment..."
	@echo "✅ Development environment ready"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env file with your Azure credentials"
	@echo "2. Run: make test"
	@echo "3. Run: make local-test URL=https://youtu.be/your-video-id"

# Quick test with a sample video (replace with actual video)
quick-test:
	@echo "⚡ Running quick test with sample video..."
	@echo "Note: Replace this URL with a real YouTube video for testing"
	@echo "make local-test URL=https://youtu.be/dQw4w9WgXcQ TITLE='Sample Meeting'"

# Check environment
check-env:
	@echo "🔍 Checking environment..."
	@python -c "from src.utils.helpers import validate_environment; missing = validate_environment(); print('✅ Environment OK' if not missing else f'❌ Missing: {missing}')"

# Install development dependencies
install-dev:
	@echo "📦 Installing development dependencies..."
	pip install -r requirements.txt
	pip install pytest-cov black flake8 mypy
	@echo "✅ Development dependencies installed"

# Run specific test file
test-file:
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Error: FILE parameter is required"; \
		echo "Usage: make test-file FILE=tests/test_parser.py"; \
		exit 1; \
	fi
	@echo "🧪 Running specific test file: $(FILE)"
	python -m pytest $(FILE) -v

# Performance test
perf-test:
	@echo "⚡ Running performance test..."
	@echo "This will measure pipeline performance with a sample video"
	@if [ -z "$(URL)" ]; then \
		echo "❌ Error: URL parameter is required"; \
		echo "Usage: make perf-test URL=https://youtu.be/abc123"; \
		exit 1; \
	fi
	@echo "📊 Starting performance measurement..."
	@time python scripts/run_local.py "$(URL)" --log-level DEBUG

# Build distribution
build:
	@echo "🔨 Building distribution..."
	@echo "Creating distribution files..."
	@mkdir -p dist
	@echo "✅ Build completed"

# Show project status
status:
	@echo "📊 Project Status"
	@echo "================="
	@echo "Python version: $(shell python --version)"
	@echo "Project directory: $(shell pwd)"
	@echo "Environment file: $(shell [ -f .env ] && echo '✅ Present' || echo '❌ Missing')"
	@echo "Dependencies: $(shell pip list | grep -E '(yt-dlp|webvtt|openai|weasyprint)' | wc -l) key packages installed"
	@echo "Tests: $(shell find tests/ -name '*.py' | wc -l) test files"
	@echo "Source files: $(shell find src/ -name '*.py' | wc -l) Python files"
	@echo ""
	@echo "Recent output:"
	@ls -la output/ 2>/dev/null || echo "No output directory found"

# Show help again (alias)
info: help 