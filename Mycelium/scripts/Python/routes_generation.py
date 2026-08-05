"""Generation/analysis routes: Wikigraphs generation, move-balance analysis,
and balance-score visualization data. These are all CPU-heavier, less
frequent, deliberate GM actions rather than per-turn hot paths, so a single
lock serializing each is an acceptable and simple concurrency fix at this
scale (vs. the per-path RLock used for the hot-contention fields).
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import quote

from flask import request, jsonify, current_app

import events
import resource_cache
from frontend_api import bp
from sheet_helpers import REPO_ROOT, PLAYER_ROOT_PREFIX, get_player_root_base, WIKIGRAPHS_LOG

try:
    from balance_scorer import get_scorer
    BALANCE_SCORER_AVAILABLE = True
except (ImportError, Exception) as e:
    print(f"Balance scorer not available: {e}")
    BALANCE_SCORER_AVAILABLE = False

try:
    from simplicity_scorer import get_scorer as get_simplicity_scorer
    SIMPLICITY_SCORER_AVAILABLE = True
except (ImportError, Exception) as e:
    print(f"Simplicity scorer not available: {e}")
    SIMPLICITY_SCORER_AVAILABLE = False

try:
    from full_analysis_scorer import get_scorer as get_full_analysis_scorer
    FULL_ANALYSIS_SCORER_AVAILABLE = True
except (ImportError, Exception) as e:
    print(f"Full analysis scorer not available: {e}")
    FULL_ANALYSIS_SCORER_AVAILABLE = False

_graphs_generation_lock = threading.Lock()


@bp.route('/api/generate-graphs', methods=['POST'])
def generate_graphs():
    """Generate sunburst and treemap HTML files using Wikigraphs.py."""
    data = request.get_json() or {}
    folder = (data.get('folder') or data.get('folderPath') or '').strip()

    if folder.rstrip('/') == PLAYER_ROOT_PREFIX.rstrip('/'):
        rel_folder = ''
    elif folder.startswith(PLAYER_ROOT_PREFIX):
        rel_folder = folder[len(PLAYER_ROOT_PREFIX):].lstrip('/')
    else:
        rel_folder = folder.lstrip('/')

    player_base = get_player_root_base()
    if player_base == REPO_ROOT:
        target_dir = REPO_ROOT if not rel_folder else (REPO_ROOT / rel_folder)
    else:
        target_dir = player_base if not rel_folder else (player_base / rel_folder)

    try:
        target_dir = target_dir.resolve()
    except Exception:
        return jsonify(error='Invalid folder path'), 400

    target_path = target_dir

    try:
        repo_resolved = REPO_ROOT.resolve()
        if repo_resolved not in target_dir.parents and target_dir != repo_resolved:
            return jsonify(error='Folder is outside repository'), 400
    except Exception:
        return jsonify(error='Path resolution error'), 400

    if not target_dir.exists() or not target_dir.is_dir():
        return jsonify(error='Folder does not exist'), 400

    script_module = None
    tried_import = []
    make_graphs_func = None
    try:
        import importlib
        tried_import.append('Mycelium.scripts.Python.Wikigraphs')
        script_module = importlib.import_module('Mycelium.scripts.Python.Wikigraphs')
    except Exception:
        script_module = None
    if script_module is None:
        try:
            tried_import.append('scripts.Python.Wikigraphs')
            script_module = importlib.import_module('scripts.Python.Wikigraphs')
        except Exception:
            script_module = None

    if script_module is not None:
        make_graphs_func = getattr(script_module, 'make_graphs', None)

    generated = []
    errors = []
    captured_stdout = ''
    captured_stderr = ''

    # Serialize the whole operation with a lock (rare, deliberate GM action,
    # not a hot path) and capture output via contextlib.redirect_stdout/stderr
    # into a request-scoped buffer instead of directly monkey-patching the
    # process-global sys.stdout/sys.stderr, which used to corrupt concurrent
    # callers' captured output under threaded=True.
    if callable(make_graphs_func):
        with _graphs_generation_lock:
            buf_out, buf_err = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
                    make_graphs_func(root=target_path, outdir=target_dir)
                captured_stdout = buf_out.getvalue() or ''
                captured_stderr = buf_err.getvalue() or ''
                if captured_stdout:
                    current_app.logger.info('[wikigraphs stdout]\n' + captured_stdout)
                if captured_stderr:
                    current_app.logger.warning('[wikigraphs stderr]\n' + captured_stderr)
                _persist_wikigraphs_log(captured_stdout, captured_stderr)
            except Exception as e:
                errors.append(str(e))
    else:
        try:
            script_path = REPO_ROOT.joinpath('Mycelium', 'scripts', 'Python', 'Wikigraphs.py')
            if not script_path.exists():
                script_path = REPO_ROOT.joinpath('Mycelium', 'scripts', 'manuals', 'Wikigraphs.py')
            if not script_path.exists():
                return jsonify(error='Wikigraphs.py not found to run'), 500
            arg_root = str(rel_folder) if rel_folder else '.'
            cmd = [sys.executable, str(script_path), '--root', arg_root, '--out', str(target_dir)]
            with _graphs_generation_lock:
                proc = subprocess.run(cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
            captured_stdout = proc.stdout or ''
            captured_stderr = proc.stderr or ''
            if captured_stdout:
                current_app.logger.info('[wikigraphs stdout]\n' + captured_stdout)
            if captured_stderr:
                current_app.logger.warning('[wikigraphs stderr]\n' + captured_stderr)
            _persist_wikigraphs_log(captured_stdout, captured_stderr)
            if proc.returncode != 0:
                errors.append(proc.stderr or proc.stdout or f'Exit {proc.returncode}')
        except subprocess.TimeoutExpired:
            errors.append('Wikigraphs run timed out after 300s')
        except Exception as e:
            errors.append(str(e))

    try:
        for p in target_dir.iterdir():
            if not p.is_file():
                continue
            if p.name.endswith('_wikigraph_sunburst.html') or p.name.endswith('_wikigraph_treemap.html') or p.name.endswith('_wikigraph.html'):
                try:
                    rel = p.relative_to(REPO_ROOT).as_posix()
                except Exception:
                    try:
                        rel = (player_base.relative_to(REPO_ROOT).as_posix().rstrip('/') + '/' + p.relative_to(player_base).as_posix()).lstrip('/')
                    except Exception:
                        rel = p.as_posix()
                parts = rel.split('/')
                quoted = '/'.join(quote(seg) for seg in parts if seg != '')
                generated.append('/' + quoted)
    except Exception:
        pass

    if errors and not generated:
        return jsonify(success=False, errors=errors, tried_import=tried_import, stdout=captured_stdout, stderr=captured_stderr), 500

    return jsonify(success=True, files=generated, errors=errors, tried_import=tried_import, stdout=captured_stdout, stderr=captured_stderr)


def _persist_wikigraphs_log(stdout: str, stderr: str) -> None:
    """Append log lines to the wikigraphs log file and publish them over SSE
    so /api/tail-wikigraphs subscribers (routes_events.py) see them live,
    instead of the old file-polling tail implementation."""
    try:
        with open(str(WIKIGRAPHS_LOG), 'a', encoding='utf-8') as lf:
            if stdout:
                for ln in stdout.splitlines():
                    if not ln.strip():
                        continue
                    lf.write(json.dumps({'severity': 'info', 'text': ln}) + '\n')
                    events.publish_log_line(ln, severity='info')
            if stderr:
                for ln in stderr.splitlines():
                    if not ln.strip():
                        continue
                    lf.write(json.dumps({'severity': 'error', 'text': ln}) + '\n')
                    events.publish_log_line(ln, severity='error')
    except Exception:
        pass


@bp.route('/api/wikigraphs', methods=['POST'])
def api_wikigraphs():
    """Run the repository's Wikigraphs script for a given folder under Player Root."""
    data = request.get_json() or {}
    root = data.get('root') or ''
    s = str(root or '').strip()
    prefix_no_slash = PLAYER_ROOT_PREFIX.rstrip('/')
    if s == prefix_no_slash:
        s = ''
    elif s.startswith(prefix_no_slash + '/'):
        s = s[len(prefix_no_slash) + 1:].lstrip('/')
    target_rel = s or ''

    try:
        player_base = get_player_root_base()
        target_path = (player_base / target_rel).resolve() if target_rel else player_base.resolve()
    except Exception as e:
        return jsonify({'error': f'Path resolution error: {e}'}), 400

    try:
        repo_res = REPO_ROOT.resolve()
        if repo_res not in target_path.parents and target_path != repo_res:
            return jsonify({'error': 'Target outside repository'}), 400
    except Exception:
        return jsonify({'error': 'Repository resolution error'}), 500

    if not target_path.exists() or not target_path.is_dir():
        return jsonify({'error': 'Target folder not found'}), 404

    script_path = REPO_ROOT.joinpath('Mycelium', 'scripts', 'Python', 'Wikigraphs.py')
    if not script_path.exists():
        script_path = REPO_ROOT.joinpath('Mycelium', 'scripts', 'manuals', 'Wikigraphs.py')
        if not script_path.exists():
            return jsonify({'error': 'Wikigraphs script not found on server'}), 500

    arg_root = str(target_rel) if target_rel else '.'
    cmd = [sys.executable, str(script_path), '--root', arg_root]
    try:
        with _graphs_generation_lock:
            proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300)
        out = proc.stdout or ''
        err = proc.stderr or ''
        status = proc.returncode
        _persist_wikigraphs_log(out, err)
        if status != 0:
            return jsonify({'success': False, 'code': status, 'stdout': out, 'stderr': err}), 500

        written = []
        try:
            repo_res = REPO_ROOT.resolve()
            candidates = list(repo_res.rglob('*_wikigraph_*.html'))
            for p in candidates:
                try:
                    rel = p.relative_to(repo_res).as_posix()
                except Exception:
                    continue
                rel_norm = rel
                if target_rel:
                    if target_rel.replace('\\', '/') not in rel_norm:
                        continue
                else:
                    player_base = get_player_root_base()
                    if player_base != REPO_ROOT:
                        if not (rel_norm.startswith('Player Root/') or 'Player Root' in rel_norm):
                            continue
                parts = rel.split('/')
                quoted = '/'.join(quote(p) for p in parts)
                written.append('/' + quoted)
        except Exception:
            written = []

        return jsonify({'success': True, 'code': status, 'stdout': out, 'stderr': err, 'written': written})
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Wikigraphs run timed out'}), 504
    except Exception as e:
        return jsonify({'error': f'Failed to run Wikigraphs: {e}'}), 500


def parse_move_content(content: str, name: str, level: int, element: str):
    """Parse a move markdown file and extract key information."""
    move_info = {
        'name': name, 'level': level, 'element': element, 'actionType': 'Unknown',
        'range': None, 'damage': None, 'effects': None, 'description': None,
        'duration': None, 'cost': None
    }

    action_tags = ['#Action', '#Bonus_Action', '#Bonus_action', '#Reaction', '#Danger_Sense_Reaction']
    for tag in action_tags:
        if tag in content:
            if 'Danger_Sense' in tag:
                move_info['actionType'] = 'Danger Sense Reaction'
            elif 'Bonus' in tag:
                move_info['actionType'] = 'Bonus Action'
            elif 'Reaction' in tag:
                move_info['actionType'] = 'Reaction'
            elif 'Action' in tag:
                move_info['actionType'] = 'Action'
            break

    range_match = re.search(r'\*\*Range:?\*\*\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
    if range_match:
        move_info['range'] = range_match.group(1).strip()
    else:
        range_match = re.search(r'-\s*Range:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if range_match:
            move_info['range'] = range_match.group(1).strip()
        radius_match = re.search(r'Radius:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if radius_match:
            move_info['range'] = f"Radius: {radius_match.group(1).strip()}"

    damage_match = re.search(r'\*\*Damage:?\*\*\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
    if damage_match:
        move_info['damage'] = damage_match.group(1).strip()
    else:
        damage_match = re.search(r'-\s*Damage:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if damage_match:
            move_info['damage'] = damage_match.group(1).strip()

    duration_match = re.search(r'\*\*Duration:?\*\*\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
    if duration_match:
        move_info['duration'] = duration_match.group(1).strip()

    cost_match = re.search(r'Cost:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
    if cost_match:
        move_info['cost'] = cost_match.group(1).strip()

    effects_match = re.search(r'\*\*Effect[s]?:?\*\*\s*(.+?)(?:\n\n|$)', content, re.IGNORECASE | re.DOTALL)
    if effects_match:
        move_info['effects'] = effects_match.group(1).strip()
    else:
        effect_lines = []
        for line in content.split('\n'):
            if line.strip().startswith('-') and not any(x in line for x in ['Range:', 'Damage:', 'Duration:', 'Cost:']):
                effect_lines.append(line.strip().lstrip('- ').strip())
        if effect_lines:
            move_info['effects'] = ' '.join(effect_lines)

    if not move_info['effects']:
        clean_content = re.sub(r'#\w+', '', content)
        clean_content = re.sub(r'\*\*[^*]+\*\*:?', '', clean_content)
        clean_content = ' '.join([line.strip() for line in clean_content.split('\n') if line.strip() and not line.strip().startswith('-')])
        move_info['description'] = clean_content.strip()[:200]

    return move_info


def calculate_uniqueness_score(move_info):
    """Calculate a uniqueness score for a move based on its properties (0-10)."""
    score = 5.0

    effects = (move_info.get('effects') or '') + ' ' + (move_info.get('description') or '')
    effects_lower = effects.lower()
    action_type = move_info.get('actionType', 'Action')
    range_text = (move_info.get('range') or '').lower()

    if 'danger sense' in action_type.lower():
        score += 1.2
    elif 'reaction' in action_type.lower():
        score += 0.9
    elif 'bonus action' in action_type.lower():
        score += 0.4

    if 'cone' in range_text:
        score += 1.7
    elif 'line' in range_text:
        score += 1.5
    elif 'radius' in range_text or 'aoe' in range_text or 'area' in range_text:
        score += 1.2
    elif 'self' in range_text and 'radius' not in range_text:
        score += 0.6
    elif any(num in range_text for num in ['5', '10', '15', '25']):
        score += 0.3

    complexity_score = 0
    if 'concentration' in effects_lower:
        complexity_score += 1.8
    if 'lingering' in effects_lower or 'persistent' in effects_lower or 'ongoing' in effects_lower:
        complexity_score += 2.2
    if 'charge' in effects_lower or 'stack' in effects_lower:
        complexity_score += 1.5

    status_effects = {
        'stunned': 1.5, 'paralyzed': 1.5, 'petrified': 1.8,
        'prone': 0.8, 'dazed': 1.0, 'blinded': 1.2,
        'disadvantage': 0.7, 'advantage': 0.6, 'restrained': 1.1
    }
    for status, value in status_effects.items():
        if status in effects_lower:
            complexity_score += value
            break

    movement_effects = {
        'pull': 0.7, 'push': 0.6, 'knock': 0.8, 'shove': 0.6,
        'teleport': 1.8, 'swap': 1.6, 'slide': 0.9
    }
    for movement, value in movement_effects.items():
        if movement in effects_lower:
            complexity_score += value
            break

    score += min(4.5, complexity_score)

    utility_score = 0
    if any(word in effects_lower for word in ['dash', 'disengage', 'dodge']):
        utility_score += 0.7
    if any(word in effects_lower for word in ['move', 'movement', 'speed']):
        utility_score += 0.4
    if any(word in effects_lower for word in ['wall', 'barrier', 'shield', 'dome']):
        utility_score += 1.7
    if any(word in effects_lower for word in ['terrain', 'environment', 'create', 'shape']):
        utility_score += 1.3
    if any(word in effects_lower for word in ['ally', 'willing', 'friendly']):
        utility_score += 0.8
    if any(word in effects_lower for word in ['support', 'buff', 'enhance']):
        utility_score += 0.9
    if any(word in effects_lower for word in ['heal', 'restore', 'recover']):
        utility_score += 1.1
    score += min(2.8, utility_score)

    damage_variety = 0
    if 'slashing' in effects_lower:
        damage_variety += 0.6
    if 'piercing' in effects_lower:
        damage_variety += 0.6
    if any(word in effects_lower for word in ['multi', 'multiple', 'several']):
        damage_variety += 0.5
    if any(word in effects_lower for word in ['projectile', 'volley', 'barrage']):
        damage_variety += 0.7
    score += min(1.5, damage_variety)

    if any(word in effects_lower for word in ['temporary slot', 'bonus slot', 'gain slot']):
        score += 2.0
    elif 'generate' in effects_lower or 'create slot' in effects_lower:
        score += 1.6

    if 'combo' in effects_lower or 'synerg' in effects_lower:
        score += 1.0
    elif 'combine' in effects_lower or 'enhance another' in effects_lower:
        score += 0.8

    score = min(10.0, score)
    return round(score, 1)


@bp.route('/api/analyze-moves', methods=['POST'])
def analyze_moves():
    """Analyze bending moves for specific elements and levels.

    Result is cached (resource_cache.analysis_cache_*) keyed on the scanned
    move files' combined mtime/size, so repeat calls with the same
    element/level/mode selection don't re-parse and re-score the whole move
    tree every time.
    """
    try:
        data = request.get_json()
        elements = data.get('elements', ['air'])
        if isinstance(elements, str):
            elements = [elements]
        levels = data.get('levels', [1, 2])
        mode = data.get('mode', 'balance')

        player_root = get_player_root_base()

        move_files = []
        for element in elements:
            element_lower = element.lower()
            element_path = player_root / 'Rules' / 'Bending Rules' / element_lower.capitalize() / f'{element_lower.capitalize()}bending Moves'
            if not element_path.exists():
                continue
            for level in levels:
                level_path = element_path / f'Level {level}'
                if not level_path.exists():
                    continue
                move_files.extend(sorted(level_path.glob('*.md')))

        cache_key = resource_cache.analysis_cache_key(move_files) + f":{mode}:{sorted(elements)}:{sorted(levels)}"
        cached = resource_cache.analysis_cache_get(cache_key)
        if cached is not None:
            return jsonify(cached)

        moves = []
        for element in elements:
            element_lower = element.lower()
            element_path = player_root / 'Rules' / 'Bending Rules' / element_lower.capitalize() / f'{element_lower.capitalize()}bending Moves'
            if not element_path.exists():
                print(f'Warning: Element path not found: {element_path}')
                continue

            for level in levels:
                level_path = element_path / f'Level {level}'
                if not level_path.exists():
                    continue

                for move_file in level_path.glob('*.md'):
                    try:
                        content = move_file.read_text(encoding='utf-8')
                        move_info = parse_move_content(content, move_file.stem, level, element_lower)
                        move_info['filePath'] = str(move_file.relative_to(REPO_ROOT))

                        if mode in ['balance', 'full'] and BALANCE_SCORER_AVAILABLE:
                            try:
                                balance_scorer = get_scorer()
                                balance_result = balance_scorer.score_move(move_info)
                                balance_feedback = balance_scorer.generate_feedback(move_info, balance_result)
                                move_info['mlBalanceScore'] = balance_result['score']
                                move_info['mlBalanceScoringMethod'] = balance_result['method']
                                move_info['mlBalanceFeedback'] = balance_feedback
                            except Exception as e:
                                print(f"Balance scoring error for {move_info['name']}: {e}")

                        if mode in ['simplicity', 'full'] and SIMPLICITY_SCORER_AVAILABLE:
                            try:
                                simplicity_scorer = get_simplicity_scorer()
                                simplicity_score = simplicity_scorer.calculate_score(move_info)
                                simplicity_feedback = simplicity_scorer.generate_feedback(move_info)
                                move_info['mlSimplicityScore'] = simplicity_score
                                move_info['mlSimplicityFeedback'] = simplicity_feedback
                            except Exception as e:
                                print(f"Simplicity scoring error for {move_info['name']}: {e}")

                        if mode in ['uniqueness', 'full']:
                            try:
                                move_info['uniquenessScore'] = calculate_uniqueness_score(move_info)
                            except Exception as e:
                                print(f"Uniqueness scoring error for {move_info['name']}: {e}")
                                move_info['uniquenessScore'] = 5.0

                        if mode == 'full' and FULL_ANALYSIS_SCORER_AVAILABLE:
                            try:
                                balance_score = move_info.get('mlBalanceScore', 5.0)
                                simplicity_score = move_info.get('mlSimplicityScore', 5.0)
                                uniqueness_score = move_info.get('uniquenessScore', 5.0)
                                full_scorer = get_full_analysis_scorer()
                                full_result = full_scorer.calculate_score(
                                    uniqueness_score, balance_score, simplicity_score,
                                    uniqueness_data=move_info.get('uniquenessData'),
                                    balance_data=move_info.get('mlBalanceFeedback'),
                                    simplicity_data=move_info.get('mlSimplicityFeedback')
                                )
                                full_feedback = full_scorer.generate_feedback(
                                    uniqueness_score, balance_score, simplicity_score,
                                    uniqueness_data=move_info.get('uniquenessData'),
                                    balance_data=move_info.get('mlBalanceFeedback'),
                                    simplicity_data=move_info.get('mlSimplicityFeedback')
                                )
                                move_info['mlFullScore'] = full_result['score']
                                move_info['mlFullMethod'] = full_result['method']
                                move_info['mlFullBreakdown'] = full_result['breakdown']
                                move_info['mlFullFeedback'] = full_feedback
                            except Exception as e:
                                print(f"Full analysis error for {move_info['name']}: {e}")

                        moves.append(move_info)
                    except Exception as e:
                        print(f"Error parsing {move_file}: {e}")
                        continue

        result = {'moves': moves, 'elements': elements, 'levels': levels, 'mode': mode}
        resource_cache.analysis_cache_set(cache_key, result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/balance-visualization', methods=['POST'])
def balance_visualization():
    """Generate visualization data for balance score distributions."""
    try:
        data = request.get_json()
        moves = data.get('moves', [])
        if not moves:
            return jsonify({'error': 'No moves provided'}), 400

        scores = []
        move_names = []
        elements = []
        levels = []
        action_types = []

        for move in moves:
            score = move.get('mlBalanceScore') or move.get('balanceScore')
            if score is not None:
                scores.append(float(score))
                move_names.append(move.get('name', 'Unknown'))
                elements.append(move.get('element', 'unknown'))
                levels.append(move.get('level', 1))
                action_types.append(move.get('actionType', 'Action'))

        if not scores:
            return jsonify({'error': 'No balance scores found in moves'}), 400

        import numpy as np
        scores_array = np.array(scores)

        statistics = {
            'mean': float(np.mean(scores_array)), 'median': float(np.median(scores_array)),
            'std': float(np.std(scores_array)), 'min': float(np.min(scores_array)),
            'max': float(np.max(scores_array)), 'q25': float(np.percentile(scores_array, 25)),
            'q75': float(np.percentile(scores_array, 75)), 'total': len(scores),
            'severely_underpowered': int(np.sum(scores_array <= 3.5)),
            'underpowered': int(np.sum((scores_array > 3.5) & (scores_array <= 4.5))),
            'slightly_below': int(np.sum((scores_array > 4.5) & (scores_array <= 5.5))),
            'balanced': int(np.sum((scores_array > 5.5) & (scores_array <= 7.0))),
            'slightly_above': int(np.sum((scores_array > 7.0) & (scores_array <= 8.0))),
            'overpowered': int(np.sum((scores_array > 8.0) & (scores_array <= 9.0))),
            'severely_overpowered': int(np.sum(scores_array > 9.0))
        }

        hist_counts, hist_edges = np.histogram(scores_array, bins=20, range=(0, 10))
        histogram = {
            'counts': hist_counts.tolist(), 'edges': hist_edges.tolist(),
            'bin_centers': [(hist_edges[i] + hist_edges[i + 1]) / 2 for i in range(len(hist_edges) - 1)]
        }

        boxplot_by_element = {}
        for element in set(elements):
            element_scores = [scores[i] for i in range(len(scores)) if elements[i] == element]
            if element_scores:
                boxplot_by_element[element] = {
                    'scores': element_scores, 'min': float(np.min(element_scores)),
                    'q25': float(np.percentile(element_scores, 25)), 'median': float(np.median(element_scores)),
                    'q75': float(np.percentile(element_scores, 75)), 'max': float(np.max(element_scores)),
                    'mean': float(np.mean(element_scores))
                }

        boxplot_by_level = {}
        for level in set(levels):
            level_scores = [scores[i] for i in range(len(scores)) if levels[i] == level]
            if level_scores:
                boxplot_by_level[str(level)] = {
                    'scores': level_scores, 'min': float(np.min(level_scores)),
                    'q25': float(np.percentile(level_scores, 25)), 'median': float(np.median(level_scores)),
                    'q75': float(np.percentile(level_scores, 75)), 'max': float(np.max(level_scores)),
                    'mean': float(np.mean(level_scores))
                }

        scatterplot = {'scores': scores, 'names': move_names, 'elements': elements, 'levels': levels, 'action_types': action_types}

        categories = {
            'Severely Underpowered': statistics['severely_underpowered'],
            'Underpowered': statistics['underpowered'],
            'Slightly Below Avg': statistics['slightly_below'],
            'Well Balanced': statistics['balanced'],
            'Slightly Above Avg': statistics['slightly_above'],
            'Overpowered': statistics['overpowered'],
            'Severely Overpowered': statistics['severely_overpowered']
        }

        return jsonify({
            'histogram': histogram, 'boxplot_by_element': boxplot_by_element,
            'boxplot_by_level': boxplot_by_level, 'scatterplot': scatterplot,
            'statistics': statistics, 'categories': categories
        })
    except Exception as e:
        import traceback
        print(f"Visualization error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
