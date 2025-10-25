# Mycelium Frontend React

This is the React version of the Mycelium repo browser frontend, converted from the original static HTML file.

## Project Structure

```
frontend-react/
├── index.html              # HTML entry point
├── package.json            # Dependencies and scripts
├── vite.config.js          # Vite configuration
├── public/                 # Static assets
├── src/
│   ├── main.jsx           # React entry point
│   ├── App.jsx            # Main application component
│   ├── components/        # React components
│   │   ├── Header.jsx
│   │   ├── Navigation.jsx
│   │   ├── FileList.jsx
│   │   ├── MarkdownPreview.jsx
│   │   ├── FileEditor.jsx
│   │   ├── DiceRoller.jsx
│   │   └── EventLog.jsx
│   ├── utils/             # Utility functions
│   │   ├── helpers.js     # Helper functions (markdown, colors, dice)
│   │   └── api.js         # API calls to backend
│   └── styles/            # CSS styles
│       └── App.css        # Main stylesheet
```

## Features Converted

✅ File browser with directory navigation
✅ Markdown file preview and editing
✅ Dice roller with custom expressions
✅ Event log system
✅ Pin/unpin paths
✅ Search functionality
✅ Wikigraph generation
✅ File creation and deletion
✅ Fullscreen editor mode
✅ Pastel color scheme with animated background

## Installation

1. **Install Node.js** (if not already installed):

   - Download from [nodejs.org](https://nodejs.org/)
   - Or use a package manager (Homebrew on macOS: `brew install node`)

2. **Install dependencies**:
   ```bash
   cd Mycelium/scripts/frontend-react
   npm install
   ```

## Development

Run the development server:

```bash
npm run dev
```

This will start the Vite dev server, typically at `http://localhost:5173`

The dev server includes:

- Hot Module Replacement (HMR) for instant updates
- Proxy configuration for backend API calls

## Building for Production

Create an optimized production build:

```bash
npm run build
```

This creates a `dist/` folder with optimized static assets.

Preview the production build:

```bash
npm run preview
```

## Backend Configuration

The app expects the backend API to be available at:

- Development: Proxied through Vite (configured in `vite.config.js`)
- Production: Same origin as the frontend, or set `window.MYCELIUM_BACKEND_BASE`

API endpoints used:

- `/player_root/*` - File and directory operations
- `/api/generate-graphs` - Wikigraph generation
- `/api/search` - Search functionality

## Key Differences from Original HTML

1. **Modular Components**: Split into reusable React components
2. **State Management**: Using React hooks (useState, useEffect)
3. **Modern Build Tool**: Vite for fast development and optimized builds
4. **Module System**: ES modules instead of inline scripts
5. **Maintainability**: Easier to extend and modify

## Tech Stack

- **React 18** - UI library
- **Vite** - Build tool and dev server
- **marked** - Markdown parsing
- **DOMPurify** - HTML sanitization

## Notes

- The original HTML file is preserved at `../frontend/index.html`
- This React version maintains feature parity with the original
- Backend API compatibility is preserved
- All styling and visual effects are maintained
