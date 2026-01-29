from pathlib import Path
from tempfile import TemporaryDirectory

from biblicus.backends import get_backend
from biblicus.context import (
    ContextPackPolicy,
    TokenBudget,
    build_context_pack,
    fit_context_pack_to_token_budget,
)
from biblicus.corpus import Corpus
from biblicus.models import QueryBudget


if __name__ == "__main__":
    with TemporaryDirectory(prefix="biblicus-readme-demo-") as temp_dir:
        # This script is a narrative demonstration of the README flow using the Python API.
        # It keeps each stage explicit so the sequence reads like a story: collect memories,
        # build a retrieval run, query for evidence, then shape a context pack for a model.

        corpus_path = Path(temp_dir) / "corpora" / "story"
        corpus = Corpus.init(corpus_path)

        # Stage 1: Ingest a handful of short memories into a corpus.
        # Each memory is a regular note stored as a corpus item with lightweight metadata.

        notes = [
            ("User name", "The user's name is Tactus Maximus."),
            (
                "Button style preference",
                "Primary button style preference: the user's favorite color is magenta.",
            ),
            ("Style preference", "The user prefers concise answers."),
            ("Language preference", "The user dislikes idioms and abbreviations."),
            (
                "Engineering preference",
                "The user likes code that is over-documented and behavior-driven.",
            ),
        ]
        for note_title, note_text in notes:
            corpus.ingest_note(note_text, title=note_title, tags=["memory"])

        # Stage 2: Build a retrieval run and ask a question that should surface the preference.
        # The scan backend is a simple lexical baseline that makes this demonstration deterministic.

        backend = get_backend("scan")
        run = backend.build_run(corpus, recipe_name="Story demo", config={})
        budget = QueryBudget(
            max_total_items=5,
            max_total_characters=2000,
            max_items_per_source=None,
        )
        result = backend.query(
            corpus,
            run=run,
            query_text="Primary button style preference",
            budget=budget,
        )
        if not result.evidence:
            raise AssertionError("Expected non-empty evidence list from retrieval")

        # Stage 3: Turn evidence into a context pack and then fit it to a token budget.
        # This models the step where your application shapes evidence into model context.

        policy = ContextPackPolicy(join_with="\n\n")
        context_pack = build_context_pack(result, policy=policy)
        context_pack = fit_context_pack_to_token_budget(
            context_pack,
            policy=policy,
            token_budget=TokenBudget(max_tokens=60),
        )
        if "magenta" not in context_pack.text.lower():
            raise AssertionError("Expected context pack to include the user's color preference")

        print("End-to-end README demo succeeded.")
        print()
        print("Retrieval evidence (first item):")
        print(result.evidence[0].model_dump_json(indent=2))
        print()
        print("Context pack:")
        print(context_pack.text)
