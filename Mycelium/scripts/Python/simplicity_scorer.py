"""
Simplicity Scorer for Avatar TTRPG Moves
Rewards simple structure, clear wording, and brevity
"""

import re
import json
from pathlib import Path

class SimplicityScorer:
    """Scores moves based on simplicity, clarity, and brevity"""
    
    def __init__(self):
        """Load tuned parameter defaults for simplicity scoring."""
        self.params = self._load_params()
    
    def _load_params(self):
        """Load tuned parameters if available, else use defaults"""
        params_path = Path(__file__).parent / 'tuned_simplicity_params.json'
        
        if params_path.exists():
            try:
                with open(params_path, 'r') as f:
                    params = json.load(f)
                print("✓ Loaded tuned simplicity parameters")
                return params
            except Exception as e:
                print(f"⚠ Error loading tuned params: {e}")
        
        # Default parameters
        return {
            'base_score': 7.0,
            'word_count_optimal': 15,
            'word_count_penalty_per': 0.15,
            'sentence_count_penalty_per': 0.3,
            'complex_word_penalty': 0.2,
            'jargon_penalty': 0.4,
            'clause_penalty': 0.25,
            'parentheses_penalty': 0.3,
            'long_sentence_threshold': 20,
            'long_sentence_penalty': 0.5,
            'dice_notation_bonus': 0.5,
            'simple_range_bonus': 0.3,
            'simple_duration_bonus': 0.3,
            'brevity_bonus_threshold': 10,
            'brevity_bonus': 1.0,
            'clarity_bonus': 0.5
        }
    
    def extract_features(self, move):
        """Extract simplicity-related features from a move"""
        # Get description, handling None values
        description = move.get('effects') or move.get('description') or ''
        if not isinstance(description, str):
            description = str(description) if description else ''
        
        # Word count and sentence analysis
        words = description.split()
        word_count = len(words)
        sentences = re.split(r'[.!?]+', description)
        sentence_count = len([s for s in sentences if s.strip()])
        
        # Average words per sentence
        avg_words_per_sentence = word_count / max(sentence_count, 1)
        
        # Count complex words (3+ syllables, rough approximation)
        complex_words = sum(1 for word in words if self._estimate_syllables(word) >= 3)
        complex_word_ratio = complex_words / max(word_count, 1)
        
        # Count technical jargon terms
        jargon_terms = ['additional', 'temporarily', 'immediately', 'simultaneously', 
                       'subsequently', 'disadvantage', 'advantage', 'concentration',
                       'instantaneous', 'prerequisite', 'component']
        jargon_count = sum(1 for word in words if word.lower() in jargon_terms)
        
        # Count complex sentence structures
        clause_indicators = [',', ';', ':', 'and', 'or', 'but', 'if', 'when', 'while']
        clause_count = sum(description.lower().count(indicator) for indicator in clause_indicators)
        
        # Count parentheses (often indicate complexity)
        parentheses_count = description.count('(') + description.count('[')
        
        # Check for simple, standardized patterns (handle None values)
        damage = move.get('damage') or ''
        range_text = move.get('range') or ''
        duration = move.get('duration') or ''
        
        has_simple_damage = bool(re.search(r'^\d+d\d+$', str(damage)))
        has_simple_range = str(range_text).lower() in ['self', 'touch', 'melee', '30 feet', '60 feet', '120 feet']
        has_simple_duration = str(duration).lower() in ['instantaneous', '1 round', '1 minute', 'concentration']
        
        # Readability score (simplified Flesch reading ease)
        flesch_score = 206.835 - 1.015 * avg_words_per_sentence - 84.6 * (complex_word_ratio * 10)
        
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'avg_words_per_sentence': avg_words_per_sentence,
            'complex_word_ratio': complex_word_ratio,
            'jargon_count': jargon_count,
            'clause_count': clause_count,
            'parentheses_count': parentheses_count,
            'has_simple_damage': has_simple_damage,
            'has_simple_range': has_simple_range,
            'has_simple_duration': has_simple_duration,
            'flesch_score': flesch_score,
            'description': description
        }
    
    def _estimate_syllables(self, word):
        """Rough syllable estimation"""
        word = word.lower()
        vowels = 'aeiouy'
        syllable_count = 0
        previous_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel
        
        # Adjust for silent e
        if word.endswith('e'):
            syllable_count -= 1
        
        return max(1, syllable_count)
    
    def calculate_score(self, move):
        """Calculate simplicity score (0-10, higher = simpler/better)"""
        features = self.extract_features(move)
        params = self.params
        
        score = params['base_score']
        
        # Penalty for word count deviation from optimal
        word_deviation = abs(features['word_count'] - params['word_count_optimal'])
        score -= word_deviation * params['word_count_penalty_per']
        
        # Penalty for multiple sentences (prefer concise single-sentence descriptions)
        if features['sentence_count'] > 1:
            score -= (features['sentence_count'] - 1) * params['sentence_count_penalty_per']
        
        # Penalty for complex words
        score -= features['complex_word_ratio'] * 10 * params['complex_word_penalty']
        
        # Penalty for jargon
        score -= features['jargon_count'] * params['jargon_penalty']
        
        # Penalty for complex sentence structure (many clauses)
        score -= features['clause_count'] * params['clause_penalty']
        
        # Penalty for parentheses (indicate clarifications/complexity)
        score -= features['parentheses_count'] * params['parentheses_penalty']
        
        # Penalty for long sentences
        if features['avg_words_per_sentence'] > params['long_sentence_threshold']:
            excess = features['avg_words_per_sentence'] - params['long_sentence_threshold']
            score -= excess * params['long_sentence_penalty']
        
        # Bonuses for standardized formats
        if features['has_simple_damage']:
            score += params['dice_notation_bonus']
        if features['has_simple_range']:
            score += params['simple_range_bonus']
        if features['has_simple_duration']:
            score += params['simple_duration_bonus']
        
        # Bonus for exceptional brevity
        if features['word_count'] <= params['brevity_bonus_threshold']:
            score += params['brevity_bonus']
        
        # Bonus for high readability
        if features['flesch_score'] > 60:  # Easy to read
            score += params['clarity_bonus']
        
        # Clamp to 0-10 range
        score = max(0.0, min(10.0, score))
        
        return round(score, 1)
    
    def generate_feedback(self, move):
        """Generate detailed feedback for a move's simplicity"""
        features = self.extract_features(move)
        score = self.calculate_score(move)
        
        # Rating categories
        if score >= 8.5:
            rating = "Excellent Simplicity"
        elif score >= 7.0:
            rating = "Good Simplicity"
        elif score >= 5.5:
            rating = "Acceptable"
        elif score >= 4.0:
            rating = "Somewhat Complex"
        else:
            rating = "Too Complex"
        
        strengths = []
        warnings = []
        recommendations = []
        
        # Analyze features
        if features['word_count'] <= 12:
            strengths.append("Concise description")
        elif features['word_count'] > 25:
            warnings.append(f"Long description ({features['word_count']} words)")
            recommendations.append("Simplify wording - aim for 10-15 words")
        
        if features['sentence_count'] == 1:
            strengths.append("Single clear sentence")
        elif features['sentence_count'] > 2:
            warnings.append(f"Multiple sentences ({features['sentence_count']})")
            recommendations.append("Combine into one sentence if possible")
        
        if features['complex_word_ratio'] < 0.2:
            strengths.append("Simple vocabulary")
        elif features['complex_word_ratio'] > 0.4:
            warnings.append("Many complex words")
            recommendations.append("Use simpler, shorter words")
        
        if features['jargon_count'] == 0:
            strengths.append("No technical jargon")
        elif features['jargon_count'] > 2:
            warnings.append(f"Technical jargon used ({features['jargon_count']} terms)")
            recommendations.append("Replace jargon with plain language")
        
        if features['clause_count'] <= 2:
            strengths.append("Simple sentence structure")
        elif features['clause_count'] > 4:
            warnings.append("Complex sentence structure")
            recommendations.append("Break down into simpler clauses")
        
        if features['has_simple_damage']:
            strengths.append("Clear damage notation")
        
        if features['has_simple_range']:
            strengths.append("Standard range format")
        
        if features['has_simple_duration']:
            strengths.append("Standard duration format")
        
        if features['flesch_score'] > 70:
            strengths.append("Very easy to read")
        elif features['flesch_score'] < 50:
            warnings.append("Difficult to read")
            recommendations.append("Simplify sentence structure and word choice")
        
        return {
            'score': score,
            'rating': rating,
            'features': features,
            'strengths': strengths,
            'warnings': warnings,
            'recommendations': recommendations
        }

# Singleton instance
_scorer = None

def get_scorer():
    """Get or create simplicity scorer instance"""
    global _scorer
    if _scorer is None:
        _scorer = SimplicityScorer()
    return _scorer
