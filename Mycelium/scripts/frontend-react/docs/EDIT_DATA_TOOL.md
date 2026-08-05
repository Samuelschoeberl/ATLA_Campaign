# Edit Data Tool - Quick Reference

## Overview

The **Edit Data** tool (✏️) allows quick editing of token parameters and hex cell data directly on the battlemap by clicking on any token or hex cell.

## Features

### Token Editing
When clicking on a token with the Edit Data tool active, you can modify:

#### Basic Properties
- **Name**: Token display name
- **Type**: Player, Enemy, or NPC
- **Color**: Token border and highlight color
- **Size**: Width and height in hexes (1-5)

#### Combat Stats
- **Current HP**: Live HP value
- **Max HP**: Maximum HP value
- **HP Bar**: Visual preview showing health percentage

#### Conditions
- **Toggle Conditions**: Click to activate/deactivate any condition
- **Available Conditions**:
  - Bleeding out (Red)
  - Blinded (Dark Gray)
  - Dazed (Orange)
  - Immobilised (Gray)
  - Paralysed (Purple)
  - Prone (Light Gray)
  - Slowed (Blue)
  - Empowered (Yellow)
  - Armor Surge (Teal)
  - Barrier Surge (Purple)
  - Harmonic Flow (Pink)
  - Exhausted (Dark Blue)

### Hex Cell Editing
When clicking on an empty hex (no token), you can view:
- **Position**: Row and column coordinates
- **Color**: Current cell color (painted or transparent)
- **Effect**: Any active effect on the cell

*Note: Hex cells have limited editing - use paint tools for full customization*

## Usage

### Step 1: Select Edit Data Tool
Click the **✏️ Edit Data** button in the Drawing Tools panel.

### Step 2: Click Target
- **Click a token** → Opens token editor
- **Click an empty hex** → Opens hex cell viewer

### Step 3: Edit Parameters
- Modify any field in the modal
- Toggle conditions on/off
- See live HP bar preview as you adjust values

### Step 4: Save Changes
Click **"Save Changes"** to apply, or **"Cancel"** to discard.

## Workflow Examples

### Quick HP Update
1. Select Edit Data tool (✏️)
2. Click the token
3. Update Current HP field
4. Click Save

### Add Multiple Conditions
1. Select Edit Data tool (✏️)
2. Click the token
3. Click multiple condition buttons to activate them
4. Conditions appear in the Active Conditions section
5. Click Save

### Change Token Type
1. Select Edit Data tool (✏️)
2. Click the token
3. Change Type dropdown (Player/Enemy/NPC)
4. Optionally adjust color to match
5. Click Save

### Adjust Token Size
1. Select Edit Data tool (✏️)
2. Click the token
3. Set Width and Height in hexes
4. Click Save
5. Token will occupy multiple hex cells

## Visual Feedback

### HP Bar Preview
- **Green**: >66% HP (healthy)
- **Orange**: 33-66% HP (wounded)
- **Red**: 1-33% HP (critical)
- **Gray**: 0% HP (unconscious/dead)

### Condition Colors
Each condition has a unique color that appears:
- In the condition ring around the token
- In the modal's condition buttons
- In the active conditions display

### Active Conditions Display
Shows all active conditions as colored tags with remove (×) buttons.

## Keyboard Shortcuts

- **ESC**: Close modal without saving
- **Enter**: (Not implemented - use Save button)

## Integration with Character Sheets

The Edit Data tool modifies token data that can be synchronized with character sheets:

### Data Flow
```
Edit Data Modal → Token State → CharacterToken Component → Visual Display
```

### Synchronized Fields
- `currentHp` / `hp`
- `maxHp`
- `conditions` array
- `name`
- `color`
- `type`

### Automatic Updates
When you save changes in Edit Data:
1. Token state is updated immediately
2. CharacterToken component re-renders
3. Health bar updates to reflect new HP
4. Condition rings appear/disappear based on active conditions
5. Tooltips show current condition descriptions

## Best Practices

### During Combat
1. Keep Edit Data tool selected for quick HP updates
2. Update HP after each hit/heal
3. Toggle conditions as they're applied/removed
4. Use HP bar preview to verify changes

### Token Setup
1. Place token first (Place Token tool)
2. Switch to Edit Data tool
3. Set HP, conditions, and properties
4. Token is ready for combat

### Managing Conditions
1. Click condition buttons to toggle (don't need to remove and re-add)
2. Active conditions show in the summary
3. Remove by clicking the × button on tags
4. Conditions persist across sessions (if saved)

## Tips & Tricks

### Rapid HP Changes
- Tab between Current HP and Max HP fields
- Use arrow keys for small adjustments
- Watch HP bar preview for visual feedback

### Bulk Condition Setup
- Click multiple conditions before saving
- All changes apply at once
- Reduces modal open/close cycles

### Color Coding Tokens
- **Green**: Player characters
- **Red**: Enemies
- **Blue**: Allies/NPCs
- **Purple**: Special/boss enemies

### Token Sizes
- **1×1**: Standard medium creatures
- **2×2**: Large creatures (ogres, horses)
- **3×3**: Huge creatures (giants, dragons)
- **4×4+**: Gargantuan creatures

## Troubleshooting

### Modal doesn't open
- Ensure Edit Data tool is selected (✏️ highlighted)
- Click directly on token or hex center
- Check that you're not in Watcher Mode

### Changes not saving
- Click "Save Changes" button (not × or Cancel)
- Verify Undo button shows new history entry
- Check browser console for errors

### Conditions not appearing
- Ensure condition is toggled in Active Conditions section
- Check that token has CharacterToken integration
- Verify condition name matches exactly (case-sensitive)

### HP bar not updating
- Refresh page if values seem stuck
- Verify Max HP is not 0
- Check that Current HP is a valid number

## API Reference

### Token Data Structure
```javascript
{
  id: 'unique-id',
  name: 'Character Name',
  currentHp: 85,
  maxHp: 100,
  color: '#3498db',
  type: 'player', // 'player' | 'enemy' | 'npc'
  width: 1,
  height: 1,
  row: 5,
  col: 5,
  conditions: [
    {
      name: 'Slowed',
      active: true,
      description: 'Initiative halved'
    }
  ]
}
```

### Condition Object
```javascript
{
  name: 'Slowed',
  active: true,
  description: 'Your Initiative is halved...'
}
```

### Edit Target Structure
```javascript
{
  type: 'token', // or 'hex'
  data: { ...tokenOrHexData },
  row: 5,
  col: 5,
  tokenId: 'unique-id' // only for tokens
}
```

## Related Tools

- **Place Token** (🎭): Create new tokens
- **Move Token** (👤): Reposition tokens on grid
- **Paint** (🖌️): Color hex cells
- **Debug** (🔍): View detailed hex/token data

## Future Enhancements

Planned improvements:
- [ ] Keyboard shortcuts (Enter to save, etc.)
- [ ] Copy token stats to clipboard
- [ ] Paste stats from another token
- [ ] Batch edit multiple tokens
- [ ] Condition duration tracking
- [ ] Auto-save on HP change
- [ ] History of HP changes
- [ ] Quick templates for common setups

## Version History

### v1.0.0 (Current)
- Initial release
- Token HP editing
- Condition management
- Hex cell viewing
- Color picker
- Size adjustment
- Type selection
