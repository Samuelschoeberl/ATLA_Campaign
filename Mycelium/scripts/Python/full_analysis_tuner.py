"""
Hyperparameter Tuning for Full Analysis Scorer
Optimizes weights and parameters to achieve balanced distribution
"""

import json
import numpy as np
from pathlib import Path
from scipy.optimize import differential_evolution
from scipy.stats import normaltest
import matplotlib.pyplot as plt

# Import the scorers
import sys
sys.path.insert(0, str(Path(__file__).parent))
from balance_scorer import get_scorer as get_balance_scorer
from simplicity_scorer import get_scorer as get_simplicity_scorer

class FullAnalysisTuner:
    """Tunes full analysis scorer parameters for optimal distribution"""
    
    def __init__(self):
        """Initialize scorer instances and storage for loaded moves."""
        self.moves_data = []
        self.balance_scorer = get_balance_scorer()
        self.simplicity_scorer = get_simplicity_scorer()
        
    def load_moves(self):
        """Load all moves from the game files"""
        from frontend_api import get_player_root_base, parse_move_content
        
        player_root = get_player_root_base()
        elements = ['air', 'water', 'earth', 'fire']
        levels = [1, 2, 3, 4, 5]
        
        moves = []
        for element in elements:
            element_path = player_root / 'Rules' / 'Bending Rules' / element.capitalize() / f'{element.capitalize()}bending Moves'
            
            if not element_path.exists():
                continue
            
            for level in levels:
                level_path = element_path / f'Level {level}'
                if not level_path.exists():
                    continue
                
                for move_file in level_path.glob('*.md'):
                    try:
                        content = move_file.read_text(encoding='utf-8')
                        move_info = parse_move_content(content, move_file.stem, level, element)
                        moves.append(move_info)
                    except Exception as e:
                        print(f"Error loading {move_file}: {e}")
        
        print(f"Loaded {len(moves)} moves for tuning")
        return moves
    
    def calculate_move_scores(self, moves):
        """Calculate all three component scores for each move"""
        scored_moves = []
        errors = []
        
        for move in moves:
            try:
                # Ensure move has required fields with defaults
                if not move.get('name'):
                    continue
                
                move.setdefault('effects', '')
                move.setdefault('description', '')
                move.setdefault('range', '')
                move.setdefault('duration', '')
                move.setdefault('damage', '')
                move.setdefault('actionType', 'Action')
                
                # Balance score
                balance_result = self.balance_scorer.score_move(move)
                balance_score = balance_result['score']
                
                # Simplicity score
                simplicity_score = self.simplicity_scorer.calculate_score(move)
                
                # Uniqueness score (simple heuristic)
                uniqueness_score = self._calculate_uniqueness(move)
                
                scored_moves.append({
                    'name': move['name'],
                    'balance': balance_score,
                    'uniqueness': uniqueness_score,
                    'simplicity': simplicity_score
                })
            except Exception as e:
                errors.append(f"{move.get('name', 'Unknown')}: {str(e)}")
        
        if errors and len(errors) < 20:  # Only show first 20 errors
            print(f"Errors encountered ({len(errors)} moves):")
            for error in errors[:10]:
                print(f"  - {error}")
        
        return scored_moves
    
    def _calculate_uniqueness(self, move):
        """Simple uniqueness calculation"""
        score = 5.0
        
        # Action type variety
        action_type = move.get('actionType', '')
        if action_type in ['Reaction', 'Danger Sense Reaction']:
            score += 1.0
        
        # Range creativity
        range_str = move.get('range', '') or ''
        if 'radius' in range_str.lower():
            score += 1.0
        elif 'cone' in range_str.lower():
            score += 1.5
        elif 'self' in range_str.lower():
            score += 0.5
        
        # Effect complexity
        effects_str = (move.get('effects', '') or '') + (move.get('description', '') or '')
        effects = effects_str.lower()
        if 'concentration' in effects:
            score += 1.5
        if 'lingering' in effects:
            score += 2.0
        if any(word in effects for word in ['prone', 'dazed', 'disadvantage']):
            score += 1.0
        if any(word in effects for word in ['pull', 'push', 'knock']):
            score += 0.5
        if any(word in effects for word in ['wall', 'terrain', 'environmental']):
            score += 1.5
        if 'temporary' in effects and 'slot' in effects:
            score += 1.5
        
        return min(10.0, score)
    
    def calculate_full_scores(self, scored_moves, params):
        """Calculate full analysis scores using given parameters"""
        full_scores = []
        
        balance_weight = params[0]
        uniqueness_weight = params[1]
        simplicity_weight = params[2]
        balance_target = params[3]
        uniqueness_target = params[4]
        simplicity_target = params[5]
        balance_deviation_penalty = params[6]
        synergy_bonus = params[7]
        consistency_bonus = params[8]
        low_score_penalty = params[9]
        
        for move in scored_moves:
            balance = move['balance']
            uniqueness = move['uniqueness']
            simplicity = move['simplicity']
            
            # Base weighted average
            score = (
                balance * balance_weight +
                uniqueness * uniqueness_weight +
                simplicity * simplicity_weight
            )
            
            # Penalty for balance deviation from target
            balance_deviation = abs(balance - balance_target)
            if balance_deviation > 2.0:
                score -= (balance_deviation - 2.0) * balance_deviation_penalty
            
            # Synergy bonus: all scores are good
            if all(s >= 6.5 for s in [balance, uniqueness, simplicity]):
                score += synergy_bonus
            
            # Consistency bonus: scores are similar
            score_range = max([balance, uniqueness, simplicity]) - min([balance, uniqueness, simplicity])
            if score_range <= 2.0:
                score += consistency_bonus
            
            # Penalty for critically low scores
            if any(s < 3.5 for s in [balance, uniqueness, simplicity]):
                min_score = min([balance, uniqueness, simplicity])
                score -= (3.5 - min_score) * low_score_penalty
            
            # Clamp to 0-10
            score = max(0.0, min(10.0, score))
            full_scores.append(score)
        
        return np.array(full_scores)
    
    def calculate_loss(self, params):
        """Loss function for optimization"""
        scores = self.calculate_full_scores(self.moves_data, params)
        
        # Target distribution: mean around 6.5, std around 1.5
        target_mean = 6.5
        target_std = 1.5
        
        mean = np.mean(scores)
        std = np.std(scores)
        
        # Mean deviation loss (heavily weighted)
        mean_loss = abs(mean - target_mean) * 10.0
        
        # Std deviation loss
        std_loss = abs(std - target_std) * 5.0
        
        # Distribution across categories
        excellent = np.sum(scores >= 8.0)
        good = np.sum((scores >= 6.0) & (scores < 8.0))
        needs_work = np.sum(scores < 6.0)
        total = len(scores)
        
        # Target: ~30% excellent, ~40% good, ~30% needs work
        target_excellent = total * 0.30
        target_good = total * 0.40
        target_needs_work = total * 0.30
        
        category_loss = (
            abs(excellent - target_excellent) +
            abs(good - target_good) +
            abs(needs_work - target_needs_work)
        ) * 0.5
        
        # Penalty for extreme scores (too many 0s or 10s)
        extreme_penalty = (np.sum(scores <= 1.0) + np.sum(scores >= 9.5)) * 2.0
        
        # Normality test (we want somewhat normal distribution)
        try:
            _, p_value = normaltest(scores)
            normality_loss = max(0, 0.1 - p_value) * 20.0  # Penalize if too far from normal
        except:
            normality_loss = 0.0
        
        total_loss = mean_loss + std_loss + category_loss + extreme_penalty + normality_loss
        
        return total_loss
    
    def tune(self):
        """Run hyperparameter optimization"""
        print("Starting hyperparameter tuning for Full Analysis Scorer...")
        print("=" * 60)
        
        # Load and score all moves
        moves = self.load_moves()
        self.moves_data = self.calculate_move_scores(moves)
        
        if not self.moves_data:
            print("ERROR: No moves could be scored successfully!")
            return None
        
        print(f"\nSuccessfully scored {len(self.moves_data)} moves")
        print("\nComponent score ranges:")
        balances = [m['balance'] for m in self.moves_data]
        uniquenesses = [m['uniqueness'] for m in self.moves_data]
        simplicities = [m['simplicity'] for m in self.moves_data]
        
        print(f"  Balance: {min(balances):.1f} - {max(balances):.1f} (avg: {np.mean(balances):.1f})")
        print(f"  Uniqueness: {min(uniquenesses):.1f} - {max(uniquenesses):.1f} (avg: {np.mean(uniquenesses):.1f})")
        print(f"  Simplicity: {min(simplicities):.1f} - {max(simplicities):.1f} (avg: {np.mean(simplicities):.1f})")
        
        # Parameter bounds: [balance_weight, uniqueness_weight, simplicity_weight, 
        #                    balance_target, uniqueness_target, simplicity_target,
        #                    balance_deviation_penalty, synergy_bonus, consistency_bonus, low_score_penalty]
        bounds = [
            (0.25, 0.50),  # balance_weight
            (0.25, 0.45),  # uniqueness_weight
            (0.15, 0.35),  # simplicity_weight
            (4.5, 5.5),    # balance_target
            (6.0, 7.5),    # uniqueness_target
            (6.0, 7.5),    # simplicity_target
            (0.2, 1.0),    # balance_deviation_penalty
            (0.0, 1.0),    # synergy_bonus
            (0.0, 0.5),    # consistency_bonus
            (0.2, 1.0)     # low_score_penalty
        ]
        
        print("\nOptimizing parameters...")
        print("Target: mean=6.5, std=1.5, 30% excellent, 40% good, 30% needs work")
        
        # Run differential evolution
        result = differential_evolution(
            self.calculate_loss,
            bounds,
            maxiter=100,
            popsize=20,
            workers=1,
            updating='deferred',
            disp=True
        )
        
        # Extract optimal parameters
        optimal_params = result.x
        
        # Normalize weights to sum to 1.0
        weight_sum = optimal_params[0] + optimal_params[1] + optimal_params[2]
        optimal_params[0] /= weight_sum
        optimal_params[1] /= weight_sum
        optimal_params[2] /= weight_sum
        
        # Calculate final distribution
        final_scores = self.calculate_full_scores(self.moves_data, optimal_params)
        
        print("\n" + "=" * 60)
        print("OPTIMIZATION COMPLETE")
        print("=" * 60)
        print(f"\nFinal Distribution:")
        print(f"  Mean: {np.mean(final_scores):.2f} (target: 6.50)")
        print(f"  Std Dev: {np.std(final_scores):.2f} (target: 1.50)")
        print(f"  Min: {np.min(final_scores):.2f}")
        print(f"  Max: {np.max(final_scores):.2f}")
        
        excellent = np.sum(final_scores >= 8.0)
        good = np.sum((final_scores >= 6.0) & (final_scores < 8.0))
        needs_work = np.sum(final_scores < 6.0)
        total = len(final_scores)
        
        print(f"\nCategory Distribution:")
        print(f"  Excellent (≥8.0): {excellent} ({excellent/total*100:.1f}%)")
        print(f"  Good (6.0-8.0): {good} ({good/total*100:.1f}%)")
        print(f"  Needs Work (<6.0): {needs_work} ({needs_work/total*100:.1f}%)")
        
        print(f"\nOptimal Parameters:")
        print(f"  Balance Weight: {optimal_params[0]:.3f}")
        print(f"  Uniqueness Weight: {optimal_params[1]:.3f}")
        print(f"  Simplicity Weight: {optimal_params[2]:.3f}")
        print(f"  Balance Target: {optimal_params[3]:.2f}")
        print(f"  Uniqueness Target: {optimal_params[4]:.2f}")
        print(f"  Simplicity Target: {optimal_params[5]:.2f}")
        print(f"  Balance Deviation Penalty: {optimal_params[6]:.3f}")
        print(f"  Synergy Bonus: {optimal_params[7]:.3f}")
        print(f"  Consistency Bonus: {optimal_params[8]:.3f}")
        print(f"  Low Score Penalty: {optimal_params[9]:.3f}")
        
        # Save parameters
        params_dict = {
            'balance_weight': float(optimal_params[0]),
            'uniqueness_weight': float(optimal_params[1]),
            'simplicity_weight': float(optimal_params[2]),
            'balance_target': float(optimal_params[3]),
            'uniqueness_target': float(optimal_params[4]),
            'simplicity_target': float(optimal_params[5]),
            'balance_deviation_penalty': float(optimal_params[6]),
            'synergy_bonus': float(optimal_params[7]),
            'consistency_bonus': float(optimal_params[8]),
            'low_score_penalty': float(optimal_params[9])
        }
        
        output_path = Path(__file__).parent / 'tuned_full_analysis_params.json'
        with open(output_path, 'w') as f:
            json.dump(params_dict, f, indent=2)
        
        print(f"\n✓ Parameters saved to: {output_path}")
        
        # Plot distribution
        self.plot_distribution(final_scores, optimal_params)
        
        return params_dict
    
    def plot_distribution(self, scores, params):
        """Plot score distribution"""
        plt.figure(figsize=(12, 6))
        
        # Histogram
        plt.subplot(1, 2, 1)
        plt.hist(scores, bins=20, range=(0, 10), color='#4ec9b0', alpha=0.7, edgecolor='black')
        plt.axvline(np.mean(scores), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(scores):.2f}')
        plt.axvline(6.5, color='blue', linestyle=':', linewidth=2, label='Target: 6.50')
        plt.xlabel('Overall Score')
        plt.ylabel('Number of Moves')
        plt.title('Full Analysis Score Distribution')
        plt.legend()
        plt.grid(axis='y', alpha=0.3)
        
        # Category pie chart
        plt.subplot(1, 2, 2)
        excellent = np.sum(scores >= 8.0)
        good = np.sum((scores >= 6.0) & (scores < 8.0))
        needs_work = np.sum(scores < 6.0)
        
        sizes = [excellent, good, needs_work]
        labels = [f'Excellent (≥8)\n{excellent} moves', f'Good (6-8)\n{good} moves', f'Needs Work (<6)\n{needs_work} moves']
        colors = ['#2ecc71', '#f39c12', '#e74c3c']
        
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        plt.title('Category Distribution')
        
        plt.tight_layout()
        
        output_path = Path(__file__).parent.parent.parent.parent / 'logs' / 'full_analysis_distribution.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✓ Distribution plot saved to: {output_path}")
        plt.close()

if __name__ == '__main__':
    tuner = FullAnalysisTuner()
    tuner.tune()
