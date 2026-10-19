"""Run the five UI examples in one fresh process and retain each stage's trace."""
import json
import time

from policy_assistant.ingest import ROOT
from policy_assistant.pipeline import default_pipeline

QUESTIONS = [
    'What security requirements must my laptop meet before I use it for GitLab work?',
    'Who should I contact about home office expenses?',
    'Can I use a public computer to sign into company accounts?',
    'Tell me about the policy.',
    'What should I consider before working while traveling?',
]


def main():
    pipeline = default_pipeline()
    directory = ROOT / 'data/diagnostics'
    directory.mkdir(parents=True, exist_ok=True)
    results = []
    for number, question in enumerate(QUESTIONS, 1):
        if number > 1:
            print('Waiting 65 seconds for the provider token window…', flush=True)
            time.sleep(65)
        print(f'{number}/{len(QUESTIONS)}: {question}', flush=True)
        for stage in ('generation', 'verification'):
            (directory / f'{stage}.json').unlink(missing_ok=True)
        result = pipeline.run(question).as_dict()
        traces = {}
        for stage in ('generation', 'verification'):
            path = directory / f'{stage}.json'
            if path.exists():
                traces[stage] = json.loads(path.read_text())
        results.append({'result': result, 'traces': traces})
        (directory / 'examples.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print(f"  {result['status']} | {result.get('error')} | {result['elapsed_seconds']:.2f}s", flush=True)
    print('Saved data/diagnostics/examples.json')


if __name__ == '__main__':
    main()
