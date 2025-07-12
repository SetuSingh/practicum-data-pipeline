#!/bin/bash

# 🗑️ Cleanup Script for Outdated Documentation
# This script safely removes outdated documentation files while preserving important research materials

echo "🧹 Starting cleanup of outdated documentation..."
echo "================================================"

# Function to safely remove files/directories
safe_remove() {
    if [ -e "$1" ]; then
        echo "✅ Removing: $1"
        rm -rf "$1"
    else
        echo "⚠️  Not found: $1"
    fi
}

# Remove outdated documentation files
echo "📚 Removing outdated documentation files..."
safe_remove "docs/architecture_diagrams.md"
safe_remove "docs/pipeline_processing_workflow.md"
safe_remove "docs/pipeline_processing_workflow_UPDATED.md"
safe_remove "docs/data_ingestion_reality_check.md"
safe_remove "docs/implementation_setup.md"
safe_remove "docs/research_evaluation_framework.md"
safe_remove "backend/COMPLETE_SYSTEM_DOCUMENTATION.md"

# Remove potentially unused setup scripts
echo "🏗️ Removing potentially unused setup scripts..."
safe_remove "setup/enhanced_quick_start.sh"
safe_remove "setup/quick_start.sh"
safe_remove "start-setup.sh"

# Remove empty directories
echo "📁 Cleaning up empty directories..."
if [ -d "setup" ] && [ -z "$(ls -A setup)" ]; then
    echo "✅ Removing empty setup directory"
    rmdir setup
fi

# Keep important files
echo "📋 Keeping important files..."
echo "✅ Keeping: docs/README.md (documentation index)"
echo "✅ Keeping: docs/praticum-details/ (research materials)"
echo "✅ Keeping: docs/related-paper/ (research papers)"
echo "✅ Keeping: README.md (single source of truth)"
echo "✅ Keeping: SYSTEM_ANALYSIS_SUMMARY.md (analysis results)"

echo ""
echo "🎉 Cleanup complete!"
echo "================================================"
echo "📖 Your new single source of truth is: README.md"
echo "📊 System analysis available in: SYSTEM_ANALYSIS_SUMMARY.md"
echo "🔍 Research materials preserved in: docs/praticum-details/"
echo ""
echo "✨ Your system is now clean and well-documented!" 