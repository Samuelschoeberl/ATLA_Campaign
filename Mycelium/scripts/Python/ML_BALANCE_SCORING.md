# ML Balance Scoring System

## Overview
The balance scoring system uses machine learning (TensorFlow) to evaluate bending moves on a 0-10 scale, where:
- **0-3.5**: Severely Underpowered
- **3.5-4.5**: Underpowered  
- **4.5-5.5**: Slightly Below Average
- **5.5-7**: Well Balanced ⭐
- **7-8**: Slightly Above Average
- **8-9**: Overpowered
- **9-10**: Severely Overpowered

## Features Extracted

The system analyzes **21 features** from each move:

### Damage Features (3)
- Average damage (from dice notation)
- Maximum possible damage
- Has damage flag

### Cost Features (3)
- Bending slot cost
- Water charge cost
- Total cost (slots + water*0.5)

### Range Features (3)
- Range in feet
- Is self-targeted
- Is area of effect

### Action Economy (3)
- Is standard action
- Is bonus action
- Is reaction

### Effect Complexity (5)
- Has control effects (prone, stun, etc.)
- Has mobility effects (dash, fly, etc.)
- Has defense effects (armor, resistance, etc.)
- Has duration/concentration
- Word count in description

### Level (1)
- Move level (1-5)

### Derived Metrics (3)
- Damage per cost
- Overall efficiency
- Utility score

## Scoring Method

### ML-Based (When Available)
1. Extract 21 features from move
2. Normalize features
3. Pass through TensorFlow neural network
4. Get balanced score prediction (0-10)

### Rule-Based (Fallback)
Expert rules that consider:
- Expected damage for level
- Cost efficiency 
- Utility value
- Action economy
- Range and AoE
- Duration penalties

## Usage

### Backend (Automatic)
When the `/api/analyze-moves` endpoint is called, each move is automatically scored:

```python
from balance_scorer import get_scorer

scorer = get_scorer()
result = scorer.score_move(move_data)
feedback = scorer.generate_feedback(move_data, result)
```

### Frontend Display
Balance scores are displayed with:
- 🤖 **ML-Powered** badge (when TensorFlow model is used)
- 📊 **Rule-Based** badge (when fallback rules are used)
- Rating text (e.g., "Well Balanced", "Overpowered")
- Detailed warnings and recommendations

## Training a Model (Future)

To train a custom TensorFlow model:

1. Collect labeled move data (moves with known balance scores)
2. Create training script:
```python
import tensorflow as tf
from balance_scorer import BalanceScorer

# Load your labeled data
X_train, y_train = load_training_data()

# Build model
model = tf.keras.Sequential([
    tf.keras.layers.Dense(64, activation='relu', input_shape=(21,)),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(16, activation='relu'),
    tf.keras.layers.Dense(1, activation='linear')  # Output: 0-10 score
])

model.compile(
    optimizer='adam',
    loss='mse',
    metrics=['mae']
)

# Train
model.fit(X_train, y_train, epochs=100, validation_split=0.2)

# Save
model.save('models/balance_model.keras')
```

3. Place trained model at: `Mycelium/scripts/Python/models/balance_model.keras`

## Dependencies

- `tensorflow>=2.0` (optional, will fallback to rule-based)
- `numpy>=1.19`

Install with:
```bash
pip3 install tensorflow numpy
```

## File Structure

```
Mycelium/scripts/Python/
├── balance_scorer.py          # Main scoring module
├── frontend_api.py            # API integration
├── models/                    # Trained models directory
│   └── balance_model.keras    # (optional) Trained TensorFlow model
└── ML_BALANCE_SCORING.md     # This file
```

## API Response Format

When ML scoring is active, moves include:

```json
{
  "name": "Fire Blast",
  "mlBalanceScore": 7.2,
  "mlScoringMethod": "ml",
  "mlFeedback": {
    "score": 7.2,
    "rating": "Slightly Above Average",
    "warnings": ["⚠️ High damage output"],
    "strengths": ["✅ Area of effect"],
    "recommendations": ["Consider increasing slot cost"]
  }
}
```

## Performance

- **Rule-Based**: Instant (< 1ms per move)
- **ML-Based**: Fast (< 10ms per move with TensorFlow)
- **Batch Processing**: Handles 100+ moves efficiently

## Future Enhancements

- [ ] Train model on actual gameplay data
- [ ] Add synergy detection to scoring
- [ ] Compare moves across elements
- [ ] Generate balancing suggestions automatically
- [ ] Export balance reports
