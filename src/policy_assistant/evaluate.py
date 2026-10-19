"""Frozen-case evaluation; missing labels or human reviews never become passing scores."""
import argparse
import hashlib
import json
import statistics
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .ingest import ROOT, atomic_json


def questions_hash(cases):
    return hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest()


def review_fingerprint(row):
    """Bind judgments to the actual answer, question, and full retrieved evidence."""
    fields = ('id', 'mode', 'question', 'expected_status', 'expected_facts',
              'status', 'answer', 'citation_ids', 'hits')
    content = {key:row.get(key) for key in fields}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def retrieval_metrics(retrieved_ids: list[str], relevant_ids: set[str]) -> dict[str, float]:
    retrieved = set(retrieved_ids[:4])
    overlap = len(retrieved & relevant_ids)
    return {'recall_at_4': overlap / len(relevant_ids) if relevant_ids else 0.0,
            'precision_at_4': overlap / len(retrieved) if retrieved else 0.0}


def validate_cases(cases):
    expected = {'direct':6, 'paraphrase':2, 'exact-term':1, 'cross-document':3, 'ambiguous':1, 'unanswerable':2}
    if Counter(c['category'] for c in cases) != expected or len({c['id'] for c in cases}) != 15:
        raise ValueError('Expected exactly 15 distinct cases with the agreed category distribution.')
    for case in cases:
        if case['expected_status'] not in {'answer', 'clarify', 'insufficient'}:
            raise ValueError('Invalid expected status.')
        if case['expected_status'] == 'answer' and not case.get('expected_facts'):
            raise ValueError('Answerable questions require expected facts.')
        if case['category'] == 'cross-document' and len(set(case['required_source_urls'])) < 2:
            raise ValueError('Cross-document questions require at least two sources.')


def validate_labels(labels, cases, chunks, corpus_hash):
    if not labels.get('reviewed') or labels.get('corpus_hash') != corpus_hash:
        raise ValueError('Evidence labels must be reviewed against the active snapshot.')
    if labels.get('questions_hash') != questions_hash(cases):
        raise ValueError('Questions changed after evidence labeling; review labels again.')
    chunk_map = {c.id:c for c in chunks}
    for case in cases:
        ids = labels.get('relevant_chunks', {}).get(case['id'])
        if not isinstance(ids, list) or any(i not in chunk_map for i in ids):
            raise ValueError(f'Invalid or missing evidence labels for {case["id"]}.')
        if case['expected_status'] == 'answer':
            sources = {chunk_map[i].source_url for i in ids}
            if not ids or not set(case['required_source_urls']) <= sources:
                raise ValueError(f'Labels must cover the required evidence for {case["id"]}.')
        elif ids:
            raise ValueError('Non-answer cases must use empty relevant-chunk labels.')


def evaluate_case(case, pipeline, mode, relevant):
    started = time.perf_counter()
    try:
        result = pipeline.run(case['question'], mode).as_dict()
    except Exception:
        result = {'question':case['question'], 'status':'error', 'answer':'Query failed.',
                  'hits':[], 'citation_ids':[], 'elapsed_seconds':time.perf_counter()-started,
                  'error':'query_failed'}
    ids = [h['chunk']['id'] for h in result['hits']]
    sources = {h['chunk']['source_url'] for h in result['hits']}
    row = {**result, 'id':case['id'], 'category':case['category'], 'mode':mode,
            'expected_status':case['expected_status'], 'expected_facts':case.get('expected_facts', []),
            'retrieval':retrieval_metrics(ids, set(relevant[case['id']])),
            'required_sources_retrieved':set(case['required_source_urls']) <= sources,
            'ranks':[{'rank':i+1, 'chunk_id':h['chunk']['id'], 'score':h['score']}
                     for i,h in enumerate(result['hits'])]}
    row['review_hash'] = review_fingerprint(row)
    return row


def summarize(rows, reviews):
    answerable = [r for r in rows if r['expected_status'] == 'answer']
    answers = [r for r in rows if r['status'] == 'answer']
    review_count, total, supported, correct, citation_support = 0, 0, 0, 0, 0
    for row in answers:
        review = reviews.get(f'{row["mode"]}:{row["id"]}')
        if not review or review.get('answer_hash') != review_fingerprint(row):
            continue
        n, s = review.get('total_claims'), review.get('supported_claims')
        if type(n) is not int or type(s) is not int or not 0 <= s <= n:
            raise ValueError('Invalid human review claim counts.')
        if n == 0:
            continue
        review_count += 1
        total += n
        supported += s
        correct += review.get('correct') is True
        citation_support += review.get('citation_support') is True
    all_reviewed = review_count == len(answers) and bool(answers)
    faithfulness = supported / total if total and all_reviewed else None
    valid_citations = sum(bool(r['citation_ids']) and set(r['citation_ids']) <= {h['chunk']['id'] for h in r['hits']} for r in answers)
    edge = [r for r in rows if r['expected_status'] != 'answer']
    return {
        'queries':len(rows), 'errors':sum(r['status']=='error' for r in rows),
        'recall_at_4':statistics.mean(r['retrieval']['recall_at_4'] for r in answerable) if answerable else None,
        'precision_at_4':statistics.mean(r['retrieval']['precision_at_4'] for r in answerable) if answerable else None,
        'answer_coverage':len(answers)/len(rows) if rows else 0.0,
        'answerable_coverage':sum(r['status']=='answer' for r in answerable)/len(answerable) if answerable else None,
        'expected_status_rate':sum(r['status']==r['expected_status'] for r in rows)/len(rows) if rows else None,
        'edge_status_rate':sum(r['status']==r['expected_status'] for r in edge)/len(edge) if edge else None,
        'citation_id_validity':valid_citations/len(answers) if answers else None,
        'reviewed_answers':review_count, 'substantive_answers':len(answers),
        'supported_claims':supported, 'total_claims':total, 'faithfulness':faithfulness,
        'correct_answer_rate':correct/len(answers) if all_reviewed else None,
        'reviewed_citation_support_rate':citation_support/len(answers) if all_reviewed else None,
        'median_warm_seconds':statistics.median(r['elapsed_seconds'] for r in rows if r['status']!='error') if any(r['status']!='error' for r in rows) else None,
    }


def write_report(payload, reviews, output: Path):
    lines = ['# Policy Assistant Evaluation', '',
             f'Run: {payload["created_at"]}. Corpus hash: `{payload["corpus_hash"]}`.', '',
             'Scores use the frozen 15 questions and manually reviewed chunk labels. Human judgments are separate from the runtime model checker.', '']
    for mode in sorted({r['mode'] for r in payload['rows']}):
        rows = [r for r in payload['rows'] if r['mode']==mode]
        summary = summarize(rows, reviews)
        lines.extend([f'## {mode.title()} results', '', '| Metric | Value |', '| --- | --- |'])
        for key, value in summary.items():
            display = 'Unreviewed / undefined' if value is None else f'{value:.3f}' if isinstance(value,float) else str(value)
            lines.append(f'| {key} | {display} |')
        recall, faith, latency = summary['recall_at_4'], summary['faithfulness'], summary['median_warm_seconds']
        lines += ['', f'Targets: recall ≥0.80: {recall is not None and recall >= .8}; faithfulness ≥0.95: {"pending review" if faith is None else faith >= .95}; median warm latency <10s: {latency is not None and latency < 10}. Errors: {summary["errors"]}.', '',
                  '| Case | Expected / actual | Recall@4 | Precision@4 | Required sources present |', '| --- | --- | --- | --- | --- |']
        for r in rows:
            lines.append(f'| {r["id"]} | {r["expected_status"]} / {r["status"]} | {r["retrieval"]["recall_at_4"]:.2f} | {r["retrieval"]["precision_at_4"]:.2f} | {r["required_sources_retrieved"]} |')
        lines += ['', '### Per-question evidence and analysis', '']
        for r in rows:
            ids = ', '.join(h['chunk']['id'] for h in r['hits']) or 'none'
            review = reviews.get(f'{mode}:{r["id"]}', {})
            note = review.get('notes', 'Human failure/success analysis pending.') if review.get('answer_hash') == review_fingerprint(r) else 'Human failure/success analysis pending (missing or stale review).'
            lines += [f'#### {r["id"]}: {r["question"]}', '', r['answer'], '',
                      f'Retrieved: {ids}. Time: {r["elapsed_seconds"]:.2f}s. Error: {r["error"] or "none"}.', '',
                      f'Review hash: `{review_fingerprint(r)}`.', '', note, '']
    lines += ['## Interpretation', '',
              'Compare dense and hybrid rows on the same questions. Missed gold chunks indicate retrieval failure; present evidence with a wrong answer indicates generation or verification failure. Review extraction and chunk boundaries before blaming the generator. Record concrete causes and regressions in the human review notes.', '',
              f'Cold initialization seconds: {payload["cold_initialization_seconds"]:.2f}. Warm-up request seconds: {payload["warmup_seconds"]:.2f}. Errors are retained in coverage and status metrics; latency excludes errors and must be interpreted alongside the error count.', '']
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines))


def prepare_labels(cases, retriever):
    labels = {'reviewed':False, 'corpus_hash':retriever.manifest['corpus_hash'],
              'questions_hash':questions_hash(cases),
              'relevant_chunks':{c['id']:[] for c in cases}}
    path = ROOT / 'eval/relevance.json'
    current = json.loads(path.read_text()) if path.exists() else {}
    if current.get('reviewed'):
        raise ValueError('Existing labels are reviewed. Save them before preparing a new snapshot.')
    atomic_json(path, labels)
    lines = ['# Evidence catalog for manual labeling', '', 'Read every chunk, identify all relevant evidence per case, and update relevance.json before setting reviewed=true.', '']
    for chunk in retriever.chunks:
        lines += [f'## {chunk.id}', '', f'{chunk.source_url} · {chunk.section}', '', chunk.text, '']
    (ROOT / 'eval/evidence-catalog.md').write_text('\n'.join(lines))
    print('Created evidence catalog and label skeleton. Review all 15 expected answers against this snapshot before freezing labels.')


def run_cases(cases, modes, pipe, relevant, payload, output, interval):
    """Checkpoint each real result; explicit resumes keep completed cases."""
    completed = {(r['mode'], r['id']) for r in payload['rows']}
    for mode in modes:
        for case in cases:
            if (mode, case['id']) in completed:
                continue
            if payload['rows'] and interval:
                print(f'Waiting {interval:g}s for provider token window…', flush=True)
                time.sleep(interval)
            print(f'{mode}: {case["id"]}', flush=True)
            row = evaluate_case(case, pipe, mode, relevant)
            payload['rows'].append(row)
            atomic_json(output, payload)
            print(f'  {row.get("status")} | {row.get("error")} | {row.get("elapsed_seconds", 0):.2f}s', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['dense','hybrid','both'], default='both')
    parser.add_argument('--prepare', action='store_true', help='Prepare snapshot-bound manual evidence labels without calling the LLM')
    parser.add_argument('--report-only', action='store_true', help='Regenerate report after human review; makes no model calls')
    parser.add_argument('--interval', type=float, default=65, help='Seconds between scored queries (default 65 for free-tier token limits)')
    parser.add_argument('--resume', action='store_true', help='Continue the same checkpoint without repeating completed cases')
    args = parser.parse_args()
    if args.interval < 0:
        parser.error('--interval must be nonnegative')
    try:
        reviews = json.loads((ROOT / 'eval/reviews.json').read_text())
        if args.report_only:
            payload = json.loads((ROOT / 'reports/results.json').read_text())
        else:
            from .retrieval import load_index
            started = time.perf_counter()
            cases = json.loads((ROOT / 'eval/questions.json').read_text())
            validate_cases(cases)
            retriever = load_index(ROOT / 'data')
            if args.prepare:
                prepare_labels(cases, retriever)
                return
            labels = json.loads((ROOT / 'eval/relevance.json').read_text())
            validate_labels(labels, cases, retriever.chunks, retriever.manifest['corpus_hash'])
            from .config import Settings
            from .pipeline import LangChainClient, Pipeline
            pipe = Pipeline(retriever, LangChainClient(Settings.from_env()))
            cold = time.perf_counter()-started
            warm_started = time.perf_counter()
            warmup = pipe.run(cases[0]['question'])
            if warmup.status == 'error':
                raise ValueError('Provider warm-up failed; verify model access before evaluation.')
            warm_seconds = time.perf_counter()-warm_started
            modes = ['dense','hybrid'] if args.mode=='both' else [args.mode]
            if args.interval:
                print(f'Warm-up complete. Waiting {args.interval:g}s before scoring…', flush=True)
                time.sleep(args.interval)
            revision = hashlib.sha256(b''.join((ROOT / 'src/policy_assistant' / name).read_bytes()
                                              for name in ('pipeline.py', 'prompts.py', 'retrieval.py'))).hexdigest()
            payload = {'created_at':datetime.now(timezone.utc).isoformat(),
                       'corpus_hash':retriever.manifest['corpus_hash'], 'questions_hash':questions_hash(cases),
                       'cold_initialization_seconds':cold, 'warmup_seconds':warm_seconds,
                       'embedding_model':retriever.manifest['embedding_model'],
                       'generation_model':Settings.from_env().model,
                       'pipeline_revision':revision, 'query_interval_seconds':args.interval,
                       'requested_modes':modes, 'rows':[]}
            results_path = ROOT / 'reports/results.json'
            if args.resume:
                previous = json.loads(results_path.read_text())
                for field in ('corpus_hash', 'questions_hash', 'generation_model', 'pipeline_revision', 'requested_modes'):
                    if previous.get(field) != payload[field]:
                        raise ValueError(f'Cannot resume: {field} changed. Start a new evaluation.')
                payload = previous
            elif results_path.exists():
                archive = ROOT / 'reports/runs' / f'{time.time_ns()}.json'
                atomic_json(archive, json.loads(results_path.read_text()))
            atomic_json(results_path, payload)
            run_cases(cases, modes, pipe, labels['relevant_chunks'], payload, results_path, args.interval)
        write_report(payload, reviews, ROOT / 'reports/evaluation.md')
        print('Saved reports/evaluation.md. Complete human reviews before claiming faithfulness or correctness.')
    except Exception as exc:
        # Expose only our setup validation messages, never remote exception bodies.
        message = str(exc) if isinstance(exc, (ValueError, FileNotFoundError)) else 'Dependency, model, or provider setup failed. See README.md.'
        if isinstance(exc, FileNotFoundError):
            message = 'Required local artifacts are missing. Follow README.md setup and evaluation labeling steps.'
        parser.exit(1, f'Evaluation not completed: {message}\n')


if __name__ == '__main__':
    main()
