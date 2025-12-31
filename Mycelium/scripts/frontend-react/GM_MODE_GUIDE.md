# 🎯 Game Master Mode - Complete Guide

## Overview

Game Master Mode is a specialized interface designed to help DMs analyze, balance, and manage their ATLA campaign content. It provides powerful tools for identifying issues with moves, checking balance, and gaining insights into your campaign structure.

## Quick Start

### Option 1: Direct Access
```bash
./start_gm_mode.sh
```
Then visit: `http://localhost:5173?gm=true`

### Option 2: Toggle in App
1. Start the game normally with `./start_game.sh`
2. Click the **"🎯 GM Mode"** button in the top-right corner

## Features

### 1. 🎯 Move Analysis Tool

#### What It Does
Analyzes bending moves to identify:
- Moves with low uniqueness (potential replacements)
- Over-represented move categories
- Missing mechanics
- Similar/redundant moves

#### How It Works

**Step 1: Configure Analysis**
- Select element (air, water, earth, fire, spirit)
- Choose levels to compare (multi-select)
- Set minimum uniqueness threshold filter
- Choose sort order

**Step 2: Run Analysis**
Click "🔍 Run Analysis" - the system will:
1. Load all moves from selected levels
2. Parse move properties (action type, range, effects)
3. Calculate uniqueness scores (0-10)
4. Detect similar moves
5. Generate recommendations

**Step 3: Review Results**

The analysis provides:

##### Summary Statistics
- Total moves analyzed
- Distribution by uniqueness score
- Category breakdown
- Visual distribution chart

##### Recommendations
Three priority levels:
- ⚠️ **High Priority (Replace)**: Moves scoring ≤5
- 🟡 **Medium Priority (Diversify)**: Overrepresented categories
- 💡 **Low Priority (Add)**: Missing mechanics

##### Detailed Move Cards
Each move shows:
- Uniqueness score (color-coded)
- Level and action type
- Range and damage info
- Complete effects
- Category tags
- Similar moves (if any)

#### Uniqueness Scoring Formula

```
Base Score: 5

+ Action Type:
  - Reaction/Danger Sense: +1
  
+ Range Creativity:
  - Self: +0.5
  - Radius/Area: +1
  - Cone/Special: +1.5
  
+ Effects:
  - Concentration: +1.5
  - Lingering effects: +2
  - Conditions (prone/dazed): +1
  - Forced movement: +0.5
  
+ Utility:
  - Movement: +0.5
  - Terrain manipulation: +1.5
  - Support/ally effects: +1
  
+ Damage Variety:
  - Special damage types: +0.5
  - Multi-hit mechanics: +0.5

Maximum: 10
```

#### Score Meanings

| Score | Rating | Action |
|-------|--------|--------|
| 0-4 | 🔴 Very Low | **Must replace** - Too generic or redundant |
| 5 | 🟠 Low | **Should replace** - Lacks unique identity |
| 6-7 | 🟡 Medium | **Consider rework** - Functional but improvable |
| 8 | 🟢 Good | **Keep** - Solid unique design |
| 9-10 | 🌟 Excellent | **Definitely keep** - Outstanding uniqueness |

#### Example Analysis Session

**Scenario**: Analyzing Air Levels 1-2

**Results**:
```
📊 Summary:
- Total: 13 moves
- Low (≤5): 3 moves
- Medium (6-7): 6 moves  
- High (>7): 4 moves

⚠️ REPLACE Recommendations:
1. Air Blade (4/10) - Generic ranged attack
2. Wind Spear (5/10) - Too similar to Air Blade
3. Emergency Air Push (5/10) - Redundant with Gentle Push

📊 Category Distribution:
- Damage: 4 moves (overrepresented)
- Mobility: 3 moves
- Defense: 2 moves
- Support: 1 move (underrepresented)

💡 Suggestions:
- Replace Air Blade with unique mechanic
- Merge Wind Spear and Air Blade concepts
- Add more support-oriented moves
```

### 2. ⚖️ Balance Check (Coming Soon)

Planned features:
- DPS calculations across elements
- Resource cost efficiency
- Power level curves
- Encounter difficulty calculator

### 3. 📚 Content Overview (Coming Soon)

Planned features:
- NPC database and stats
- Location catalog
- Story arc tracker
- Session notes
- Campaign statistics

### 4. 👥 Active Sessions

View:
- Connected players
- Request activity
- Session duration
- Direct link to log viewer

## Advanced Features

### Filtering and Sorting

**Filter by Score**:
Use the threshold slider to hide low-scoring moves and focus on specific ranges.

**Sort Options**:
- Uniqueness: Low to high scores
- Name: Alphabetical
- Level: Progression order
- Action Type: Group by action types

### Category System

Moves are automatically categorized:
- **Damage**: Attack rolls, damage output
- **Mobility**: Movement, dashes, teleports
- **Forced Movement**: Push, pull, knockback
- **Defense**: Armor, damage reduction, deflection
- **Control**: Conditions, CC, debuffs
- **Area Control**: Terrain, lingering effects, zones
- **Support**: Ally buffs, healing, positioning help
- **Utility**: Miscellaneous unique effects

### Similarity Detection

The system compares moves based on:
- Action type match (30% weight)
- Category overlap (40% weight)
- Range similarity (30% weight)

Moves with >60% similarity are flagged.

## Best Practices

### For Move Analysis

1. **Analyze Regularly**: Run after adding/modifying moves
2. **Compare Adjacent Levels**: Check 1-2, 2-3, etc. for progression
3. **Act on High Priority**: Address red-flagged moves first
4. **Maintain Diversity**: Aim for variety in categories
5. **Document Changes**: Track which moves you've reworked

### Identifying Good Candidates for Replacement

Replace moves that have:
- ✗ Uniqueness score ≤ 5
- ✗ 2+ similar moves
- ✗ Generic description ("deals damage", "move faster")
- ✗ No special mechanics or conditions

Keep moves that have:
- ✓ Uniqueness score ≥ 8
- ✓ Unique mechanics
- ✓ Multiple effects or conditions
- ✓ Interesting tactical options

### Designing Better Replacements

Good replacement moves:
1. **Combine effects**: Don't just damage - add utility
2. **Add conditions**: Prone, dazed, disadvantage
3. **Create interactions**: Synergize with terrain or allies
4. **Use unique shapes**: Cones, lines, donuts, not just circles
5. **Add decisions**: Give players choices within the move

Example transformation:
```
❌ Before: Air Blade
- Simple 1d6 damage per slot
- Ranged attack roll
- Nothing special

✓ After: Severing Gust
- 1d6 damage per slot
- Ranged attack roll
- On hit: Target must choose:
  * Drop one held item
  * Take disadvantage on next attack
- Severs ropes and light objects in path
```

## Troubleshooting

### Backend Connection Issues

If analysis fails:
1. Check backend is running: `lsof -i :9002`
2. Check console for errors (F12)
3. Verify file paths in terminal output
4. Try restarting: `./stop_game.sh && ./start_game.sh`

### Missing Moves

If moves don't appear:
1. Verify folder structure matches: `Rules/Bending Rules/{Element}/{Element}bending Moves/Level {N}/`
2. Check file extensions are `.md`
3. Ensure moves have required tags (#Action, #Bonus_Action, etc.)
4. Check console for parsing errors

### Incorrect Scores

Scores seem off? The algorithm prioritizes:
- Unique mechanics over high damage
- Tactical variety over simplicity
- Multiple effects over single purpose
- Interesting choices over straightforward actions

Adjust expectations: A simple but effective move might score 6-7, which is fine!

## Integration with Existing Workflows

### With Character Sheets
1. Analyze moves in GM Mode
2. Identify changes needed
3. Edit move files in file explorer
4. Character sheets automatically reflect updates

### With Campaign Planning
1. Review move balance before sessions
2. Ensure players have diverse options
3. Identify gaps in party capabilities
4. Design encounters around available moves

## API Reference

### Analyze Moves Endpoint

```http
POST /api/analyze-moves
Content-Type: application/json

{
  "element": "air",
  "levels": [1, 2, 3]
}
```

Response:
```json
{
  "moves": [
    {
      "name": "Air Blade",
      "level": 1,
      "element": "air",
      "actionType": "Action",
      "range": "X meters",
      "damage": "1d6 per slot",
      "effects": "Send a blade of air...",
      "filePath": "Player Root/Rules/..."
    }
  ],
  "element": "air",
  "levels": [1, 2, 3]
}
```

## Roadmap

### Version 1.1 (Current)
- ✅ Move analysis with uniqueness scoring
- ✅ Category distribution
- ✅ Similarity detection
- ✅ Automated recommendations
- ✅ Multi-level comparison

### Version 1.2 (Planned)
- ⏳ Balance checker with DPS calculations
- ⏳ Resource cost efficiency analysis
- ⏳ Power curve visualization
- ⏳ Export analysis reports

### Version 1.3 (Planned)
- ⏳ Content overview dashboard
- ⏳ NPC management
- ⏳ Location database
- ⏳ Story arc tracker

### Version 2.0 (Future)
- ⏳ Custom scoring formulas
- ⏳ Encounter builder
- ⏳ Automated balance suggestions
- ⏳ Move generator AI assistance

## Support

Having issues or ideas?
1. Check this guide first
2. Review console logs (F12)
3. Check backend logs in `logs/` directory
4. Document the issue with screenshots

## Credits

Built with:
- React + Vite
- Flask backend
- Custom analysis algorithms
- Love for ATLA and great game design ❤️
