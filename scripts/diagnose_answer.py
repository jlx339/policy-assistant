"""Inspect a single live answer without exposing credentials or provider errors."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from policy_assistant.pipeline import default_pipeline, _validated
from policy_assistant.prompts import GENERATOR, VERIFIER


def main():
    pipeline = default_pipeline()
    question = "What security requirements must my laptop meet before I use it for GitLab work?"
    state = pipeline.retrieve({'question': question})
    print('Retrieval:', len(state.get('hits', [])), 'passages')
    if state.get('error'):
        print('Stopped:', state['error'])
        return
    payload = {'question': question, 'evidence': state['context']}
    for stage, prompt in [('generation', GENERATOR), ('verification', VERIFIER)]:
        try:
            result = pipeline.client.llm.invoke([
                SystemMessage(content=prompt),
                HumanMessage(content=json.dumps(payload)),
            ])
            print(stage, 'finish_reason:', result.response_metadata.get('finish_reason'))
            print(stage, 'content:', result.content)
            response = json.loads(result.content)
        except Exception as error:
            print(stage, 'failed:', type(error).__name__)
            return
        if stage == 'generation':
            valid = _validated(response, state['hits'])
            print('Schema and citations valid:', valid)
            if not valid:
                return
            payload['response'] = response


if __name__ == '__main__':
    main()
