"""Check a complete two-side Harbor smoke job; no model calls or Docker needed."""
import argparse
import json
from pathlib import Path


def check(job, agent):
    job = Path(job)

    def read(path):
        return json.loads(path.read_text())

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    expected = {f'fightingice-zen-kick-p{side}-i01-standard' for side in (1, 2)}
    results = sorted(job.glob('*/result.json'))
    require(len(results) == 2, 'expected exactly two completed trials')
    seen, rows = set(), []
    for path in results:
        result = read(path)
        name = result['task_name'].rsplit('/', 1)[-1]
        require(name in expected and name not in seen, 'unknown or duplicate task')
        seen.add(name)
        require(result.get('exception_info') is None, f'{name}: Harbor exception')
        require(result.get('agent_info', {}).get('name') == agent, f'{name}: unexpected agent')
        trial = path.parent
        reward = read(trial / 'verifier/reward.json')
        require(reward.get('result_valid') == 1, f'{name}: invalid verifier result')
        for field in ('infra_error', 'sim_error', 'environment_error'):
            require(reward.get(field) == 0, f'{name}: {field}')
        score, steps = (100, 10800) if agent == 'oracle' else (0, 0)
        require(reward.get('primary_score') == score, f'{name}: unexpected score')
        require(reward.get('success') == int(agent == 'oracle'), f'{name}: unexpected success')
        final = read(trial / 'artifacts/data/final.json')
        require(final['steps'] == reward['steps'] == steps, f'{name}: input count changed')
        require(final['terminated'] == (agent == 'oracle') and not final['truncated'], f'{name}: ending flags')
        require(final['reason'] == ('native_terminated' if agent == 'oracle' else 'agent_finished'), f'{name}: ending reason')
        require(final['metrics']['completed_rounds'] == (3 if agent == 'oracle' else 0), f'{name}: round count')
        require(read(trial / 'artifacts/data/recording.json')['render_error'] is None, f'{name}: rendering failed')
        video = trial / 'artifacts/data/replay.mp4'
        require(video.is_file() and video.stat().st_size > 1000, f'{name}: recording missing')
        rows.append({'task': name, 'score': score, 'steps': steps,
                     'resource_monitor_missing': reward.get('resource_monitor_missing'),
                     'resource_enforced': reward.get('resource_enforced')})
    require(seen == expected, 'task coverage incomplete')
    require(read(job / 'game-provenance.json')['status'] == 'complete', 'provenance incomplete')
    require(read(job / 'runtime-images.json')['complete'] is True, 'runtime image capture incomplete')
    require(read(job / 'game-report/summary.json')['complete'] is True, 'derived report incomplete')
    print(json.dumps({'agent': agent, 'evidence': 'complete', 'trials': rows}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', type=Path)
    parser.add_argument('agent', choices=('oracle', 'nop'))
    args = parser.parse_args()
    check(args.job, args.agent)
