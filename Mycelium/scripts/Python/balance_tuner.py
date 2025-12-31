"""
Hyperparameter Tuning for Balance Scoring
Automatically calibrates scoring parameters to achieve normal distribution around 5/10
"""

import numpy as np
from pathlib import Path
import json
from scipy import stats
from scipy.optimize import differential_evolution, minimize
import matplotlib.pyplot as plt
from balance_scorer import BalanceScorer, get_scorer


class BalanceTuner:
    """Tune balance scoring parameters for normal distribution around target score."""
    
    def __init__(self, target_mean=5.0, target_std=1.5):
        """
        Initialize tuner.
        
        Args:
            target_mean: Desired mean score (default: 5.0)
            target_std: Desired standard deviation (default: 1.5)
        """
        self.target_mean = target_mean
        self.target_std = target_std
        
        # Tunable parameters for rule-based scoring
        self.params = {
            # Damage scaling
            'damage_weight': 0.4,              # Weight of damage in total score
            'damage_underpowered_threshold': 0.6,  # Ratio below expected
            'damage_underpowered_penalty': 2.0,
            'damage_slightly_under_threshold': 0.8,
            'damage_slightly_under_penalty': 1.0,
            'damage_overpowered_threshold': 1.5,
            'damage_overpowered_bonus': 3.0,
            'damage_slightly_over_threshold': 1.2,
            'damage_slightly_over_bonus': 1.5,
            
            # Cost efficiency
            'efficiency_weight': 0.3,          # Weight of efficiency
            'efficiency_poor_threshold': 3.0,
            'efficiency_poor_penalty': 1.5,
            'efficiency_below_avg_threshold': 5.0,
            'efficiency_below_avg_penalty': 0.5,
            'efficiency_high_threshold': 12.0,
            'efficiency_high_bonus': 2.5,
            'efficiency_good_threshold': 8.0,
            'efficiency_good_bonus': 1.0,
            
            # Utility
            'utility_weight': 0.2,             # Weight of utility
            'utility_high_threshold': 3,
            'utility_high_bonus': 1.5,
            'utility_medium_threshold': 2,
            'utility_medium_bonus': 0.8,
            'utility_none_penalty': 2.0,
            
            # Action economy
            'action_weight': 0.1,
            'bonus_action_bonus': 0.8,
            'reaction_bonus': 0.5,
            
            # Range/AoE
            'aoe_bonus': 1.0,
            'long_range_threshold': 60,
            'long_range_bonus': 0.5,
            'melee_penalty': 0.5,
            'melee_threshold': 5,
            
            # Duration penalty
            'duration_penalty': 0.3,
            
            # Base score
            'base_score': 5.0
        }
        
        self.best_params = None
        self.tuning_history = []
        
    def calculate_score_with_params(self, features, params):
        """Calculate balance score using given parameters."""
        score = params['base_score']
        
        # Expected damage by level
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
        
        # 3. Utility
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
        
        # 5. Range/AoE
        if features['is_aoe'] > 0:
            score += params['aoe_bonus']
        if features['range_feet'] > params['long_range_threshold']:
            score += params['long_range_bonus']
        elif features['range_feet'] <= params['melee_threshold']:
            score -= params['melee_penalty']
        
        # 6. Duration
        if features['has_duration'] > 0:
            score -= params['duration_penalty']
        
        return float(np.clip(score, 0.0, 10.0))
    
    def score_all_moves(self, moves, params):
        """Score all moves with given parameters."""
        scorer = BalanceScorer()
        scores = []
        
        for move in moves:
            features = scorer.extract_features(move)
            score = self.calculate_score_with_params(features, params)
            scores.append(score)
        
        return np.array(scores)
    
    def calculate_loss(self, param_values, param_names, moves):
        """
        Calculate loss function for optimization.
        
        Lower loss = better fit to target normal distribution.
        """
        # Convert flat array to parameter dict
        params = self.params.copy()
        for i, name in enumerate(param_names):
            params[name] = param_values[i]
        
        # Score all moves
        scores = self.score_all_moves(moves, params)
        
        # Calculate statistics
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        
        # Loss components
        mean_loss = (mean_score - self.target_mean) ** 2
        std_loss = (std_score - self.target_std) ** 2
        
        # Penalize extreme scores (too many 0s or 10s)
        extreme_count = np.sum((scores <= 0.5) | (scores >= 9.5))
        extreme_penalty = (extreme_count / len(scores)) ** 2
        
        # Check for normality using Shapiro-Wilk test
        if len(scores) >= 3:
            try:
                _, p_value = stats.shapiro(scores)
                normality_loss = (1 - p_value) ** 2  # Lower p-value = less normal
            except:
                normality_loss = 0.5
        else:
            normality_loss = 0.5
        
        # Combined loss
        total_loss = (
            mean_loss * 10.0 +           # Heavily weight hitting target mean
            std_loss * 5.0 +              # Weight target std
            extreme_penalty * 20.0 +      # Penalize extremes
            normality_loss * 2.0          # Encourage normal distribution
        )
        
        return total_loss
    
    def tune(self, moves, method='differential_evolution', max_iterations=100):
        """
        Tune parameters to achieve target distribution.
        
        Args:
            moves: List of move dictionaries
            method: 'differential_evolution' or 'nelder_mead'
            max_iterations: Maximum optimization iterations
        
        Returns:
            dict: Tuned parameters
        """
        print(f"\n{'='*70}")
        print(f"Starting Hyperparameter Tuning")
        print(f"{'='*70}")
        print(f"Target Mean: {self.target_mean:.2f}")
        print(f"Target Std Dev: {self.target_std:.2f}")
        print(f"Number of Moves: {len(moves)}")
        print(f"Optimization Method: {method}")
        
        # Select parameters to tune (exclude weights which need to sum to 1)
        tunable_params = [
            'damage_underpowered_threshold',
            'damage_underpowered_penalty',
            'damage_slightly_under_threshold',
            'damage_slightly_under_penalty',
            'damage_overpowered_threshold',
            'damage_overpowered_bonus',
            'damage_slightly_over_threshold',
            'damage_slightly_over_bonus',
            'efficiency_poor_threshold',
            'efficiency_poor_penalty',
            'efficiency_below_avg_threshold',
            'efficiency_below_avg_penalty',
            'efficiency_high_threshold',
            'efficiency_high_bonus',
            'efficiency_good_threshold',
            'efficiency_good_bonus',
            'utility_high_threshold',
            'utility_high_bonus',
            'utility_medium_threshold',
            'utility_medium_bonus',
            'utility_none_penalty',
            'bonus_action_bonus',
            'reaction_bonus',
            'aoe_bonus',
            'long_range_threshold',
            'long_range_bonus',
            'melee_penalty',
            'duration_penalty',
            'base_score'
        ]
        
        # Define bounds for each parameter
        bounds = [
            (0.3, 0.9),   # damage_underpowered_threshold
            (0.5, 4.0),   # damage_underpowered_penalty
            (0.5, 1.0),   # damage_slightly_under_threshold
            (0.2, 2.0),   # damage_slightly_under_penalty
            (1.2, 2.0),   # damage_overpowered_threshold
            (1.0, 5.0),   # damage_overpowered_bonus
            (1.0, 1.5),   # damage_slightly_over_threshold
            (0.5, 3.0),   # damage_slightly_over_bonus
            (1.0, 5.0),   # efficiency_poor_threshold
            (0.5, 3.0),   # efficiency_poor_penalty
            (3.0, 8.0),   # efficiency_below_avg_threshold
            (0.1, 1.5),   # efficiency_below_avg_penalty
            (8.0, 20.0),  # efficiency_high_threshold
            (1.0, 4.0),   # efficiency_high_bonus
            (5.0, 12.0),  # efficiency_good_threshold
            (0.3, 2.0),   # efficiency_good_bonus
            (2, 4),       # utility_high_threshold
            (0.5, 3.0),   # utility_high_bonus
            (1, 3),       # utility_medium_threshold
            (0.2, 1.5),   # utility_medium_bonus
            (0.5, 4.0),   # utility_none_penalty
            (0.3, 2.0),   # bonus_action_bonus
            (0.2, 1.5),   # reaction_bonus
            (0.3, 2.5),   # aoe_bonus
            (30, 90),     # long_range_threshold
            (0.2, 1.5),   # long_range_bonus
            (0.2, 1.5),   # melee_penalty
            (0.1, 1.0),   # duration_penalty
            (3.0, 7.0)    # base_score
        ]
        
        # Initial parameter values
        x0 = [self.params[name] for name in tunable_params]
        
        print(f"\nOptimizing {len(tunable_params)} parameters...")
        print("This may take a few minutes...\n")
        
        # Optimize
        if method == 'differential_evolution':
            result = differential_evolution(
                lambda x: self.calculate_loss(x, tunable_params, moves),
                bounds,
                maxiter=max_iterations,
                popsize=15,
                tol=0.01,
                atol=0.001,
                workers=1,
                updating='deferred',
                polish=True,
                callback=self._optimization_callback
            )
        else:  # nelder_mead
            result = minimize(
                lambda x: self.calculate_loss(x, tunable_params, moves),
                x0,
                method='Nelder-Mead',
                options={'maxiter': max_iterations, 'disp': True}
            )
        
        # Update parameters with optimized values
        self.best_params = self.params.copy()
        for i, name in enumerate(tunable_params):
            self.best_params[name] = result.x[i]
        
        # Calculate final statistics
        final_scores = self.score_all_moves(moves, self.best_params)
        final_mean = np.mean(final_scores)
        final_std = np.std(final_scores)
        
        print(f"\n{'='*70}")
        print(f"Optimization Complete!")
        print(f"{'='*70}")
        print(f"Final Mean: {final_mean:.2f} (target: {self.target_mean:.2f})")
        print(f"Final Std Dev: {final_std:.2f} (target: {self.target_std:.2f})")
        print(f"Loss: {result.fun:.4f}")
        print(f"Success: {result.success}")
        
        # Distribution statistics
        print(f"\nScore Distribution:")
        print(f"  Min: {np.min(final_scores):.2f}")
        print(f"  25th percentile: {np.percentile(final_scores, 25):.2f}")
        print(f"  Median: {np.median(final_scores):.2f}")
        print(f"  75th percentile: {np.percentile(final_scores, 75):.2f}")
        print(f"  Max: {np.max(final_scores):.2f}")
        
        # Count in each category
        severely_under = np.sum(final_scores <= 3.5)
        under = np.sum((final_scores > 3.5) & (final_scores <= 4.5))
        slightly_under = np.sum((final_scores > 4.5) & (final_scores <= 5.5))
        balanced = np.sum((final_scores > 5.5) & (final_scores <= 7.0))
        slightly_over = np.sum((final_scores > 7.0) & (final_scores <= 8.0))
        over = np.sum((final_scores > 8.0) & (final_scores <= 9.0))
        severely_over = np.sum(final_scores > 9.0)
        
        print(f"\nCategory Distribution:")
        print(f"  Severely Underpowered (≤3.5): {severely_under} ({severely_under/len(final_scores)*100:.1f}%)")
        print(f"  Underpowered (3.5-4.5): {under} ({under/len(final_scores)*100:.1f}%)")
        print(f"  Slightly Below Avg (4.5-5.5): {slightly_under} ({slightly_under/len(final_scores)*100:.1f}%)")
        print(f"  Well Balanced (5.5-7.0): {balanced} ({balanced/len(final_scores)*100:.1f}%)")
        print(f"  Slightly Above Avg (7.0-8.0): {slightly_over} ({slightly_over/len(final_scores)*100:.1f}%)")
        print(f"  Overpowered (8.0-9.0): {over} ({over/len(final_scores)*100:.1f}%)")
        print(f"  Severely Overpowered (>9.0): {severely_over} ({severely_over/len(final_scores)*100:.1f}%)")
        
        return self.best_params
    
    def _optimization_callback(self, xk, convergence):
        """Callback for differential evolution progress."""
        iteration = len(self.tuning_history)
        if iteration % 10 == 0:
            print(f"  Iteration {iteration}: convergence = {convergence:.6f}")
        self.tuning_history.append(convergence)
        return False  # Don't stop
    
    def save_parameters(self, filepath):
        """Save tuned parameters to JSON file."""
        if self.best_params is None:
            raise ValueError("No tuned parameters available. Run tune() first.")
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(self.best_params, f, indent=2)
        
        print(f"\n✅ Parameters saved to: {filepath}")
    
    def load_parameters(self, filepath):
        """Load parameters from JSON file."""
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Parameter file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            self.best_params = json.load(f)
        
        self.params = self.best_params.copy()
        print(f"✅ Parameters loaded from: {filepath}")
    
    def plot_distribution(self, moves, save_path=None):
        """Plot score distribution before and after tuning."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not available for plotting")
            return
        
        # Original scores
        original_scores = self.score_all_moves(moves, self.params)
        
        # Tuned scores
        if self.best_params:
            tuned_scores = self.score_all_moves(moves, self.best_params)
        else:
            tuned_scores = original_scores
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Original distribution
        axes[0].hist(original_scores, bins=20, edgecolor='black', alpha=0.7)
        axes[0].axvline(np.mean(original_scores), color='red', linestyle='--', 
                       label=f'Mean: {np.mean(original_scores):.2f}')
        axes[0].axvline(self.target_mean, color='green', linestyle='--',
                       label=f'Target: {self.target_mean:.2f}')
        axes[0].set_xlabel('Balance Score')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Original Distribution')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Tuned distribution
        axes[1].hist(tuned_scores, bins=20, edgecolor='black', alpha=0.7, color='orange')
        axes[1].axvline(np.mean(tuned_scores), color='red', linestyle='--',
                       label=f'Mean: {np.mean(tuned_scores):.2f}')
        axes[1].axvline(self.target_mean, color='green', linestyle='--',
                       label=f'Target: {self.target_mean:.2f}')
        axes[1].set_xlabel('Balance Score')
        axes[1].set_ylabel('Frequency')
        axes[1].set_title('Tuned Distribution')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✅ Plot saved to: {save_path}")
        else:
            plt.show()


def load_all_moves_from_repo(repo_root):
    """Load all bending moves from the repository."""
    repo_root = Path(repo_root)
    player_root = repo_root / 'Player Root'
    
    if not player_root.exists():
        player_root = repo_root
    
    bending_rules = player_root / 'Rules' / 'Bending Rules'
    
    if not bending_rules.exists():
        raise FileNotFoundError(f"Bending Rules directory not found: {bending_rules}")
    
    moves = []
    elements = ['Air', 'Water', 'Earth', 'Fire', 'Spirit']
    
    for element in elements:
        element_path = bending_rules / element / f'{element}bending Moves'
        
        if not element_path.exists():
            continue
        
        for level in range(1, 6):
            level_path = element_path / f'Level {level}'
            
            if not level_path.exists():
                continue
            
            for move_file in level_path.glob('*.md'):
                try:
                    content = move_file.read_text(encoding='utf-8')
                    move = parse_move_for_tuning(content, move_file.stem, level, element.lower())
                    moves.append(move)
                except Exception as e:
                    print(f"Warning: Could not parse {move_file}: {e}")
    
    return moves


def parse_move_for_tuning(content, name, level, element):
    """Parse move file for tuning purposes."""
    import re
    
    move = {
        'name': name,
        'level': level,
        'element': element,
        'actionType': 'Action',
        'range': None,
        'damage': None,
        'cost': None,
        'effects': None,
        'description': None
    }
    
    # Extract action type
    action_tags = ['#Action', '#Bonus_Action', '#Reaction', '#Danger_Sense_Reaction']
    for tag in action_tags:
        if tag in content:
            if 'Danger_Sense' in tag:
                move['actionType'] = 'Danger Sense Reaction'
            elif 'Bonus' in tag:
                move['actionType'] = 'Bonus Action'
            elif 'Reaction' in tag:
                move['actionType'] = 'Reaction'
            else:
                move['actionType'] = 'Action'
            break
    
    # Extract range
    range_match = re.search(r'\*\*Range:?\*\*\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
    if range_match:
        move['range'] = range_match.group(1).strip()
    
    # Extract damage
    damage_match = re.search(r'\*\*Damage:?\*\*\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
    if damage_match:
        move['damage'] = damage_match.group(1).strip()
    elif re.search(r'\d+d\d+', content):
        # Find dice notation in content
        dice_match = re.search(r'(\d+d\d+(?:\s*\+\s*\d+)?)', content)
        if dice_match:
            move['damage'] = dice_match.group(1)
    
    # Extract cost
    cost_match = re.search(r'\*\*Cost:?\*\*\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
    if cost_match:
        move['cost'] = cost_match.group(1).strip()
    
    # Extract effects/description
    effects_match = re.search(r'\*\*Effect:?s?\*\*\s*(.+?)(?:\n\n|\Z)', content, re.IGNORECASE | re.DOTALL)
    if effects_match:
        move['effects'] = effects_match.group(1).strip()
    else:
        # Use everything after the metadata as description
        lines = content.split('\n')
        description_lines = []
        for line in lines:
            if not line.startswith('#') and not line.startswith('**') and line.strip():
                description_lines.append(line.strip())
        move['description'] = ' '.join(description_lines)
    
    return move


if __name__ == '__main__':
    import sys
    
    # Get repo root
    repo_root = Path(__file__).resolve().parents[3]
    
    print("Loading all bending moves from repository...")
    moves = load_all_moves_from_repo(repo_root)
    print(f"Loaded {len(moves)} moves")
    
    if len(moves) < 10:
        print("Not enough moves found for tuning!")
        sys.exit(1)
    
    # Create tuner
    tuner = BalanceTuner(target_mean=5.0, target_std=1.5)
    
    # Tune parameters
    tuned_params = tuner.tune(moves, method='differential_evolution', max_iterations=50)
    
    # Save parameters
    param_file = repo_root / 'Mycelium' / 'scripts' / 'Python' / 'tuned_balance_params.json'
    tuner.save_parameters(param_file)
    
    # Try to plot
    try:
        plot_file = repo_root / 'logs' / 'balance_distribution.png'
        tuner.plot_distribution(moves, save_path=plot_file)
    except Exception as e:
        print(f"Could not create plot: {e}")
    
    print("\n✅ Tuning complete! Restart the backend to use new parameters.")
