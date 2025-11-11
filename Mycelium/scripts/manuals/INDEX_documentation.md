# Variable Synchronization System — Documentation Index

## Quick Navigation

### I Just Want to Use It
Start here: **QUICKSTART_sync_variables.md**
- How to start the watcher
- Common commands
- Quick troubleshooting

### I Want to Understand the System
Read in order:
1. **COMPLETE_GUIDE_understanding.md** — Big picture overview
2. **ARCHITECTURE_dataflow.md** — Data flows and diagrams
3. **variable_file_writing.md** — Tag transformation details

### I Need a Reference
**sync_variables.md** — Complete manual with all options and behaviors

### I'm Debugging Something
1. Check **sync_variables.md** → Troubleshooting section
2. Run with `--verbose` flag
3. Verify file format in **variable_file_writing.md**

---

## All Documentation Files

### Main Script
**File**: `Mycelium/scripts/Python/sync_variables.py`
- Complete working implementation
- 600+ lines with extensive comments
- Handles all synchronization logic

### Manual Files (in Mycelium/scripts/manuals/)

| File | Purpose | Best For |
|------|---------|----------|
| **QUICKSTART_sync_variables.md** | Fast reference | Getting started quickly |
| **sync_variables.md** | Complete manual | All options and features |
| **variable_file_writing.md** | Technical deep-dive | Understanding tag system |
| **ARCHITECTURE_dataflow.md** | System design | Understanding flow |
| **COMPLETE_GUIDE_understanding.md** | Conceptual overview | Big picture understanding |

---

## Understanding the System: Knowledge Map

```
You are here
    │
    ▼
┌─────────────────────────────────────┐
│ QUICKSTART (5 min read)            │
│ • How to run it                    │
│ • Common commands                  │
│ • Basic troubleshooting            │
└────────────┬────────────────────────┘
             │ "Tell me more"
             ▼
┌─────────────────────────────────────┐
│ COMPLETE_GUIDE (15 min read)       │
│ • What the system does             │
│ • Why it matters                   │
│ • Complete workflow                │
│ • Tag concepts                     │
└────────────┬────────────────────────┘
             │ "Show me the details"
             ▼
┌─────────────────────────────────────┐
│ ARCHITECTURE_dataflow (20 min)     │
│ • System diagrams                  │
│ • Data flow visualization          │
│ • File structure                   │
│ • Tag flow through system          │
└────────────┬────────────────────────┘
             │ "I need to know everything"
             ▼
┌─────────────────────────────────────┐
│ variable_file_writing.md (30 min)  │
│ • Tag transformation rules         │
│ • File format specification        │
│ • Secondary/primary stat handling  │
│ • Step-by-step examples            │
└────────────┬────────────────────────┘
             │ "Full reference"
             ▼
┌─────────────────────────────────────┐
│ sync_variables.md (reference)      │
│ • All CLI options                  │
│ • Integration with other scripts   │
│ • Troubleshooting guide            │
│ • Performance tuning               │
└─────────────────────────────────────┘
```

---

## Document Contents at a Glance

### QUICKSTART_sync_variables.md
```
• What you need to know (3 sections)
• Variable files exist here
• Variable file format
• Tags explained
• Using sync_variables.py (5 commands)
• Workflow overview
• Example: Change a character's HP
• Tag guide
• File structure diagram
• Troubleshooting
• Common commands
• Key points to remember
• Where to find more info
```

### COMPLETE_GUIDE_understanding.md
```
• What was created
• The problem this solves
• How it all fits together
• Tag transformation: Complete story
• Complete workflow (3 steps)
• Real example: Anju takes damage
• Key concepts
• File organization
• Using sync_variables.py
• Common tasks
• Understanding tag system in depth
• Troubleshooting
• Architecture summary
• Next steps
```

### ARCHITECTURE_dataflow.md
```
• System overview diagram
• Data flow: Complete cycle
  - Phase 1: Generation
  - Phase 2: Synchronization
• File transformation chain
• Tag flow through system
• Directory structure at sync time
• Script interaction map
• Update propagation example
• Key design principles
```

### variable_file_writing.md
```
• Overview
• Variable file directory structure
  - Location
  - Naming convention
• File format
  - Components
  - Real example
• Tag transformation process
  - Source: Primary stats
  - Source: Secondary stats
• Tag types and meanings
• Special handling: Zero-valued secondaries
• Tag suffix mechanism
• Writing process: Step-by-step
• File example: Complete walkthrough
• Integration points
• Key takeaways
```

### sync_variables.md
```
• Overview
• How variable files are written (from recreate_pcs.py)
• How sync_variables.py works (5 sections)
  1. Initialization
  2. File monitoring (5-second polling)
  3. Synchronization flow
  4. Character sheet updates
  5. Stat overview updates
• Usage guide (5 examples)
• Architecture (classes and methods)
• File reading format
• Tag detection
• Integration with other scripts
• Limitations and future enhancements
• Troubleshooting
• Contact
```

---

## Use Cases and Recommended Reading

### Use Case 1: "I just need to start using it"
**Read**: QUICKSTART_sync_variables.md (5 minutes)
**Then**: Run the script and make a test edit
**Done**: You can use it immediately

### Use Case 2: "I want to understand how it works"
**Read**: 
1. COMPLETE_GUIDE_understanding.md
2. ARCHITECTURE_dataflow.md
3. QUICKSTART_sync_variables.md
**Result**: You understand the whole system

### Use Case 3: "It's not working, help me debug"
**Read**: 
1. QUICKSTART_sync_variables.md → Troubleshooting section
2. sync_variables.md → Troubleshooting section
3. Run with `--verbose` flag
4. Check variable_file_writing.md for format validation

### Use Case 4: "I want to modify/extend the script"
**Read**:
1. variable_file_writing.md (understand data format)
2. ARCHITECTURE_dataflow.md (understand flow)
3. sync_variables.md (complete reference)
4. Study `Mycelium/scripts/Python/sync_variables.py` source code

### Use Case 5: "I need to explain this to someone else"
**Share**: COMPLETE_GUIDE_understanding.md
**Then show**: ARCHITECTURE_dataflow.md diagrams
**Finally**: Let them read QUICKSTART_sync_variables.md

---

## Key Concepts Index

### Tags
- What they are: QUICKSTART_sync_variables.md → "Tags Explained"
- How they're created: variable_file_writing.md → "Tag Transformation Process"
- How they're used: ARCHITECTURE_dataflow.md → "Tag Flow Through System"
- Complete guide: COMPLETE_GUIDE_understanding.md → "The Tag System"

### File Format
- Quick reference: QUICKSTART_sync_variables.md → "Variable File Format"
- Detailed spec: variable_file_writing.md → "File Format"
- Real examples: variable_file_writing.md → "File Example: Complete Walkthrough"

### Synchronization Flow
- Overview: QUICKSTART_sync_variables.md → "Workflow"
- Complete details: ARCHITECTURE_dataflow.md → "Phase 2: Synchronization"
- Step-by-step example: COMPLETE_GUIDE_understanding.md → "Real Example"

### Tag Transformation
- Quick explanation: QUICKSTART_sync_variables.md → "Tags Explained"
- Medium detail: COMPLETE_GUIDE_understanding.md → "Tag Transformation"
- Complete technical: variable_file_writing.md → "Tag Transformation Process"

### Directory Structure
- Quick ref: QUICKSTART_sync_variables.md → "File Structure at a Glance"
- Full diagram: ARCHITECTURE_dataflow.md → "Directory Structure at Sync Time"
- Detailed explanation: variable_file_writing.md → "Variable File Directory Structure"

---

## Finding Information

### By Topic

**"How do I run the script?"**
→ QUICKSTART_sync_variables.md → "Using sync_variables.py"

**"What are the command-line options?"**
→ sync_variables.md → "Usage" section

**"How are tags transformed?"**
→ variable_file_writing.md → "Tag Transformation Process"

**"Why does my variable file look like this?"**
→ variable_file_writing.md → "File Format"

**"How does the script decide what to update?"**
→ ARCHITECTURE_dataflow.md → "Tag Flow Through System"

**"What should I do if something isn't working?"**
→ sync_variables.md → "Troubleshooting"

**"I want to understand the big picture"**
→ COMPLETE_GUIDE_understanding.md → "How It All Fits Together"

**"Show me a real example"**
→ COMPLETE_GUIDE_understanding.md → "Real Example: Anju Takes Damage"

---

## Quick Reference Links

### Commands
```bash
# Start watching
python3 Mycelium/scripts/Python/sync_variables.py

# With verbose output
python3 Mycelium/scripts/Python/sync_variables.py --verbose

# Custom interval
python3 Mycelium/scripts/Python/sync_variables.py --interval 10

# Check syntax
python3 -m py_compile Mycelium/scripts/Python/sync_variables.py

# Generate initial files
python3 Mycelium/scripts/Python/recreate_pcs.py
```

### File Locations
```
Variable files:    Player Root/variable/PC_variables/<PC>/<PC>_*.md
Character sheets:  Player Root/PCs/<PC>/<PC> character sheet.md
Stat overview:     Player Root/PCs/stat_overview.md
Templates:         Player Root/variable/secondary_stat/*.md
Script:            Mycelium/scripts/Python/sync_variables.py
```

---

## Reading Paths by Role

### Game Master/Campaign Runner
→ QUICKSTART_sync_variables.md
→ COMPLETE_GUIDE_understanding.md (optional)
→ You're good to go!

### Developer/Maintainer
→ COMPLETE_GUIDE_understanding.md
→ ARCHITECTURE_dataflow.md
→ variable_file_writing.md
→ sync_variables.md
→ Study the source code

### System Administrator
→ sync_variables.md
→ ARCHITECTURE_dataflow.md
→ Check troubleshooting and integration sections

### New User
→ QUICKSTART_sync_variables.md
→ Try it out
→ Read COMPLETE_GUIDE_understanding.md if curious
→ Refer back to QUICKSTART for common tasks

---

## Document Map

```
START HERE
    │
    ├─→ QUICKSTART (practical)
    │       │
    │       ├─→ Need details?
    │       │   └─→ COMPLETE_GUIDE
    │       │       │
    │       │       ├─→ Need architecture?
    │       │       │   └─→ ARCHITECTURE
    │       │       │       │
    │       │       │       └─→ Need deep technical?
    │       │       │           └─→ variable_file_writing
    │       │       │
    │       │       └─→ Need reference?
    │       │           └─→ sync_variables
    │       │
    │       └─→ Troubleshooting problem?
    │           ├─→ Quick fix? → sync_variables (Troubleshooting)
    │           ├─→ Format issue? → variable_file_writing (File Format)
    │           └─→ Logic issue? → ARCHITECTURE (Data Flow)
    │
    └─→ Script source
            └─→ sync_variables.py (implemented here)
```

---

## Summary

You have comprehensive documentation covering:
- ✓ Quick start guide for immediate use
- ✓ Conceptual overview for understanding
- ✓ Architecture diagrams for system design
- ✓ Technical deep-dive for implementation
- ✓ Complete reference manual for all features
- ✓ Real examples and use cases
- ✓ Troubleshooting guides
- ✓ Integration information

**Start with QUICKSTART, then navigate based on your needs.**

All documentation is in: `Mycelium/scripts/manuals/`

The implementation is in: `Mycelium/scripts/Python/sync_variables.py`
