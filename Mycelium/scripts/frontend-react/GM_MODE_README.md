# 🎲 Game Master Mode

A specialized UI for Dungeon Masters to analyze and manage campaign content.

## Features

### 🎯 Move Analysis Tool

The Move Analysis tool helps you identify which bending moves need reworking or replacement based on uniqueness scores.

#### Uniqueness Scoring System

Each move is scored from **0-10** based on multiple factors:

- **Action Type** (0.5-1 points)
  - Reactions and Danger Sense Reactions are more unique (+1)
  - Standard Actions and Bonus Actions are common (+0)

- **Range Creativity** (0.5-1.5 points)
  - Self-range moves (+0.5)
  - Area of effect/radius (+1)
  - Cone/unique shapes (+1.5)

- **Effect Complexity** (0.5-2 points)
  - Concentration mechanics (+1.5)
  - Lingering effects (+2)
  - Conditions (prone, dazed, disadvantage) (+1)
  - Forced movement (push, pull, knock) (+0.5)

- **Utility Value** (0.5-1.5 points)
  - Movement/dash abilities (+0.5)
  - Environmental/terrain manipulation (+1.5)
  - Support/ally mechanics (+1)

- **Damage Variety** (0.5 points each)
  - Non-standard damage types (slashing, piercing)
  - Multi-hit/projectile mechanics

#### Score Interpretation

- **0-5**: 🔴 **Low Uniqueness** - Consider replacing or major rework
- **6-7**: 🟡 **Medium Uniqueness** - Functional but could be improved
- **8-10**: 🟢 **High Uniqueness** - Keep as-is, excellent design

#### Analysis Features

1. **Category Distribution** - See which move types are over/under-represented
2. **Similarity Detection** - Find moves that overlap too much
3. **Automated Recommendations** - Get prioritized suggestions for improvements
4. **Multi-level Comparison** - Analyze progression between levels

### Usage

1. **Select Element**: Choose air, water, earth, fire, or spirit
2. **Select Levels**: Pick which levels to compare (multi-select)
3. **Run Analysis**: Click "Run Analysis" to process moves
4. **Review Results**:
   - Summary statistics
   - Category distribution chart
   - Prioritized recommendations
   - Detailed move breakdown with uniqueness scores
   - Similar move detection

### Recommendations

The system generates three types of recommendations:

- ⚠️ **REPLACE** (High Priority) - Moves with low uniqueness that should be redesigned
- 🔄 **DIVERSIFY** (Medium Priority) - Overrepresented categories needing balance
- 💡 **ADD** (Low Priority) - Missing mechanics or categories

### Example Analysis Output

```
📊 Analysis Summary
Total Moves: 13
Low Uniqueness (≤5): 3
Medium (6-7): 6
High (>7): 4

⚠️ REPLACE (High Priority)
Affected moves: Air Blade, Wind Spear, Emergency Air Push
Reason: Low uniqueness scores and high similarity to other moves

🔄 DIVERSIFY (Medium Priority)
Categories: Damage, Forced Movement
Reason: Too many moves in these categories

💡 ADD (Low Priority)
Categories: Support, Area Control
Reason: Consider adding moves with these mechanics
```

## Future Tabs

### ⚖️ Balance Check (Coming Soon)
- Damage output calculations
- Resource cost analysis
- Power level comparisons across elements
- Level progression curves

### 📚 Content Overview (Coming Soon)
- NPC statistics and management
- Location tracking
- Story arc progression
- Campaign statistics dashboard

### 👥 Active Sessions
- View active player connections
- Monitor server logs
- Track session activity
- Access to log viewer

## Access

1. **Via URL Parameter**: Add `?gm=true` to the URL
2. **Via Toggle Button**: Click the "🎯 GM Mode" button in the top-right

## Backend Integration

The GM Mode connects to the Flask backend at `/api/analyze-moves`:

```json
POST /api/analyze-moves
{
  "element": "air",
  "levels": [1, 2]
}

Response:
{
  "moves": [
    {
      "name": "Air Blade",
      "level": 1,
      "actionType": "Action",
      "range": "...",
      "damage": "...",
      "effects": "...",
      "filePath": "..."
    }
  ],
  "element": "air",
  "levels": [1, 2]
}
```

## Development

The GM Mode is built with:
- React for UI
- Flask backend API
- Real-time analysis algorithms
- Responsive design with light/dark modes

### File Structure

```
frontend-react/src/components/
├── GameMasterMode.jsx      # Main component
├── GameMasterMode.css      # Styling
```

Backend API:
```
Mycelium/scripts/Python/
├── frontend_api.py         # API endpoints
└── run_backend.py          # Server
```

## Tips for Game Masters

1. **Regular Analysis**: Run move analysis after adding new content
2. **Balance Progressions**: Check level-by-level to ensure smooth power curves
3. **Diversify Categories**: Aim for variety in move types and effects
4. **Iterate on Low Scores**: Moves scoring below 5 likely need attention
5. **Compare Elements**: Analyze different elements to maintain parity

## Contributing

To add new analysis features:
1. Add analysis logic to `GameMasterMode.jsx`
2. Create corresponding backend endpoints in `frontend_api.py`
3. Update this README with new features
