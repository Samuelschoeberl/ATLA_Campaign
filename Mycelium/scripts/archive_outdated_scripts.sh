#!/usr/bin/env bash
# Script to archive outdated Python scripts from Mycelium/scripts/Python
# Created: 2025-10-25
# This script moves outdated scripts to an archive directory for safe keeping

# Note: Not using set -e because arithmetic operations can return non-zero exit codes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_DIR="$SCRIPT_DIR/Python"
ARCHIVE_DIR="$SCRIPT_DIR/archived_$(date +%Y%m%d_%H%M%S)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Mycelium Scripts Archive Tool${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create archive directory
echo -e "${YELLOW}Creating archive directory:${NC} $ARCHIVE_DIR"
mkdir -p "$ARCHIVE_DIR"
echo ""

# Counter
ARCHIVED_COUNT=0
FAILED_COUNT=0

# Function to archive a file
archive_file() {
    local file="$1"
    local reason="$2"
    
    if [ -f "$PYTHON_DIR/$file" ]; then
        echo -e "${GREEN}✓${NC} Archiving: $file"
        echo -e "  Reason: $reason"
        if mv "$PYTHON_DIR/$file" "$ARCHIVE_DIR/" 2>/dev/null; then
            ARCHIVED_COUNT=$((ARCHIVED_COUNT + 1))
        else
            echo -e "${RED}  ERROR: Failed to move file${NC}"
            FAILED_COUNT=$((FAILED_COUNT + 1))
        fi
    else
        echo -e "${RED}✗${NC} Not found: $file"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
}

echo -e "${BLUE}Archiving outdated scripts...${NC}"
echo ""

# Category: Old/Replaced Functionality
echo -e "${YELLOW}=== Old/Replaced Functionality ===${NC}"
archive_file "change_var.py" "Minimal test stub, superseded by sync_variables.py"
archive_file "add_folder_tag.py" "Tiny stub, likely experimental"
archive_file "create_from_template.py" "Minimal stub"
archive_file "config_common.py" "Near-empty config stub"
echo ""

# Category: Deprecated Watch/Sync Scripts
echo -e "${YELLOW}=== Deprecated Watch/Sync Scripts ===${NC}"
archive_file "watch_env_and_regen.py" "Old environmental variable watcher, superseded"
archive_file "env_sync_server.py" "Old HTTP sync server, superseded by frontend_api.py"
archive_file "mycelium_auto_reboot_watcher.py" "Character sheet file watcher, integrated into watch_and_regen.py"
archive_file "manage_env_sync.sh" "Shell script for old env_sync_server"
echo ""

# Category: Old Character Sheet Generators
echo -e "${YELLOW}=== Old Character Sheet Generators ===${NC}"
archive_file "update_character_sheets_from_variables.py" "Old updater, replaced by recreate_pcs.py"
archive_file "update_sheets_for_var.py" "Old sheet updater"
archive_file "update_bending_slots.py" "Specific updater, functionality in recreate_pcs.py"
archive_file "update_collection_block.py" "Old block updater"
archive_file "update_manual_timestamps.py" "Manual timestamp updater"
echo ""

# Category: Legacy Graph/Analysis Scripts
echo -e "${YELLOW}=== Legacy Graph/Analysis Scripts ===${NC}"
archive_file "mycelium_ttrpg.py" "Old PC folder generator, not used in current workflow"
archive_file "mycelium_grow_mushroom.py" "Old mushroom graph generator"
archive_file "mycelium_ctl.py" "Old controller script"
archive_file "mycelium_caretaker.py" "Old caretaker script"
archive_file "pipeline_profiler_and_pagerank.py" "Old profiler"
archive_file "compute_shortest_paths.py" "Unused graph analysis"
archive_file "animate_pagerank.py" "PageRank animation (unused feature)"
echo ""

# Category: Old Tag/Link Management
echo -e "${YELLOW}=== Old Tag/Link Management ===${NC}"
archive_file "build_tag_backlinks.py" "Old backlink builder"
archive_file "append_backlinks.py" "Old backlink appender"
archive_file "tag_folder.py" "Old folder tagger"
archive_file "infer_file_tags.py" "Old tag inference"
archive_file "sort_unsorted_by_mushroom_tags.py" "Old sorting script"
archive_file "aggregate_mycelium.py" "Old aggregation script"
echo ""

# Category: Diagnostic/Test Files
echo -e "${YELLOW}=== Diagnostic/Test Files ===${NC}"
archive_file "diagnose_allowed.py" "Old diagnostic"
archive_file "test_change_var_integration.py" "Integration test for deprecated change_var.py"
archive_file "Resiliance.py" "Old content checker, not in active use"
archive_file "run_propagate_dry.py" "Old dry-run script"
echo ""

# Category: Old Variable Management
echo -e "${YELLOW}=== Old Variable Management ===${NC}"
archive_file "create_unsorted_from_wikilinks.py" "Old file creator"
archive_file "create_variable_aliases.py" "Old alias creator"
archive_file "cleanup_unused.py" "Old cleanup script"
echo ""

# Category: Old Graph Utilities
echo -e "${YELLOW}=== Old Graph Utilities ===${NC}"
archive_file "graph_from_json.py" "Old graph builder from JSON"
archive_file "graph_md_io.py" "Old graph I/O utilities, replaced by Wikigraphs.py"
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Archive Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Successfully archived:${NC} $ARCHIVED_COUNT files"
echo -e "${RED}Not found (already removed?):${NC} $FAILED_COUNT files"
echo -e "${YELLOW}Archive location:${NC} $ARCHIVE_DIR"
echo ""

# Create a README in the archive
cat > "$ARCHIVE_DIR/README.md" << 'EOF'
# Archived Mycelium Scripts

**Archive Date:** $(date +"%Y-%m-%d %H:%M:%S")

## Purpose
These scripts were archived as part of a cleanup effort to remove outdated and unused scripts from the active Mycelium/scripts/Python directory.

## Why These Scripts Were Archived

### Categories of Archived Scripts:

1. **Old/Replaced Functionality** - Minimal stubs and experimental scripts replaced by newer implementations
2. **Deprecated Watch/Sync Scripts** - Old file watchers and sync servers superseded by current system
3. **Old Character Sheet Generators** - Legacy updaters replaced by recreate_pcs.py and recreate_npcs.py
4. **Legacy Graph/Analysis Scripts** - Old graph generators and analysis tools no longer in use
5. **Old Tag/Link Management** - Deprecated tag and link management utilities
6. **Diagnostic/Test Files** - Old test and diagnostic scripts for deprecated systems
7. **Old Variable Management** - Legacy variable creation and management scripts
8. **Old Graph Utilities** - Old graph building utilities replaced by Wikigraphs.py

## Active Scripts (NOT Archived)

The following scripts remain active and in use:
- sync_variables.py (main variable sync system)
- recreate_pcs.py (active PC sheet generator)
- recreate_npcs.py (active NPC sheet generator)
- watch_and_regen.py (file watcher for auto-regeneration)
- run_backend.py (Flask backend server)
- frontend_api.py (main API blueprint)
- common.py (shared utilities)
- generate_initiative.py
- generate_pc_sheets.py
- generate_stat_overview.py
- generate_secondary_stats.py
- Wikigraphs.py (graph visualization)
- And other actively used utilities

## Restoration

If you need to restore any of these scripts:

```bash
# Restore a single file
cp archived_YYYYMMDD_HHMMSS/script_name.py ../Python/

# Restore all files
cp archived_YYYYMMDD_HHMMSS/*.py ../Python/
```

## Safe Deletion

After confirming the system works without these scripts for a sufficient period (e.g., 30-90 days), this archive directory can be safely deleted.

EOF

# Replace date placeholder in README
sed -i.bak "s/\$(date +\"%Y-%m-%d %H:%M:%S\")/$(date +"%Y-%m-%d %H:%M:%S")/g" "$ARCHIVE_DIR/README.md"
rm -f "$ARCHIVE_DIR/README.md.bak"

echo -e "${GREEN}✓${NC} Created README.md in archive directory"
echo ""

# List remaining active scripts
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Active Scripts Remaining${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}Python scripts still in use:${NC}"
ls -1 "$PYTHON_DIR"/*.py 2>/dev/null | wc -l | xargs echo "  Count:"
echo ""

echo -e "${GREEN}✓ Archive complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Test your workflow to ensure nothing broke"
echo "2. Run key scripts: sync_variables.py, recreate_pcs.py, etc."
echo "3. If everything works for 30-90 days, you can safely delete:"
echo "   rm -rf $ARCHIVE_DIR"
echo ""
