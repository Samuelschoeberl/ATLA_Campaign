"""
Full Analysis Scorer for Avatar TTRPG Moves
Combines uniqueness, balance, and simplicity using ML
"""

import numpy as np
import json
from pathlib import Path

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("⚠ TensorFlow not available for Full Analysis ML")

class FullAnalysisScorer:
    """Combines uniqueness, balance, and simplicity scores using ML"""
    
    def __init__(self):
        self.params = self._load_params()
        self.model = None
        if TF_AVAILABLE:
            self._try_load_model()
    
    def _load_params(self):
        """Load tuned parameters if available, else use defaults"""
        params_path = Path(__file__).parent / 'tuned_full_analysis_params.json'
        
        if params_path.exists():
            try:
                with open(params_path, 'r') as f:
                    params = json.load(f)
                print("✓ Loaded tuned full analysis parameters")
                return params
            except Exception as e:
                print(f"⚠ Error loading tuned params: {e}")
        
        # Default weights for combining scores
        return {
            'balance_weight': 0.40,      # Balance is most important
            'uniqueness_weight': 0.35,   # Uniqueness is important for fun
            'simplicity_weight': 0.25,   # Simplicity helps usability
            'balance_target': 5.0,       # Ideal balance score
            'uniqueness_target': 7.0,    # Prefer unique moves
            'simplicity_target': 7.0,    # Prefer simple moves
            'balance_deviation_penalty': 0.5,
            'synergy_bonus': 0.3,        # Bonus if all scores are good
            'consistency_bonus': 0.2     # Bonus if scores are similar
        }
    
    def _try_load_model(self):
        """Try to load pre-trained TensorFlow model"""
        model_path = Path(__file__).parent / 'full_analysis_model'
        
        if model_path.exists():
            try:
                self.model = tf.keras.models.load_model(str(model_path))
                print("✓ Loaded full analysis ML model")
            except Exception as e:
                print(f"⚠ Could not load model: {e}")
    
    def extract_combined_features(self, uniqueness_score, balance_score, simplicity_score, 
                                   uniqueness_data=None, balance_data=None, simplicity_data=None):
        """Extract features from all three scoring systems"""
        features = []
        
        # Core scores
        features.append(balance_score / 10.0)       # Normalized 0-1
        features.append(uniqueness_score / 10.0)
        features.append(simplicity_score / 10.0)
        
        # Score relationships
        features.append(abs(balance_score - uniqueness_score) / 10.0)  # Balance-uniqueness gap
        features.append(abs(balance_score - simplicity_score) / 10.0)  # Balance-simplicity gap
        features.append(abs(uniqueness_score - simplicity_score) / 10.0)  # Uniqueness-simplicity gap
        
        # Distance from ideal
        features.append(abs(balance_score - 5.0) / 10.0)      # Distance from balanced
        features.append(abs(uniqueness_score - 7.0) / 10.0)   # Distance from unique
        features.append(abs(simplicity_score - 7.0) / 10.0)   # Distance from simple
        
        # Score variance (are they consistent?)
        scores = [balance_score, uniqueness_score, simplicity_score]
        variance = np.var(scores)
        features.append(variance / 10.0)
        
        # Additional contextual features if available
        if balance_data and 'balanceMetrics' in balance_data:
            metrics = balance_data['balanceMetrics']
            features.append(min(metrics.get('damagePerSlot', 0) / 30.0, 1.0))  # Efficiency
            features.append(min(metrics.get('powerLevel', 0) / 50.0, 1.0))     # Power
        else:
            features.extend([0.5, 0.5])  # Neutral defaults
        
        if uniqueness_data:
            synergy_count = len(uniqueness_data.get('synergies', []))
            features.append(min(synergy_count / 5.0, 1.0))  # Synergy potential
        else:
            features.append(0.5)
        
        if simplicity_data and 'features' in simplicity_data:
            feat = simplicity_data['features']
            features.append(min(feat.get('word_count', 15) / 30.0, 1.0))  # Brevity
            features.append(min(feat.get('flesch_score', 60) / 100.0, 1.0))  # Readability
        else:
            features.extend([0.5, 0.6])
        
        return np.array(features, dtype=np.float32)
    
    def calculate_ml_score(self, uniqueness_score, balance_score, simplicity_score,
                           uniqueness_data=None, balance_data=None, simplicity_data=None):
        """Calculate overall score using ML model"""
        if not TF_AVAILABLE or self.model is None:
            return None
        
        try:
            features = self.extract_combined_features(
                uniqueness_score, balance_score, simplicity_score,
                uniqueness_data, balance_data, simplicity_data
            )
            
            # Reshape for model input
            features = features.reshape(1, -1)
            
            # Get prediction
            prediction = self.model.predict(features, verbose=0)[0][0]
            
            # Scale to 0-10
            score = float(prediction * 10.0)
            score = max(0.0, min(10.0, score))
            
            return round(score, 1)
        except Exception as e:
            print(f"⚠ ML scoring error: {e}")
            return None
    
    def calculate_weighted_score(self, uniqueness_score, balance_score, simplicity_score):
        """Calculate weighted average of the three scores with smart adjustments"""
        params = self.params
        
        # Base weighted average
        weighted_score = (
            balance_score * params['balance_weight'] +
            uniqueness_score * params['uniqueness_weight'] +
            simplicity_score * params['simplicity_weight']
        )
        
        # Penalty for being far from ideal balance
        balance_deviation = abs(balance_score - params['balance_target'])
        if balance_deviation > 2.0:
            weighted_score -= (balance_deviation - 2.0) * params['balance_deviation_penalty']
        
        # Synergy bonus: all three scores are good (>6.5)
        if all(s >= 6.5 for s in [balance_score, uniqueness_score, simplicity_score]):
            weighted_score += params['synergy_bonus']
        
        # Consistency bonus: scores are within 2 points of each other
        score_range = max([balance_score, uniqueness_score, simplicity_score]) - \
                      min([balance_score, uniqueness_score, simplicity_score])
        if score_range <= 2.0:
            weighted_score += params['consistency_bonus']
        
        # Penalty for any score being critically low (<3.5)
        if any(s < 3.5 for s in [balance_score, uniqueness_score, simplicity_score]):
            min_score = min([balance_score, uniqueness_score, simplicity_score])
            weighted_score -= (3.5 - min_score) * 0.5
        
        # Clamp to 0-10
        weighted_score = max(0.0, min(10.0, weighted_score))
        
        return round(weighted_score, 1)
    
    def calculate_score(self, uniqueness_score, balance_score, simplicity_score,
                       uniqueness_data=None, balance_data=None, simplicity_data=None):
        """Calculate overall score, trying ML first, then falling back to weighted"""
        # Try ML approach first
        ml_score = self.calculate_ml_score(
            uniqueness_score, balance_score, simplicity_score,
            uniqueness_data, balance_data, simplicity_data
        )
        
        if ml_score is not None:
            return {
                'score': ml_score,
                'method': 'ml',
                'breakdown': {
                    'balance': balance_score,
                    'uniqueness': uniqueness_score,
                    'simplicity': simplicity_score
                }
            }
        
        # Fall back to weighted approach
        weighted_score = self.calculate_weighted_score(
            uniqueness_score, balance_score, simplicity_score
        )
        
        return {
            'score': weighted_score,
            'method': 'weighted',
            'breakdown': {
                'balance': balance_score,
                'uniqueness': uniqueness_score,
                'simplicity': simplicity_score
            }
        }
    
    def generate_feedback(self, uniqueness_score, balance_score, simplicity_score,
                         uniqueness_data=None, balance_data=None, simplicity_data=None):
        """Generate comprehensive feedback for full analysis"""
        result = self.calculate_score(
            uniqueness_score, balance_score, simplicity_score,
            uniqueness_data, balance_data, simplicity_data
        )
        
        overall_score = result['score']
        
        # Overall rating
        if overall_score >= 8.5:
            rating = "Exceptional Move"
        elif overall_score >= 7.5:
            rating = "Excellent Move"
        elif overall_score >= 6.5:
            rating = "Good Move"
        elif overall_score >= 5.5:
            rating = "Decent Move"
        elif overall_score >= 4.5:
            rating = "Needs Improvement"
        else:
            rating = "Significant Issues"
        
        strengths = []
        warnings = []
        recommendations = []
        
        # Analyze individual components
        if balance_score >= 7.5:
            strengths.append("Well-balanced power level")
        elif balance_score <= 3.5:
            warnings.append("Balance issues detected")
            if balance_score < 5.0:
                recommendations.append("Buff this move - increase damage or add utility")
            else:
                recommendations.append("Nerf this move - reduce power or increase cost")
        
        if uniqueness_score >= 8.0:
            strengths.append("Highly unique and creative")
        elif uniqueness_score <= 5.0:
            warnings.append("Low uniqueness - similar to other moves")
            recommendations.append("Add unique mechanics or synergies")
        
        if simplicity_score >= 8.0:
            strengths.append("Clear and concise description")
        elif simplicity_score <= 5.0:
            warnings.append("Overly complex wording")
            recommendations.append("Simplify description - use fewer, clearer words")
        
        # Check for balance
        score_range = max([balance_score, uniqueness_score, simplicity_score]) - \
                      min([balance_score, uniqueness_score, simplicity_score])
        
        if score_range <= 2.0:
            strengths.append("Well-rounded across all dimensions")
        elif score_range >= 4.0:
            warnings.append("Inconsistent scores across dimensions")
            # Identify weakest dimension
            scores = {'balance': balance_score, 'uniqueness': uniqueness_score, 'simplicity': simplicity_score}
            weakest = min(scores.items(), key=lambda x: x[1])
            recommendations.append(f"Focus on improving {weakest[0]} (score: {weakest[1]})")
        
        # Synergy check
        if all(s >= 6.5 for s in [balance_score, uniqueness_score, simplicity_score]):
            strengths.append("Excellent synergy across all aspects")
        
        # Method indicator
        method_badge = "🤖 ML-Powered" if result['method'] == 'ml' else "📊 Weighted Analysis"
        
        return {
            'score': overall_score,
            'rating': rating,
            'method': result['method'],
            'method_badge': method_badge,
            'breakdown': result['breakdown'],
            'strengths': strengths,
            'warnings': warnings,
            'recommendations': recommendations
        }

# Singleton instance
_scorer = None

def get_scorer():
    """Get or create full analysis scorer instance"""
    global _scorer
    if _scorer is None:
        _scorer = FullAnalysisScorer()
    return _scorer
