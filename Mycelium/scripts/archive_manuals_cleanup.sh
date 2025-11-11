#!/usr/bin/env bash
# Script to clean up the manuals folder
# Created: 2025-10-25
# Removes Python script duplicates, backup files, and old graph HTML outputs

# Note: Not using set -e because arithmetic operations can return non-zero exit codes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MANUALS_DIR="$SCRIPT_DIR/manuals"
ARCHIVE_DIR="$SCRIPT_DIR/manuals_archived_$(date +%Y%m%d_%H%M%S)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Mycelium Manuals Cleanup Tool${NC}"
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
    
    if [ -f "$MANUALS_DIR/$file" ]; then
        echo -e "${GREEN}✓${NC} Archiving: $file"
        echo -e "  Reason: $reason"
        if mv "$MANUALS_DIR/$file" "$ARCHIVE_DIR/" 2>/dev/null; then
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

# Function to archive a directory
archive_dir() {
    local dir="$1"
    local reason="$2"
    
    if [ -d "$MANUALS_DIR/$dir" ]; then
        echo -e "${GREEN}✓${NC} Archiving directory: $dir/"
        echo -e "  Reason: $reason"
        if mv "$MANUALS_DIR/$dir" "$ARCHIVE_DIR/" 2>/dev/null; then
            ARCHIVED_COUNT=$((ARCHIVED_COUNT + 1))
        else
            echo -e "${RED}  ERROR: Failed to move directory${NC}"
            FAILED_COUNT=$((FAILED_COUNT + 1))
        fi
    else
        echo -e "${RED}✗${NC} Not found: $dir/"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
}

echo -e "${BLUE}Archiving outdated files and duplicates...${NC}"
echo ""

# Category: Duplicate Python Scripts (already archived from Python/)
echo -e "${YELLOW}=== Duplicate Python Scripts (Already Archived) ===${NC}"
archive_file "animate_pagerank.py" "Duplicate - already archived from Python/"
archive_file "pipeline_profiler_and_pagerank.py" "Duplicate - already archived from Python/"
archive_file "compute_shortest_paths.py" "Duplicate - already archived from Python/"
archive_file "append_backlinks.py" "Duplicate - already archived from Python/"
archive_file "build_tag_backlinks.py" "Duplicate - already archived from Python/"
archive_file "cli_timer.py" "Duplicate - active version in Python/"
archive_file "config_common.py" "Duplicate - already archived from Python/"
archive_file "create_from_template.py" "Duplicate - already archived from Python/"
archive_file "graph_from_json.py" "Duplicate - already archived from Python/"
archive_file "graph_md_io.py" "Duplicate - already archived from Python/"
archive_file "mycelium_ttrpg.py" "Duplicate - already archived from Python/"
echo ""

# Category: Old/Unused Python Scripts in Manuals
echo -e "${YELLOW}=== Old/Unused Python Scripts ===${NC}"
archive_file "extract_link_multipliers.py" "Old version - active version in Python/"
archive_file "generate_pc_sheets.py" "Old version - active version in Python/"
archive_file "graph_to_sankey.py" "Unused Sankey graph generator"
archive_file "mycel_brain.py" "Old brain/analysis script"
archive_file "Mycelium Caretaker.py" "Old caretaker script"
archive_file "Mycelium_light.py" "Old lightweight version"
archive_file "pagerank_from_metadata.py" "Old PageRank script"
archive_file "pulse.py" "Old pulse monitoring script"
archive_file "update_variables_and_rebuild.py" "Old update script, superseded by sync_variables.py"
archive_file "Wiki_File_System_Manager.py" "Old version - active version in Python/"
echo ""

# Category: Wrapper Scripts (Duplicates)
echo -e "${YELLOW}=== Wrapper Scripts ===${NC}"
archive_file "Wikigraphs.py" "Wrapper script - canonical version in Python/"
echo ""

# Category: Backup Files
echo -e "${YELLOW}=== Backup Files ===${NC}"
archive_file "GrowthGuide.md.bak" "Backup file"
archive_file "Mycelium_config.md.bak" "Backup file"
archive_file "Mycelium.md.bak" "Backup file"
archive_file "README.md.bak" "Backup file"
archive_file "Root.md.bak" "Backup file"
archive_file "RTFM - Usage_Guide.md.bak" "Backup file"
archive_file "Spore_operators.md.bak" "Backup file"
echo ""

# Category: Old JSON Data Files
echo -e "${YELLOW}=== Old Data Files ===${NC}"
archive_file "pagerank.json" "Old PageRank data"
archive_file "pipeline_timing.json" "Old timing data"
echo ""

# Category: Outdated Manuals
echo -e "${YELLOW}=== Outdated Manuals ===${NC}"
archive_file "change_var_manual.md" "Manual for deprecated change_var.py"
archive_file "update_sheets_for_var_manual.md" "Manual for archived update_sheets_for_var.py"
archive_file "update_charManual.md" "Old character update manual"
archive_file "create_charManual.md" "Old character creation manual"
archive_file "cli_manual.md" "Old CLI manual"
archive_file "variable_cli_manual.md" "Old variable CLI manual"
archive_file "GRAPH_MD_IO_MANUAL.md" "Manual for archived graph_md_io.py"
archive_file "GRAPH_MD_IO_README.md" "README for archived graph_md_io.py"
archive_file "Wiki_File_System_Manager – MANUAL.md" "Old WFSM manual"
archive_file "GrowthGuide.md" "Old growth guide"
archive_file "Root.md" "Old root documentation"
archive_file "Spore_operators.md" "Old spore operators doc"
archive_file "RTFM - Usage_Guide.md" "Old usage guide"
archive_file "USAGE_SNIPPETS.md" "Old usage snippets"
archive_file "Mycelium_config.md" "Old config documentation"
archive_file "HOW_TO_TEST.md" "Old testing guide"
archive_file "FILE_EDITOR.md" "Old file editor documentation"
archive_file "COMBINED_MANUAL.md" "Old combined manual"
echo ""

# Category: Old Wikigraph HTML Output Directories
echo -e "${YELLOW}=== Old Wikigraph Output Directories ===${NC}"
archive_dir "Anjuclusters" "Old wikigraph outputs"
archive_dir "Ashclusters" "Old wikigraph outputs"
archive_dir "ATLA_Campaignclusters" "Old wikigraph outputs"
archive_dir "Dms Rootclusters" "Old wikigraph outputs"
archive_dir "graphsclusters" "Old wikigraph outputs"
archive_dir "Mahoganyclusters" "Old wikigraph outputs"
archive_dir "Player Rootclusters" "Old wikigraph outputs"
archive_dir "Puyclusters" "Old wikigraph outputs"
archive_dir "Rioclusters" "Old wikigraph outputs"
archive_dir "Soraclusters" "Old wikigraph outputs"
archive_dir "Tapiocaclusters" "Old wikigraph outputs"
archive_dir "testsclusters" "Old wikigraph outputs"
archive_dir "Tiebeediyclusters" "Old wikigraph outputs"
archive_dir "unsorted" "Old unsorted files"
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Archive Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Successfully archived:${NC} $ARCHIVED_COUNT items"
echo -e "${RED}Not found (already removed?):${NC} $FAILED_COUNT items"
echo -e "${YELLOW}Archive location:${NC} $ARCHIVE_DIR"
echo ""

# Create a README in the archive
cat > "$ARCHIVE_DIR/README.md" << 'EOF'
# Archived Mycelium Manuals Content

**Archive Date:** $(date +"%Y-%m-%d %H:%M:%S")

## Purpose
These files were archived as part of a cleanup effort to remove duplicate Python scripts, outdated manuals, backup files, and old wikigraph output from the manuals directory.

## What Was Archived

### 1. Duplicate Python Scripts
Python scripts that were duplicates of files in the `Python/` folder:
- Scripts already archived from Python/ (animate_pagerank.py, pipeline_profiler_and_pagerank.py, etc.)
- Scripts with active versions in Python/ (cli_timer.py, extract_link_multipliers.py, etc.)
- Wrapper script (Wikigraphs.py) that just imports from Python/

### 2. Old/Unused Python Scripts
- graph_to_sankey.py (unused Sankey generator)
- mycel_brain.py, Mycelium Caretaker.py, Mycelium_light.py (old analysis scripts)
- pagerank_from_metadata.py, pulse.py (old monitoring scripts)
- update_variables_and_rebuild.py (superseded by sync_variables.py)

### 3. Backup Files
- *.bak files (GrowthGuide.md.bak, Mycelium_config.md.bak, etc.)

### 4. Old Data Files
- pagerank.json, pipeline_timing.json

### 5. Outdated Manuals
- Manuals for deprecated scripts (change_var_manual.md, update_sheets_for_var_manual.md)
- Old documentation (cli_manual.md, GRAPH_MD_IO_MANUAL.md, etc.)
- Old guides (GrowthGuide.md, HOW_TO_TEST.md, COMBINED_MANUAL.md)

### 6. Old Wikigraph Output Directories
- *clusters/ directories (Anjuclusters, Ashclusters, etc.) - old HTML outputs
- unsorted/ directory

## What Remains in Manuals (Current/Active)

The following up-to-date manuals remain:
- sync_variables_manual.md (current variable sync documentation)
- sync_variables_quickref.md (quick reference)
- recreate_pcs.md (PC recreation documentation)
- recreate_npcs.md (NPC recreation documentation)
- watch_and_regen_manual.md (watcher documentation)
- environmental_variables.md (environmental variables guide)
- environmental_propagation.md (propagation guide)
- character_sheets_manual.md (character sheets guide)
- char_formulas_README.md (formulas documentation)
- Frontend Manual.md (frontend documentation)
- Wikigraphs_MANUAL.md (wikigraphs documentation)
- README.md (manuals index)

## Restoration

If you need to restore any of these files:

```bash
# Restore a single file
cp manuals_archived_YYYYMMDD_HHMMSS/filename ../manuals/

# Restore a directory
cp -r manuals_archived_YYYYMMDD_HHMMSS/dirname ../manuals/
```

## Safe Deletion

After confirming the system works without these files for 30-90 days, this archive can be safely deleted:

```bash
rm -rf manuals_archived_YYYYMMDD_HHMMSS
```

EOF

# Replace date placeholder in README
sed -i.bak "s/\$(date +\"%Y-%m-%d %H:%M:%S\")/$(date +"%Y-%m-%d %H:%M:%S")/g" "$ARCHIVE_DIR/README.md"
rm -f "$ARCHIVE_DIR/README.md.bak"

echo -e "${GREEN}✓${NC} Created README.md in archive directory"
echo ""

# List remaining files
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Active Manuals Remaining${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}Current documentation files:${NC}"
ls -1 "$MANUALS_DIR"/*.md 2>/dev/null | wc -l | xargs echo "  Markdown files:"
ls -1 "$MANUALS_DIR"/*.py 2>/dev/null | wc -l | xargs echo "  Python files:"
echo ""

echo -e "${GREEN}✓ Manuals cleanup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Review remaining files in: $MANUALS_DIR"
echo "2. Test your workflow to ensure nothing broke"
echo "3. If everything works for 30-90 days, you can safely delete:"
echo "   rm -rf $ARCHIVE_DIR"
echo ""
