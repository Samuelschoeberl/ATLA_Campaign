# BendingMove Component

## Overview
The `BendingMove` component is a specialized viewer for displaying character bending moves in the ATLA Campaign application. It automatically parses markdown files containing bending move information and renders them with an enhanced, interactive UI.

## Features

### 1. **Automatic Detection**
- Files under any "Bending Rules - [CharacterName]" folder are automatically detected
- Falls back to standard markdown rendering if the expected structure isn't found
- Excludes utility, mechanics, progression, and rules files from special rendering

### 2. **Structured Parsing**
The component parses the following structure from markdown:

```markdown
#Action_CharacterName
- Range: 3 * [[Earthbending slot]] (3) meters
- [[Earth Attack Roll]] (1d20 + 1 + 3)
- Damage: [[Earthbending slot]] (3)d6 bludgeoning.

**Effect**:
- Lift and throw a small rock. Simple ranged attack.

#Level1_CharacterName
#earth_CharacterName
```

### 3. **Visual Features**
- **Element-based coloring**: Automatically detects element (fire, water, air, earth, spirit) from tags and applies appropriate color scheme
- **Action type badges**: Displays action type (Action, Bonus Action, Reaction, Danger Sense Reaction) prominently
- **Tag display**: Shows all character-specific and move-specific tags
- **Interactive dice rolls**: Click any dice notation (e.g., "1d20 + 3") to roll and see results
- **Variable references**: Highlights and displays variable references like `[[Earthbending slot]] (3)` with tooltips

### 4. **Metadata Display**
Automatically extracts and displays:
- Range
- Duration
- Attack Roll (with clickable dice)
- Damage (with clickable dice)
- DC (Difficulty Class)
- Any other metadata fields in the format `- Key: value`

### 5. **Effects Section**
Renders all effect descriptions with:
- Proper text formatting
- Clickable dice notation
- Variable reference highlighting

### 6. **Fallback Rendering**
If the file doesn't match the expected bending move structure, it falls back to displaying the raw markdown in a readable format.

## Element Colors

The component uses the following color scheme based on detected elements:
- **Fire**: `#ffb3b3` (light red)
- **Water**: `#91bbff` (light blue)
- **Air**: `#fdffd1` (light yellow)
- **Earth**: `#c8f0a6` (light green)
- **Spirit**: `#ffcaf4` (light pink)

## File Structure Requirements

For optimal rendering, bending move files should be located in:
```
Player Root/PCs/[CharacterName]/Bending Rules - [CharacterName]/
```

Or any subdirectory within that structure, such as:
- `by Action Type/Action/`
- `by Action Type/Bonus Action/`
- `by Action Type/Reaction/`
- `Earth/Earthbending Moves/Level 1/`
- `Water/Waterbending Moves/Level 2/`

## Usage

The component is automatically used by `FileViewer.jsx` when a bending move file is detected. No manual integration is required.

```jsx
// FileViewer automatically renders BendingMove for appropriate files
if (isBendingMove) {
  return <BendingMove file={file} lightMode={lightMode} />;
}
```

## Light Mode Support

The component fully supports both light and dark modes, automatically adjusting colors and contrast based on the `lightMode` prop.

## Dependencies

- React
- `../utils/colorUtils` - For color manipulation (hexToRgba function)
- `./BendingMove.css` - Component styles

## Related Components

- **CharacterSheet.jsx**: Similar interactive component for character sheets
- **FileViewer.jsx**: Parent component that determines which renderer to use
- **DiceRollText**: Shared dice rolling utility (also used in CharacterSheet)
