# Quicklinks Component

A custom React component that provides a beautiful, interactive interface for the `Quicklinks.md` file.

## Features

- **Automatic Parsing**: Parses the Quicklinks.md file to extract:
  - Top-level wiki links (e.g., `[[stat_overview]]`, `[[Initiative Tracker]]`)
  - Character links from the table

- **Interactive Navigation**: Each link is rendered as a clickable button that:
  - Searches for the corresponding file in the workspace
  - Opens the file in the FileViewer when clicked
  - Uses the existing search functionality to find exact matches

- **Dynamic Color Matching**: 
  - Character buttons automatically use the same background colors as their folder in the FileTree
  - Colors are fetched from the `/api/file-colors` endpoint
  - Each character's button displays their unique folder color (e.g., `PCs/Anju/`)
  - Falls back to a default blue color if no color is assigned

- **Beautiful UI**:
  - Gradient backgrounds with smooth transitions
  - Two distinct button styles:
    - **Primary buttons** (purple gradient) for quick access links
    - **Character buttons** (dynamic colors from FileTree) for character links
  - Hover animations with glowing effects
  - Responsive grid layout
  - Light/dark mode support

## File Structure

```
Mycelium/scripts/frontend-react/src/components/
├── Quicklinks.jsx      # Main component logic
└── Quicklinks.css      # Styling
```

## Integration

The component is automatically used when `Quicklinks.md` is opened in the FileViewer. The detection is handled in `FileViewer.jsx`:

```javascript
const isQuicklinks = file ? file.name === 'Quicklinks.md' : false;

if (isQuicklinks) {
  return <Quicklinks lightMode={lightMode} onFileSelect={searchFileByName} />;
}
```

## Props

- `lightMode` (boolean): Toggles between dark and light mode styling
- `onFileSelect` (function): Callback function to navigate to a selected file

## Styling

The component features:
- Modern card-based design with glassmorphism effects
- Smooth hover animations with shimmer effect
- Responsive grid that adapts to screen size
- Distinct visual styles for different link types
- Full support for both light and dark themes

## Usage

Simply open `Quicklinks.md` in the FileViewer and the custom renderer will automatically display the enhanced interface.
