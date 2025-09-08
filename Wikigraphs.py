#!/usr/bin/env python3
"""
Wikigraphs.py - Graph Visualization Tool for Wiki File Systems

This script creates interactive graph representations of wiki files, including:
- Plotly sunburst charts showing hierarchical file structure
- Treemap visualizations showing file relationships and content size
- HTML file generation for easy viewing

Author: ATLA Campaign Management System
Designed to work with the Wiki_File_System_Manager.py ecosystem.
"""

import argparse
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, Any
import json
from collections import defaultdict, Counter

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.offline import plot
except ImportError:
    print("Error: plotly is required. Install it with: pip install plotly")
    exit(1)

# Import file scanning utilities from the existing Wiki_File_System_Manager
try:
    from Wiki_File_System_Manager import (
        iter_files, 
        should_process_file, 
        load_text,
        DEFAULT_EXCLUDES
    )
except ImportError:
    print("Warning: Could not import from Wiki_File_System_Manager.py")
    print("Some functionality may be limited.")
    
    # Fallback implementations
    DEFAULT_EXCLUDES = {".git", ".obsidian", "__pycache__", "node_modules"}
    
    def iter_files(roots, include_globs, exclude_dirs, use_default_excludes, follow_symlinks):
        """Fallback file iteration."""
        import fnmatch
        excludes = set(exclude_dirs)
        if use_default_excludes:
            excludes |= DEFAULT_EXCLUDES
            
        for root in roots:
            if root.is_file():
                yield root
                continue
                
            for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
                # Remove excluded directories
                dirnames[:] = [d for d in dirnames if d not in excludes]
                
                for fname in filenames:
                    fpath = Path(dirpath) / fname
                    if include_globs:
                        rel = str(fpath.relative_to(root))
                        if not any(fnmatch.fnmatch(rel, patt) for patt in include_globs):
                            continue
                    yield fpath
    
    def should_process_file(path, exts):
        """Fallback file processing check."""
        if not exts:
            return True
        return path.suffix.lower() in {e.lower() for e in exts}
    
    def load_text(path):
        """Fallback text loading."""
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None


class WikiGraphAnalyzer:
    """Analyzes wiki files and creates graph data structures."""
    
    def __init__(self, roots: List[Path]):
        self.roots = roots
        self.files = []
        self.backlinks = defaultdict(set)  # file -> set of files that link to it
        self.forward_links = defaultdict(set)  # file -> set of files it links to
        self.tags = defaultdict(set)  # file -> set of tags
        self.file_categories = defaultdict(str)  # file -> category (NPC, Location, etc.)
        self.file_sizes = {}  # file -> content size
        
    def scan_files(self, extensions: List[str] = None, exclude_dirs: List[str] = None) -> None:
        """Scan files and build the graph structure."""
        if extensions is None:
            extensions = ['.md', '.txt']
        if exclude_dirs is None:
            exclude_dirs = []
            
        print(f"Scanning files with extensions: {extensions}")
        
        # Get all candidate files
        for root in self.roots:
            for file_path in iter_files(
                [root], 
                include_globs=[], 
                exclude_dirs=exclude_dirs, 
                use_default_excludes=True, 
                follow_symlinks=False
            ):
                if should_process_file(file_path, extensions):
                    self.files.append(file_path)
        
        print(f"Found {len(self.files)} files to analyze")
        
        # Analyze each file
        for file_path in self.files:
            self._analyze_file(file_path)
    
    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single file for links, tags, and metadata."""
        content = load_text(file_path)
        if not content:
            return
            
        # Store file size
        self.file_sizes[file_path] = len(content)
        
        # Determine category from path
        self.file_categories[file_path] = self._categorize_file(file_path)
        
        # Find wikilinks [[...]]
        wikilink_pattern = r'\[\[([^\]]+)\]\]'
        matches = re.findall(wikilink_pattern, content)
        
        for match in matches:
            # Remove any display text (e.g., [[File|Display Text]] -> File)
            link_target = match.split('|')[0].strip()
            
            # Find the actual file that matches this link
            target_file = self._find_file_by_name(link_target)
            if target_file:
                self.forward_links[file_path].add(target_file)
                self.backlinks[target_file].add(file_path)
        
        # Find tags #tag
        tag_pattern = r'#(\w+)'
        tag_matches = re.findall(tag_pattern, content)
        self.tags[file_path] = set(tag_matches)
    
    def _categorize_file(self, file_path: Path) -> str:
        """Determine the category of a file based on its path."""
        path_str = str(file_path).lower()
        
        if 'npc' in path_str:
            return 'NPCs'
        elif 'location' in path_str:
            return 'Locations'
        elif 'session' in path_str:
            return 'Sessions'
        elif 'organisation' in path_str:
            return 'Organisations'
        elif 'rule' in path_str:
            return 'Rules'
        elif 'map' in path_str:
            return 'Maps'
        elif 'collection' in path_str:
            return 'Collections'
        elif file_path.suffix == '.txt':
            return 'Playlists'
        else:
            return 'Other'
    
    def _find_file_by_name(self, link_target: str) -> Optional[Path]:
        """Find a file that matches the given link target."""
        # Try exact name match first
        for file_path in self.files:
            if file_path.stem == link_target:
                return file_path
        
        # Try case-insensitive match
        link_lower = link_target.lower()
        for file_path in self.files:
            if file_path.stem.lower() == link_lower:
                return file_path
        
        return None
    
    def get_file_hierarchy(self) -> Dict[str, Any]:
        """Get hierarchical structure for sunburst chart."""
        hierarchy = {}
        
        for file_path in self.files:
            # Build path hierarchy
            parts = file_path.parts
            current = hierarchy
            
            # Navigate through path parts
            for part in parts[:-1]:  # Exclude filename
                if part not in current:
                    current[part] = {'children': {}, 'files': []}
                current = current[part]['children']
            
            # Add the file
            filename = parts[-1]
            if 'files' not in current:
                current['files'] = []
            current['files'].append({
                'name': filename,
                'path': file_path,
                'size': self.file_sizes.get(file_path, 0),
                'category': self.file_categories.get(file_path, 'Other'),
                'links_out': len(self.forward_links[file_path]),
                'links_in': len(self.backlinks[file_path])
            })
        
        return hierarchy
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the wiki."""
        stats = {
            'total_files': len(self.files),
            'total_links': sum(len(links) for links in self.forward_links.values()),
            'categories': Counter(self.file_categories.values()),
            'most_linked_files': [],
            'most_connecting_files': [],
            'orphaned_files': [],
            'total_tags': sum(len(tags) for tags in self.tags.values()),
            'unique_tags': set()
        }
        
        # Find most linked files (most backlinks)
        backlink_counts = [(len(links), file_path) for file_path, links in self.backlinks.items()]
        backlink_counts.sort(reverse=True)
        stats['most_linked_files'] = [(file_path.name, count) for count, file_path in backlink_counts[:10]]
        
        # Find most connecting files (most forward links)
        forward_counts = [(len(links), file_path) for file_path, links in self.forward_links.items()]
        forward_counts.sort(reverse=True)
        stats['most_connecting_files'] = [(file_path.name, count) for count, file_path in forward_counts[:10]]
        
        # Find orphaned files (no backlinks)
        stats['orphaned_files'] = [file_path.name for file_path in self.files 
                                 if len(self.backlinks[file_path]) == 0 and file_path in self.file_categories]
        
        # Collect all unique tags
        for tags in self.tags.values():
            stats['unique_tags'].update(tags)
        stats['unique_tags'] = list(stats['unique_tags'])
        
        return stats


class WikiGraphVisualizer:
    """Creates interactive visualizations of wiki graph data."""
    
    def __init__(self, analyzer: WikiGraphAnalyzer):
        self.analyzer = analyzer
        
    def create_sunburst_chart(self, output_file: str = "sunburst.html") -> str:
        """Create a sunburst chart showing file hierarchy."""
        print(f"Creating sunburst chart: {output_file}")
        
        # Prepare data for sunburst
        ids = []
        labels = []
        parents = []
        values = []
        colors = []
        
        # Color mapping for categories
        category_colors = {
            'NPCs': '#FF6B6B',
            'Locations': '#4ECDC4', 
            'Sessions': '#45B7D1',
            'Organisations': '#FFA07A',
            'Rules': '#98D8C8',
            'Maps': '#FFD93D',
            'Collections': '#6C5CE7',
            'Playlists': '#A8E6CF',
            'Other': '#DDD'
        }
        
        def add_hierarchy_level(hierarchy, parent_id="", parent_label="Root"):
            for name, data in hierarchy.items():
                if name == 'files':
                    # Add files
                    for file_info in data:
                        file_id = f"{parent_id}/{file_info['name']}" if parent_id else file_info['name']
                        ids.append(file_id)
                        labels.append(file_info['name'])
                        parents.append(parent_id)
                        values.append(max(1, file_info['size'] // 100))  # Scale down file sizes
                        colors.append(category_colors.get(file_info['category'], '#DDD'))
                else:
                    # Add directory
                    dir_id = f"{parent_id}/{name}" if parent_id else name
                    ids.append(dir_id)
                    labels.append(name)
                    parents.append(parent_id)
                    values.append(1)  # Directories get base value
                    colors.append('#F8F8F8')  # Light gray for directories
                    
                    # Recurse into subdirectories
                    if 'children' in data:
                        add_hierarchy_level(data['children'], dir_id, name)
        
        # Build the hierarchy
        hierarchy = self.analyzer.get_file_hierarchy()
        add_hierarchy_level(hierarchy)
        
        # Create sunburst chart
        fig = go.Figure(go.Sunburst(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            marker=dict(colors=colors),
            branchvalues="total",
        ))
        
        fig.update_layout(
            title="ATLA Campaign Wiki - File Structure",
            font_size=12,
            height=800,
            width=800
        )
        
        # Save to HTML
        output_path = Path(output_file)
        plot(fig, filename=str(output_path), auto_open=False)
        
        return str(output_path.absolute())
    
    def create_treemap_chart(self, output_file: str = "treemap.html") -> str:
        """Create a treemap showing file relationships and sizes."""
        print(f"Creating treemap chart: {output_file}")
        
        # Prepare data for treemap
        labels = []
        parents = []
        values = []
        colors = []
        text_info = []
        
        # Color mapping
        category_colors = {
            'NPCs': '#FF6B6B',
            'Locations': '#4ECDC4', 
            'Sessions': '#45B7D1',
            'Organisations': '#FFA07A',
            'Rules': '#98D8C8',
            'Maps': '#FFD93D',
            'Collections': '#6C5CE7',
            'Playlists': '#A8E6CF',
            'Other': '#DDD'
        }
        
        # Add root categories
        stats = self.analyzer.get_stats()
        for category, count in stats['categories'].items():
            labels.append(category)
            parents.append("")
            values.append(count)
            colors.append(category_colors.get(category, '#DDD'))
            text_info.append(f"{category}<br>{count} files")
        
        # Add individual files
        for file_path in self.analyzer.files:
            category = self.analyzer.file_categories[file_path]
            file_size = self.analyzer.file_sizes.get(file_path, 0)
            links_in = len(self.analyzer.backlinks[file_path])
            links_out = len(self.analyzer.forward_links[file_path])
            
            labels.append(file_path.name)
            parents.append(category)
            values.append(max(1, file_size // 50))  # Scale file size
            colors.append(category_colors.get(category, '#DDD'))
            text_info.append(f"{file_path.name}<br>Size: {file_size}<br>Links in: {links_in}<br>Links out: {links_out}")
        
        # Create treemap
        fig = go.Figure(go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            text=text_info,
            textinfo="label+text",
            marker=dict(colors=colors),
            pathbar=dict(visible=True),
        ))
        
        fig.update_layout(
            title="ATLA Campaign Wiki - File Relationships & Size",
            font_size=10,
            height=800,
            width=1200
        )
        
        # Save to HTML
        output_path = Path(output_file)
        plot(fig, filename=str(output_path), auto_open=False)
        
        return str(output_path.absolute())
    
    def create_network_graph(self, output_file: str = "network.html") -> str:
        """Create a network graph showing file relationships."""
        print(f"Creating network graph: {output_file}")
        
        # This would require additional libraries like networkx
        # For now, create a simple link analysis visualization
        
        # Prepare data for a scatter plot showing link relationships
        x_vals = []
        y_vals = []
        sizes = []
        colors = []
        text_labels = []
        
        category_colors = {
            'NPCs': '#FF6B6B',
            'Locations': '#4ECDC4', 
            'Sessions': '#45B7D1',
            'Organisations': '#FFA07A',
            'Rules': '#98D8C8',
            'Maps': '#FFD93D',
            'Collections': '#6C5CE7',
            'Playlists': '#A8E6CF',
            'Other': '#DDD'
        }
        
        for i, file_path in enumerate(self.analyzer.files):
            links_in = len(self.analyzer.backlinks[file_path])
            links_out = len(self.analyzer.forward_links[file_path])
            category = self.analyzer.file_categories[file_path]
            
            x_vals.append(links_out)
            y_vals.append(links_in)
            sizes.append(max(5, self.analyzer.file_sizes.get(file_path, 0) // 100))
            colors.append(category_colors.get(category, '#DDD'))
            text_labels.append(f"{file_path.name}<br>Category: {category}")
        
        fig = go.Figure(data=go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers',
            marker=dict(
                size=sizes,
                color=colors,
                opacity=0.7,
                line=dict(width=1, color='black')
            ),
            text=text_labels,
            hovertemplate='%{text}<br>Links Out: %{x}<br>Links In: %{y}<extra></extra>'
        ))
        
        fig.update_layout(
            title="ATLA Campaign Wiki - Link Analysis",
            xaxis_title="Outgoing Links",
            yaxis_title="Incoming Links",
            height=600,
            width=800
        )
        
        # Save to HTML
        output_path = Path(output_file)
        plot(fig, filename=str(output_path), auto_open=False)
        
        return str(output_path.absolute())
    
    def create_stats_report(self, output_file: str = "wiki_stats.html") -> str:
        """Create an HTML report with wiki statistics."""
        print(f"Creating statistics report: {output_file}")
        
        stats = self.analyzer.get_stats()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ATLA Campaign Wiki Statistics</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
                h2 {{ color: #34495e; margin-top: 30px; }}
                .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: #ecf0f1; padding: 20px; border-radius: 8px; text-align: center; }}
                .stat-number {{ font-size: 2em; font-weight: bold; color: #2980b9; }}
                .stat-label {{ font-size: 0.9em; color: #7f8c8d; margin-top: 5px; }}
                .list-section {{ background: #fafafa; padding: 20px; border-radius: 8px; margin: 15px 0; }}
                ul {{ columns: 2; column-gap: 30px; }}
                li {{ margin: 5px 0; }}
                .category {{ display: inline-block; background: #3498db; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-right: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔥 ATLA Campaign Wiki Statistics</h1>
                
                <div class="stat-grid">
                    <div class="stat-card">
                        <div class="stat-number">{stats['total_files']}</div>
                        <div class="stat-label">Total Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{stats['total_links']}</div>
                        <div class="stat-label">Total Links</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{len(stats['unique_tags'])}</div>
                        <div class="stat-label">Unique Tags</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{len(stats['orphaned_files'])}</div>
                        <div class="stat-label">Orphaned Files</div>
                    </div>
                </div>
                
                <h2>📊 File Categories</h2>
                <div class="list-section">
        """
        
        for category, count in stats['categories'].most_common():
            html_content += f'<span class="category">{category}: {count}</span>'
        
        html_content += f"""
                </div>
                
                <h2>🔗 Most Linked Files</h2>
                <div class="list-section">
                    <ul>
        """
        
        for filename, count in stats['most_linked_files'][:15]:
            html_content += f"<li><strong>{filename}</strong> - {count} incoming links</li>"
        
        html_content += f"""
                    </ul>
                </div>
                
                <h2>🌐 Most Connecting Files</h2>
                <div class="list-section">
                    <ul>
        """
        
        for filename, count in stats['most_connecting_files'][:15]:
            html_content += f"<li><strong>{filename}</strong> - {count} outgoing links</li>"
        
        html_content += f"""
                    </ul>
                </div>
                
                <h2>🏷️ All Tags</h2>
                <div class="list-section">
        """
        
        for tag in sorted(stats['unique_tags']):
            html_content += f'<span class="category">#{tag}</span>'
        
        html_content += f"""
                </div>
                
                <h2>📄 Orphaned Files</h2>
                <div class="list-section">
                    <ul>
        """
        
        for filename in stats['orphaned_files'][:20]:
            html_content += f"<li>{filename}</li>"
        
        html_content += """
                    </ul>
                </div>
                
                <p style="text-align: center; margin-top: 40px; color: #7f8c8d;">
                    Generated by Wikigraphs.py for ATLA Campaign Management
                </p>
            </div>
        </body>
        </html>
        """
        
        # Save HTML file
        output_path = Path(output_file)
        output_path.write_text(html_content, encoding='utf-8')
        
        return str(output_path.absolute())


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create interactive graph visualizations of wiki file systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python Wikigraphs.py                                    # Analyze current directory
  python Wikigraphs.py --sunburst wiki_structure.html    # Create sunburst chart
  python Wikigraphs.py --treemap file_relationships.html # Create treemap
  python Wikigraphs.py --all --output-dir graphs/        # Create all visualizations
  python Wikigraphs.py "Players Part" --ext .md          # Analyze specific directory
        """
    )
    
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Root paths to analyze (default: current directory)"
    )
    
    parser.add_argument(
        "--ext",
        nargs="*",
        default=[".md", ".txt"],
        help="File extensions to analyze (default: .md .txt)"
    )
    
    parser.add_argument(
        "--exclude-dir",
        nargs="*",
        default=[],
        help="Directory names to exclude from analysis"
    )
    
    parser.add_argument(
        "--sunburst",
        help="Create sunburst chart and save to specified file"
    )
    
    parser.add_argument(
        "--treemap", 
        help="Create treemap chart and save to specified file"
    )
    
    parser.add_argument(
        "--network",
        help="Create network graph and save to specified file"
    )
    
    parser.add_argument(
        "--stats",
        help="Create statistics report and save to specified file"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Create all visualization types"
    )
    
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory for generated files (default: current directory)"
    )
    
    return parser.parse_args()


def main():
    """Main function."""
    args = parse_args()
    
    # Convert paths to Path objects
    roots = [Path(p).resolve() for p in args.paths]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🔥 ATLA Campaign Wiki Graph Generator")
    print("=" * 50)
    print(f"Analyzing paths: {[str(r) for r in roots]}")
    print(f"File extensions: {args.ext}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Initialize analyzer
    analyzer = WikiGraphAnalyzer(roots)
    analyzer.scan_files(extensions=args.ext, exclude_dirs=args.exclude_dir)
    
    if not analyzer.files:
        print("❌ No files found to analyze!")
        return 1
    
    # Initialize visualizer
    visualizer = WikiGraphVisualizer(analyzer)
    
    created_files = []
    
    # Create visualizations based on arguments
    if args.sunburst or args.all:
        filename = args.sunburst or "sunburst.html"
        output_path = output_dir / filename
        result = visualizer.create_sunburst_chart(str(output_path))
        created_files.append(result)
    
    if args.treemap or args.all:
        filename = args.treemap or "treemap.html"
        output_path = output_dir / filename
        result = visualizer.create_treemap_chart(str(output_path))
        created_files.append(result)
    
    if args.network or args.all:
        filename = args.network or "network.html"
        output_path = output_dir / filename
        result = visualizer.create_network_graph(str(output_path))
        created_files.append(result)
    
    if args.stats or args.all:
        filename = args.stats or "wiki_stats.html"
        output_path = output_dir / filename
        result = visualizer.create_stats_report(str(output_path))
        created_files.append(result)
    
    # If no specific visualization requested, create sunburst by default
    if not any([args.sunburst, args.treemap, args.network, args.stats, args.all]):
        output_path = output_dir / "sunburst.html"
        result = visualizer.create_sunburst_chart(str(output_path))
        created_files.append(result)
    
    # Display summary
    print("\n✅ Graph generation complete!")
    print(f"📊 Analyzed {len(analyzer.files)} files")
    print(f"🔗 Found {sum(len(links) for links in analyzer.forward_links.values())} links")
    print("\n📁 Created files:")
    for file_path in created_files:
        print(f"  • {file_path}")
    
    print(f"\n🌐 Open the HTML files in your browser to view the interactive visualizations!")
    
    return 0


if __name__ == "__main__":
    exit(main())