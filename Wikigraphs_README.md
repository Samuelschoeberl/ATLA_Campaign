# Wikigraphs.py - Graph Visualizations for ATLA Campaign Wiki

Wikigraphs.py is a powerful visualization tool that creates interactive graph representations of your wiki files, helping you understand the structure and relationships within your Avatar: The Last Airbender campaign content.

## 🚀 Features

- **📈 Sunburst Charts**: Hierarchical visualization of your file structure
- **🗺️ Treemap Charts**: File relationships and content size visualization  
- **🕸️ Network Graphs**: Link analysis showing connections between files
- **📊 Statistics Reports**: Comprehensive HTML reports with wiki metrics

## 📋 Requirements

Install required dependencies:
```bash
pip install plotly numpy
```

## 🎯 Quick Start

### Basic Usage
```bash
# Create a sunburst chart (default)
python Wikigraphs.py

# Create all visualization types
python Wikigraphs.py --all

# Analyze specific directory
python Wikigraphs.py "Players Part" --ext .md
```

### Specific Visualizations
```bash
# Create sunburst chart
python Wikigraphs.py --sunburst wiki_structure.html

# Create treemap
python Wikigraphs.py --treemap file_relationships.html

# Create network graph
python Wikigraphs.py --network connections.html

# Create statistics report
python Wikigraphs.py --stats wiki_stats.html
```

### Advanced Options
```bash
# Save all visualizations to specific directory
python Wikigraphs.py --all --output-dir graphs/

# Analyze only markdown files, exclude certain directories
python Wikigraphs.py --ext .md --exclude-dir "Archive" "Backup"
```

## 📈 Generated Visualizations

### Sunburst Chart (`sunburst.html`)
- Shows hierarchical file structure as concentric circles
- Color-coded by file categories (NPCs, Locations, Sessions, etc.)
- Interactive drill-down navigation
- File sizes represented by segment sizes

### Treemap Chart (`treemap.html`)
- Rectangular layout showing file relationships
- Size indicates content length
- Colors represent categories
- Hover for detailed file information

### Network Graph (`network.html`)
- Scatter plot analysis of file connections
- X-axis: outgoing links, Y-axis: incoming links
- Bubble size: file content size
- Identifies hub files and orphaned content

### Statistics Report (`wiki_stats.html`)
- Complete overview of wiki metrics
- File counts by category
- Most linked and connecting files
- Tag analysis and orphaned files list
- Clean, professional HTML format

## 📊 Example Output

For the ATLA Campaign wiki, Wikigraphs.py analyzes:
- **191 total files** across multiple categories
- **427 wiki links** between files
- **8 main categories**: NPCs, Locations, Sessions, Organizations, Rules, Maps, Collections, Playlists
- **34 unique tags** for content organization
- **107 orphaned files** that need better linking

## 🎨 File Categories

Wikigraphs.py automatically categorizes files based on their path:
- **NPCs**: Character files in NPC directories
- **Locations**: Place and setting files
- **Sessions**: Game session notes and logs
- **Organizations**: Groups and factions
- **Rules**: Game mechanics and reference
- **Maps**: Visual and location references
- **Collections**: Auto-generated backlink collections
- **Playlists**: Music and audio references (.txt files)
- **Other**: Miscellaneous content

## 🔗 Integration

Wikigraphs.py works seamlessly with the existing Wiki_File_System_Manager.py:
- Uses the same file scanning logic
- Respects the same directory exclusions (.git, .obsidian, etc.)
- Parses [[wikilinks]] and #tags using established patterns
- Follows the same command-line argument conventions

## 💡 Tips

1. **Regular Analysis**: Run `python Wikigraphs.py --stats` regularly to identify orphaned files
2. **Category Organization**: Use the treemap to see which categories need better organization
3. **Link Analysis**: Use the network graph to find hub files that should be in your index
4. **Directory Focus**: Analyze specific directories like "Players Part" for targeted insights
5. **HTML Sharing**: Generated HTML files are self-contained and can be shared with players

## 🔍 Command Reference

```
usage: Wikigraphs.py [-h] [--ext [EXT ...]] [--exclude-dir [EXCLUDE_DIR ...]] 
                     [--sunburst SUNBURST] [--treemap TREEMAP] [--network NETWORK] 
                     [--stats STATS] [--all] [--output-dir OUTPUT_DIR] [paths ...]

Options:
  paths                 Root paths to analyze (default: current directory)
  --ext [EXT ...]       File extensions to analyze (default: .md .txt)
  --exclude-dir [...]   Directory names to exclude from analysis
  --sunburst FILE       Create sunburst chart and save to FILE
  --treemap FILE        Create treemap chart and save to FILE  
  --network FILE        Create network graph and save to FILE
  --stats FILE          Create statistics report and save to FILE
  --all                 Create all visualization types
  --output-dir DIR      Output directory for generated files
```

## 🎬 Avatar Campaign Integration

This tool is specifically designed for Avatar: The Last Airbender campaign management, with:
- **Theme-appropriate colors** matching the four elements
- **Campaign-specific categories** for NPCs, locations, and sessions
- **Playlist integration** for atmospheric music references
- **Organization tracking** for groups like the White Lotus
- **Session management** for campaign progression

Perfect for DMs managing complex Avatar campaigns with rich interconnected lore!

---

*Generated visualizations are saved as interactive HTML files that can be opened in any web browser for exploration and sharing.*