"""Independent replay for privileged tasks; trusted live grading for realtime tasks."""
import argparse
import json
from pathlib import Path
from config_schema import validate_instance
from grade import grade
from mode_config import validate_mode, mode_hash


def load_actions(path, allowed, maximum):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise ValueError('missing or oversized actions.json')
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or set(data) != {'schema', 'actions'} or data['schema'] != 'game-actions/1.0':
        raise ValueError('invalid trajectory schema')
    actions = data['actions']
    if not isinstance(actions, list) or len(actions) > maximum or any(not isinstance(a, str) or a not in allowed for a in actions):
        raise ValueError('invalid trajectory actions')
    return actions


def replay(instance, mode, source, output, factory, validate_metrics):
    from server import Game
    game = Game.open(factory, instance, Path('/tests/assets'), output, wall_clock=110)
    invalid = None
    try:
        if game.final is None:
            try:
                actions = load_actions(source, game.spec()['action_schema']['enum'], mode['max_actions'])
            except (ValueError, OSError, TypeError) as exc:
                actions = []
                invalid = str(exc)
            for i, action in enumerate(actions):
                if game.final is not None:
                    invalid = 'actions after episode end'
                    break
                game.submit({'action': action, 'expected_step': game.steps, 'request_id': str(i)})
            if game.final is None:
                game.finalize('agent_finished')
        result = grade(game.final, instance, validate_metrics)
        if invalid and result['result_valid']:
            result.update(success=0.0, primary_score=0, reason='bad_trajectory', submission_error=invalid)
            # Never retain a successful metric from a rejected action sequence.
            result['native_metrics'] = {**result['native_metrics'], 'success': 0, 'completion_score': 0}
        result.update(graded_by_live=0, replays=int(invalid is None), replays_succeeded=int(bool(result['success'])), execution_mode='privileged')
        return result
    finally:
        game.close()
        recording = Path(output) / 'recording.json'
        if recording.exists():
            data = json.loads(recording.read_text()); data['video_source'] = 'verifier_replay'
            recording.write_text(json.dumps(data, indent=2) + '\n')
            # This is verifier-owned replay evidence, finalized before the verifier returns.
            final_path = Path(output) / 'final.json'
            if final_path.exists():
                final = json.loads(final_path.read_text()); final['video_source'] = 'verifier_replay'
                final_path.write_text(json.dumps(final, indent=2) + '\n')


def main():
    from metric_rules import validate_metrics
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', default='/tests/instance.json')
    parser.add_argument('--mode', default='/tests/mode.json')
    parser.add_argument('--output', default='/logs/verifier')
    parser.add_argument('--actions', default='/app/output/actions.json')
    args = parser.parse_args()
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    instance = validate_instance(json.loads(Path(args.instance).read_text()))
    mode = validate_mode(json.loads(Path(args.mode).read_text()))
    try:
        if mode['mode'] == 'privileged':
            from adapter import Adapter
            result = replay(instance, mode, args.actions, output, Adapter, validate_metrics)
        else:
            final = json.loads(Path('/data/final.json').read_text())
            timing = json.loads(Path('/data/realtime.json').read_text())
            if timing['mode_sha256'] != mode_hash(mode) or timing['executed_ticks'] != final['steps']:
                raise ValueError('realtime evidence mismatch')
            result = grade(final, instance, validate_metrics)
            result.update(execution_mode='realtime', realtime=1, held_steps=timing['held_steps'],
                          late_steps=timing['late_steps'], max_lag_s=timing['max_lag_s'],
                          stalled_s=timing['stalled_s'], service_time_s=timing['time_s'],
                          preparation_s=timing['preparation_s'], clock_s=timing['clock_s'])
    except Exception as exc:
        result = {'success': 0.0, 'infra_error': 1, 'result_valid': False, 'error_category': 'environment', 'error': str(exc)}
    (output/'metrics.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    (output/'reward.json').write_text(json.dumps({k:v for k,v in result.items() if isinstance(v,(int,float))}, indent=2)+'\n')
    if result['infra_error']:
        raise SystemExit('independent execution or trusted evidence failed')
    (output/'reward.txt').write_text(str(result['success'])+'\n')


if __name__ == '__main__':
    main()
