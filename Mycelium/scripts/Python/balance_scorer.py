"""
Machine Learning-based Balance Scorer for Bending Moves
Uses TensorFlow to calculate balance scores based on move features
"""

import numpy as np
import re
from pathlib import Path
import json

# Try to import TensorFlow, fallback to manual scoring if not available
try:
    import tensorflow as tf
    from tensorflow import keras
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("TensorFlow not available, using rule-based scoring")


class BalanceScorer:
    """Calculate balance scores for bending moves using ML or rule-based methods."""
    
    def __init__(self, model_path=None, tuned_params_path=None):
        """Set up optional ML model paths and initialize feature defaults."""
        self.model = None
        self.model_path = model_path
        self.tuned_params = None
        
        # Feature normalization constants (learned from data)
        self.feature_stats = {
            'avg_damage_mean': 15.0,
            'avg_damage_std': 10.0,
            'cost_mean': 2.0,
            'cost_std': 1.5,
            'range_mean': 30.0,
            'range_std': 20.0
        }
        
        # Load tuned parameters if available
        if tuned_params_path and Path(tuned_params_path).exists():
            try:
                with open(tuned_params_path, 'r') as f:
                    self.tuned_params = json.load(f)
                print(f"✅ Loaded tuned balance parameters from {tuned_params_path}")
            except Exception as e:
                print(f"Could not load tuned parameters: {e}")
        else:
            # Try default location
            default_path = Path(__file__).parent / 'tuned_balance_params.json'
            if default_path.exists():
                try:
                    with open(default_path, 'r') as f:
                        self.tuned_params = json.load(f)
                    print(f"✅ Loaded tuned balance parameters from {default_path}")
                except Exception as e:
                    print(f"Could not load tuned parameters: {e}")
        
        if TF_AVAILABLE and model_path and Path(model_path).exists():
            try:
                self.model = keras.models.load_model(model_path)
                print(f"Loaded balance scoring model from {model_path}")
            except Exception as e:
                print(f"Could not load model: {e}, using rule-based scoring")
    
    def extract_features(self, move):
        """Extract numerical features from a move for ML processing."""
        features = {}
        
        # 1. Damage features
        damage_str = move.get('damage', '') or ''
        features['avg_damage'] = self._parse_average_damage(damage_str)
        features['max_damage'] = self._parse_max_damage(damage_str)
        features['has_damage'] = 1.0 if features['avg_damage'] > 0 else 0.0
        
        # 2. Cost features
        cost_str = move.get('cost', '') or ''
        features['slot_cost'] = self._parse_slot_cost(cost_str)
        features['water_cost'] = self._parse_water_cost(cost_str)
        features['total_cost'] = features['slot_cost'] + (features['water_cost'] * 0.5)
        
        # 3. Range features
        range_str = move.get('range', '') or ''
        features['range_feet'] = self._parse_range(range_str)
        features['is_self'] = 1.0 if 'self' in range_str.lower() else 0.0
        features['is_aoe'] = 1.0 if any(word in range_str.lower() for word in ['radius', 'cone', 'line', 'cube']) else 0.0
        
        # 4. Action economy features
        action_type = move.get('actionType', 'Action')
        features['is_action'] = 1.0 if action_type == 'Action' else 0.0
        features['is_bonus_action'] = 1.0 if 'Bonus' in action_type else 0.0
        features['is_reaction'] = 1.0 if 'Reaction' in action_type else 0.0
        
        # 5. Effect complexity features
        effects = (move.get('effects', '') or move.get('description', '') or '').lower()
        features['has_control'] = 1.0 if any(word in effects for word in ['prone', 'restrained', 'grappled', 'stunned']) else 0.0
        features['has_mobility'] = 1.0 if any(word in effects for word in ['move', 'dash', 'jump', 'fly']) else 0.0
        features['has_defense'] = 1.0 if any(word in effects for word in ['armor', 'cover', 'resistance', 'advantage']) else 0.0
        features['has_duration'] = 1.0 if any(word in effects for word in ['concentration', 'minute', 'hour', 'until']) else 0.0
        features['word_count'] = len(effects.split())
        
        # 6. Level feature
        features['level'] = float(move.get('level', 1))
        
        # 7. Derived metrics
        if features['total_cost'] > 0:
            features['damage_per_cost'] = features['avg_damage'] / features['total_cost']
            features['efficiency'] = (features['avg_damage'] + features['range_feet'] * 0.1) / features['total_cost']
        else:
            features['damage_per_cost'] = 0.0
            features['efficiency'] = 0.0
        
        # 8. Utility score (sum of non-damage benefits)
        features['utility_score'] = (
            features['has_control'] + 
            features['has_mobility'] + 
            features['has_defense'] + 
            features['has_duration']
        )
        
        return features
    
    def _parse_average_damage(self, damage_str):
        """Calculate average damage from dice notation."""
        if not damage_str:
            return 0.0
        
        total = 0.0
        # Match patterns like "2d6", "1d8", "3d10"
        dice_pattern = re.findall(r'(\d+)d(\d+)', damage_str.lower())
        for count, sides in dice_pattern:
            count = int(count)
            sides = int(sides)
            avg_per_die = (sides + 1) / 2.0
            total += count * avg_per_die
        
        # Add flat bonuses
        bonus_pattern = re.findall(r'\+\s*(\d+)', damage_str)
        for bonus in bonus_pattern:
            total += int(bonus)
        
        return total
    
    def _parse_max_damage(self, damage_str):
        """Calculate maximum possible damage."""
        if not damage_str:
            return 0.0
        
        total = 0.0
        dice_pattern = re.findall(r'(\d+)d(\d+)', damage_str.lower())
        for count, sides in dice_pattern:
            total += int(count) * int(sides)
        
        bonus_pattern = re.findall(r'\+\s*(\d+)', damage_str)
        for bonus in bonus_pattern:
            total += int(bonus)
        
        return total
    
    def _parse_slot_cost(self, cost_str):
        """Extract bending slot cost."""
        if not cost_str:
            return 0.0
        
        # Match patterns like "1 slot", "2 bending slots"
        match = re.search(r'(\d+)\s*(?:bending\s*)?slot', cost_str.lower())
        if match:
            return float(match.group(1))
        return 0.0
    
    def _parse_water_cost(self, cost_str):
        """Extract water charge cost."""
        if not cost_str:
            return 0.0
        
        # Match patterns like "1 water charge", "2 charges"
        match = re.search(r'(\d+)\s*(?:water\s*)?charge', cost_str.lower())
        if match:
            return float(match.group(1))
        return 0.0
    
    def _parse_range(self, range_str):
        """Extract range in feet."""
        if not range_str:
            return 0.0
        
        # Self range
        if 'self' in range_str.lower():
            return 5.0
        
        # Touch range
        if 'touch' in range_str.lower():
            return 5.0
        
        # Extract numeric range
        match = re.search(r'(\d+)\s*(?:ft|feet)', range_str.lower())
        if match:
            return float(match.group(1))
        
        return 0.0
    
    def calculate_ml_score(self, features):
        """Use ML model to calculate balance score."""
        if not self.model:
            return None
        
        try:
            # Prepare feature vector in the correct order
            feature_vector = np.array([
                features['avg_damage'],
                features['max_damage'],
                features['has_damage'],
                features['slot_cost'],
                features['water_cost'],
                features['total_cost'],
                features['range_feet'],
                features['is_self'],
                features['is_aoe'],
                features['is_action'],
                features['is_bonus_action'],
                features['is_reaction'],
                features['has_control'],
                features['has_mobility'],
                features['has_defense'],
                features['has_duration'],
                features['word_count'],
                features['level'],
                features['damage_per_cost'],
                features['efficiency'],
                features['utility_score']
            ], dtype=np.float32).reshape(1, -1)
            
            # Normalize features
            feature_vector = self._normalize_features(feature_vector)
            
            # Get prediction (should be between 0-10)
            prediction = self.model.predict(feature_vector, verbose=0)[0][0]
            return float(np.clip(prediction, 0.0, 10.0))
        
        except Exception as e:
            print(f"ML scoring error: {e}")
            return None
    
    def _normalize_features(self, features):
        """Normalize features for ML model input."""
        # Simple standardization - in production, use fitted scaler
        return (features - np.mean(features)) / (np.std(features) + 1e-8)
    
    def calculate_rule_based_score(self, features):
        """Calculate balance score using expert rules (with optional tuned parameters)."""
        # Use tuned parameters if available, otherwise use defaults
        if self.tuned_params:
            params = self.tuned_params
        else:
            params = {
                'base_score': 5.0,
                'damage_underpowered_threshold': 0.6,
                'damage_underpowered_penalty': 2.0,
                'damage_slightly_under_threshold': 0.8,
                'damage_slightly_under_penalty': 1.0,
                'damage_overpowered_threshold': 1.5,
                'damage_overpowered_bonus': 3.0,
                'damage_slightly_over_threshold': 1.2,
                'damage_slightly_over_bonus': 1.5,
                'efficiency_poor_threshold': 3.0,
                'efficiency_poor_penalty': 1.5,
                'efficiency_below_avg_threshold': 5.0,
                'efficiency_below_avg_penalty': 0.5,
                'efficiency_high_threshold': 12.0,
                'efficiency_high_bonus': 2.5,
                'efficiency_good_threshold': 8.0,
                'efficiency_good_bonus': 1.0,
                'utility_high_threshold': 3,
                'utility_high_bonus': 1.5,
                'utility_medium_threshold': 2,
                'utility_medium_bonus': 0.8,
                'utility_none_penalty': 2.0,
                'bonus_action_bonus': 0.8,
                'reaction_bonus': 0.5,
                'aoe_bonus': 1.0,
                'long_range_threshold': 60,
                'long_range_bonus': 0.5,
                'melee_penalty': 0.5,
                'melee_threshold': 5,
                'duration_penalty': 0.3
            }
        
        score = params['base_score']
        
        # Expected damage for level (benchmark)
        expected_damage_by_level = {
            1: 10, 2: 14, 3: 18, 4: 22, 5: 26
        }
        level = int(features.get('level', 1))
        expected_dmg = expected_damage_by_level.get(level, 10 + (level - 1) * 4)
        
        # 1. Damage analysis
        if features['has_damage'] > 0:
            dmg_ratio = features['avg_damage'] / expected_dmg if expected_dmg > 0 else 1.0
            
            if dmg_ratio < params['damage_underpowered_threshold']:
                score -= params['damage_underpowered_penalty']
            elif dmg_ratio < params['damage_slightly_under_threshold']:
                score -= params['damage_slightly_under_penalty']
            elif dmg_ratio > params['damage_overpowered_threshold']:
                score += params['damage_overpowered_bonus']
            elif dmg_ratio > params['damage_slightly_over_threshold']:
                score += params['damage_slightly_over_bonus']
        
        # 2. Cost efficiency
        if features['total_cost'] > 0:
            efficiency = features['efficiency']
            
            if efficiency < params['efficiency_poor_threshold']:
                score -= params['efficiency_poor_penalty']
            elif efficiency < params['efficiency_below_avg_threshold']:
                score -= params['efficiency_below_avg_penalty']
            elif efficiency > params['efficiency_high_threshold']:
                score += params['efficiency_high_bonus']
            elif efficiency > params['efficiency_good_threshold']:
                score += params['efficiency_good_bonus']
        
        # 3. Utility value
        utility = features['utility_score']
        if utility >= params['utility_high_threshold']:
            score += params['utility_high_bonus']
        elif utility >= params['utility_medium_threshold']:
            score += params['utility_medium_bonus']
        elif utility == 0 and features['has_damage'] == 0:
            score -= params['utility_none_penalty']
        
        # 4. Action economy
        if features['is_bonus_action'] > 0:
            score += params['bonus_action_bonus']
        elif features['is_reaction'] > 0:
            score += params['reaction_bonus']
        
        # 5. Range consideration
        if features['is_aoe'] > 0:
            score += 1.0  # AoE is powerful
        # 5. Range consideration
        if features['is_aoe'] > 0:
            score += params['aoe_bonus']
        if features['range_feet'] > params['long_range_threshold']:
            score += params['long_range_bonus']
        elif features['range_feet'] <= params['melee_threshold']:
            score -= params['melee_penalty']
        
        # 6. Duration/concentration penalty
        if features['has_duration'] > 0:
            score -= params['duration_penalty']
        
        # Clamp to 0-10 range
        return float(np.clip(score, 0.0, 10.0))
    
    def score_move(self, move):
        """Calculate balance score for a move (0-10 scale)."""
        features = self.extract_features(move)
        
        # Try ML scoring first, fall back to rule-based
        ml_score = self.calculate_ml_score(features) if TF_AVAILABLE and self.model else None
        
        if ml_score is not None:
            return {
                'score': ml_score,
                'method': 'ml',
                'features': features
            }
        else:
            rule_score = self.calculate_rule_based_score(features)
            method = 'tuned' if self.tuned_params else 'rule-based'
            return {
                'score': rule_score,
                'method': method,
                'features': features
            }
    
    def generate_feedback(self, move, score_data):
        """Generate human-readable feedback about the balance."""
        score = score_data['score']
        features = score_data['features']
        
        feedback = {
            'score': score,
            'rating': self._get_rating(score),
            'warnings': [],
            'strengths': [],
            'recommendations': []
        }
        
        # Analyze issues
        if score <= 3.5:
            feedback['warnings'].append('⚠️ Significantly underpowered for its level')
        elif score >= 8.0:
            feedback['warnings'].append('⚠️ Potentially overpowered')
        
        # Damage analysis
        if features['has_damage'] > 0:
            if features['avg_damage'] < 5:
                feedback['warnings'].append('⚠️ Very low damage output')
            elif features['avg_damage'] > 30:
                feedback['warnings'].append('⚠️ Extremely high damage')
                feedback['recommendations'].append('Consider reducing damage dice or adding a cost')
        
        # Efficiency check
        if features['efficiency'] > 12:
            feedback['warnings'].append('⚠️ Too cost-efficient')
            feedback['recommendations'].append('Increase slot cost or reduce power')
        elif features['efficiency'] < 3 and features['total_cost'] > 0:
            feedback['warnings'].append('⚠️ Poor cost-to-benefit ratio')
            feedback['recommendations'].append('Reduce cost or increase effects')
        
        # Utility analysis
        if features['utility_score'] >= 3:
            feedback['strengths'].append('✅ High utility value')
        if features['is_aoe'] > 0:
            feedback['strengths'].append('✅ Area of effect')
        if features['is_bonus_action'] > 0:
            feedback['strengths'].append('✅ Bonus action economy')
        
        # Lack of benefits
        if features['utility_score'] == 0 and features['has_damage'] == 0:
            feedback['warnings'].append('⚠️ No clear benefit or damage')
            feedback['recommendations'].append('Add damage, utility, or control effects')
        
        return feedback
    
    def _get_rating(self, score):
        """Convert numeric score to rating."""
        if score <= 3:
            return 'Severely Underpowered'
        elif score <= 4.5:
            return 'Underpowered'
        elif score <= 5.5:
            return 'Slightly Below Average'
        elif score <= 7:
            return 'Well Balanced'
        elif score <= 8:
            return 'Slightly Above Average'
        elif score <= 9:
            return 'Overpowered'
        else:
            return 'Severely Overpowered'


# Global scorer instance
_scorer_instance = None

def get_scorer():
    """Get or create the global balance scorer instance."""
    global _scorer_instance
    if _scorer_instance is None:
        # Try to load model from default location
        model_path = Path(__file__).parent / 'models' / 'balance_model.keras'
        _scorer_instance = BalanceScorer(model_path if model_path.exists() else None)
    return _scorer_instance
