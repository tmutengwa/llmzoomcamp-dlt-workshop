import os
import sys

from dotenv import load_dotenv

load_dotenv()

import logfire

logfire.configure()
logfire.instrument_pydantic_ai()

from agent import faq_agent, SearchDeps
from ingest import build_index, load_faq_data


def main():
    # Download the FAQ and build the search index
    documents = load_faq_data()
    index = build_index(documents)

    # Inject the index into the agent via the dependency container
    deps = SearchDeps(index=index)

    # Ask a question. run_sync blocks until the agent is done;
    # the agent may call search multiple times before answering.
    question = sys.argv[1] if len(sys.argv) > 1 else 'I just discovered the course. Can I join it?'
    result = faq_agent.run_sync(question, deps=deps)

    print(result.output)

    # Work is done — flush pending spans, then skip Python's normal interpreter
    # finalization. A pydantic-core/PyO3 bug segfaults when CPython tears down
    # module globals (finalize_modules) and a datetime-linked weakref callback
    # inside pydantic-core fires against already-freed interpreter state. This
    # exit only happens in finalize_modules, never during the program's actual
    # work, so os._exit(0) here is safe and sidesteps the crash entirely.
    logfire.force_flush()
    sys.stdout.flush()
    os._exit(0)


if __name__ == '__main__':
    main()
