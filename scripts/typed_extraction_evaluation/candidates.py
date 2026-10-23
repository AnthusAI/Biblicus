"""
Candidate extractors for the typed extraction evaluation.

Every candidate exposes ``extract(text)`` and returns entity mentions and typed relations in one shape:
mentions are ``{"start", "end", "text", "kind", "score"}`` and relations are
``{"subject": mention, "object": mention, "type", "score"}``. Candidates receive the same closed vocabulary
labels and no further help.
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple

from common import normalise_name

SPACY_LABEL_TO_KIND = {
    "ORG": "maker",
    "PERSON": "maker",
    "PRODUCT": "model",
    "WORK_OF_ART": "model",
    "LAW": "licence",
}

TOKEN_PATTERN = re.compile(r"[0-9A-Za-z]+")


class Registry:
    """
    Known entities with aliases, used by the gazetteer candidate and by the shared resolution step.

    :ivar aliases: Mapping from normalised alias to a list of ``(kind, entity key)`` pairs.
    :vartype aliases: dict[str, list[tuple[str, str]]]
    """

    def __init__(self, gold_records: List[dict]):
        counts: Dict[str, Dict[Tuple[str, str], int]] = {}
        for record in gold_records:
            for mention in record["mentions"]:
                for alias in {normalise_name(mention["text"]), mention["key"]}:
                    counts.setdefault(alias, {})
                    pair = (mention["kind"], mention["key"])
                    counts[alias][pair] = counts[alias].get(pair, 0) + 1
        self.aliases: Dict[str, List[Tuple[str, str]]] = {
            alias: [pair for pair, _ in sorted(options.items(), key=lambda entry: -entry[1])]
            for alias, options in counts.items()
        }
        self.longest = max((len(alias.split()) for alias in self.aliases), default=1)

    def resolve(self, text: str, kind: str) -> Optional[str]:
        """
        Resolve a mention to a known entity key by normalised alias and kind.

        :param text: Mention text.
        :type text: str
        :param kind: Predicted kind.
        :type kind: str
        :return: Entity key, or ``None`` when the mention matches no known alias for the kind.
        :rtype: str | None
        """
        for option_kind, key in self.aliases.get(normalise_name(text), []):
            if option_kind == kind:
                return key
        return None

    def find_mentions(self, text: str) -> List[dict]:
        """
        Find known aliases in text by longest match over normalised tokens.

        :param text: Document text.
        :type text: str
        :return: Mentions with the registry kind.
        :rtype: list[dict]
        """
        tokens = [
            (match.group().lower(), match.start(), match.end())
            for match in TOKEN_PATTERN.finditer(text)
        ]
        mentions = []
        index = 0
        while index < len(tokens):
            matched = None
            for length in range(min(self.longest, len(tokens) - index), 0, -1):
                alias = " ".join(token[0] for token in tokens[index : index + length])
                if alias in self.aliases:
                    matched = (length, alias)
                    break
            if matched is None:
                index += 1
                continue
            length, alias = matched
            start, end = tokens[index][1], tokens[index + length - 1][2]
            mentions.append(
                {
                    "start": start,
                    "end": end,
                    "text": text[start:end],
                    "kind": self.aliases[alias][0][0],
                    "score": 1.0,
                }
            )
            index += length
        return mentions


class GazetteerCandidate:
    """
    Alias matcher that finds only entities already in the registry.
    """

    name = "gazetteer"
    version = "biblicus-evaluation alias matcher (normalised token longest match)"

    def __init__(self, vocabulary: dict, registry: Registry):
        self.registry = registry

    def extract(self, text: str):
        """
        Extract mentions and relations from one document.

        :param text: Document text.
        :type text: str
        :return: Mentions and relations.
        :rtype: tuple[list[dict], list[dict]]
        """
        return self.registry.find_mentions(text), []


class SpacyCandidate:
    """
    The existing spaCy named entity pipeline with a fixed label-to-kind map.
    """

    name = "spacy-en_core_web_sm"

    def __init__(self, vocabulary: dict, registry: Registry):
        import spacy
        from huggingface_hub import snapshot_download

        self.nlp = spacy.load(snapshot_download("spacy/en_core_web_sm"))
        self.version = f"spacy {spacy.__version__}, en_core_web_sm {self.nlp.meta['version']}"
        self.kinds = set(vocabulary["entity_kinds"])

    def extract(self, text: str):
        """
        Extract mentions and relations from one document.

        :param text: Document text.
        :type text: str
        :return: Mentions and relations.
        :rtype: tuple[list[dict], list[dict]]
        """
        mentions = []
        for entity in self.nlp(text).ents:
            kind = SPACY_LABEL_TO_KIND.get(entity.label_)
            if kind in self.kinds:
                mentions.append(
                    {
                        "start": entity.start_char,
                        "end": entity.end_char,
                        "text": entity.text,
                        "kind": kind,
                        "score": 1.0,
                    }
                )
        return mentions, []


class GlinerCandidate:
    """
    Zero-shot GLiNER-family span model (GLiNER, NuNER Zero).
    """

    def __init__(
        self, vocabulary: dict, registry: Registry, model_id: str, threshold: float, name: str
    ):
        import gliner
        import torch
        from gliner import GLiNER

        self.name = name
        self.model = GLiNER.from_pretrained(model_id)
        self.threshold = threshold
        self.label_to_kind = {label: kind for kind, label in vocabulary["entity_labels"].items()}
        self.version = f"gliner {gliner.__version__ if hasattr(gliner, '__version__') else '0.2.29'}, torch {torch.__version__}, {model_id}, threshold {threshold}"

    def extract(self, text: str):
        """
        Extract mentions and relations from one document.

        :param text: Document text.
        :type text: str
        :return: Mentions and relations.
        :rtype: tuple[list[dict], list[dict]]
        """
        predictions = self.model.predict_entities(
            text, list(self.label_to_kind), threshold=self.threshold, flat_ner=True
        )
        mentions = [
            {
                "start": p["start"],
                "end": p["end"],
                "text": p["text"],
                "kind": self.label_to_kind[p["label"]],
                "score": float(p["score"]),
            }
            for p in predictions
        ]
        return sorted(mentions, key=lambda mention: mention["start"]), []


class Gliner2Candidate:
    """
    GLiNER2 joint entity and relation extractor.
    """

    name = "gliner2-base"

    def __init__(
        self,
        vocabulary: dict,
        registry: Registry,
        threshold: float,
        model_id: str = "fastino/gliner2-base-v1",
    ):
        import gliner2
        import torch
        from gliner2 import GLiNER2

        self.model = GLiNER2.from_pretrained(model_id)
        self.threshold = threshold
        self.label_to_kind = {label: kind for kind, label in vocabulary["entity_labels"].items()}
        self.relation_to_type = {label: key for key, label in vocabulary["relation_labels"].items()}
        self.version = f"gliner2 {getattr(gliner2, '__version__', '2.1.0')}, torch {torch.__version__}, {model_id}, threshold {threshold}"

    def extract(self, text: str):
        """
        Extract mentions and relations from one document.

        :param text: Document text.
        :type text: str
        :return: Mentions and relations.
        :rtype: tuple[list[dict], list[dict]]
        """
        entities = self.model.extract_entities(
            text,
            list(self.label_to_kind),
            threshold=self.threshold,
            include_spans=True,
            include_confidence=True,
        )["entities"]
        mentions = []
        for label, found in entities.items():
            for item in found:
                mentions.append(
                    {
                        "start": item["start"],
                        "end": item["end"],
                        "text": item["text"],
                        "kind": self.label_to_kind[label],
                        "score": float(item["confidence"]),
                    }
                )
        mentions.sort(key=lambda mention: (mention["start"], -mention["end"]))
        relations_raw = self.model.extract_relations(
            text,
            list(self.relation_to_type),
            threshold=self.threshold,
            include_spans=True,
            include_confidence=True,
        )["relation_extraction"]
        relations = []
        for label, found in relations_raw.items():
            for item in found:
                relations.append(
                    {
                        "subject": {
                            "start": item["head"]["start"],
                            "end": item["head"]["end"],
                            "text": item["head"]["text"],
                        },
                        "object": {
                            "start": item["tail"]["start"],
                            "end": item["tail"]["end"],
                            "text": item["tail"]["text"],
                        },
                        "type": self.relation_to_type[label],
                        "score": float(min(item["head"]["confidence"], item["tail"]["confidence"])),
                    }
                )
        return mentions, relations


class RelexCandidate:
    """
    GLiNER-relex joint entity and relation extractor.
    """

    name = "gliner-relex-large"

    def __init__(
        self,
        vocabulary: dict,
        registry: Registry,
        threshold: float,
        model_id: str = "knowledgator/gliner-relex-large-v1.0",
    ):
        import torch
        from gliner import GLiNER

        self.model = GLiNER.from_pretrained(model_id)
        self.threshold = threshold
        self.label_to_kind = {label: kind for kind, label in vocabulary["entity_labels"].items()}
        self.relation_to_type = {label: key for key, label in vocabulary["relation_labels"].items()}
        self.version = (
            f"gliner 0.2.29, torch {torch.__version__}, {model_id}, threshold {threshold}"
        )

    def extract(self, text: str):
        """
        Extract mentions and relations from one document.

        :param text: Document text.
        :type text: str
        :return: Mentions and relations.
        :rtype: tuple[list[dict], list[dict]]
        """
        entities, relations_raw = self.model.inference(
            texts=[text],
            labels=list(self.label_to_kind),
            relations=list(self.relation_to_type),
            threshold=self.threshold,
            relation_threshold=self.threshold,
            return_relations=True,
            flat_ner=True,
        )
        mentions = [
            {
                "start": e["start"],
                "end": e["end"],
                "text": e["text"],
                "kind": self.label_to_kind[e["label"]],
                "score": float(e["score"]),
            }
            for e in entities[0]
        ]
        relations = []
        for item in relations_raw[0]:
            head, tail = item["head"], item["tail"]
            relations.append(
                {
                    "subject": {
                        "start": head.get("start"),
                        "end": head.get("end"),
                        "text": head["text"],
                    },
                    "object": {
                        "start": tail.get("start"),
                        "end": tail.get("end"),
                        "text": tail["text"],
                    },
                    "type": self.relation_to_type[item["relation"]],
                    "score": float(item["score"]),
                }
            )
        return sorted(mentions, key=lambda mention: mention["start"]), relations


class GlirelCandidate:
    """
    GLiNER entity spans followed by GLiREL zero-shot relation classification.
    """

    def __init__(
        self,
        vocabulary: dict,
        registry: Registry,
        threshold: float,
        entity_model_id: str = "urchade/gliner_medium-v2.1",
    ):
        import glirel
        import spacy
        from glirel import GLiREL

        self.name = "gliner-medium+glirel-large"
        self.entities = GlinerCandidate(
            vocabulary, registry, entity_model_id, threshold, "gliner-medium"
        )
        self.model = GLiREL._from_pretrained(
            model_id="jackboyla/glirel-large-v0",
            revision=None,
            cache_dir=None,
            force_download=False,
            proxies=None,
            resume_download=False,
            local_files_only=False,
            token=None,
        )
        self.tokenizer = spacy.blank("en")
        self.threshold = threshold
        self.relation_to_type = {label: key for key, label in vocabulary["relation_labels"].items()}
        self.version = f"{self.entities.version}; glirel {getattr(glirel, '__version__', '1.2.1')}, jackboyla/glirel-large-v0, threshold {threshold}"

    def extract(self, text: str):
        """
        Extract mentions and relations from one document.

        :param text: Document text.
        :type text: str
        :return: Mentions and relations.
        :rtype: tuple[list[dict], list[dict]]
        """
        mentions, _ = self.entities.extract(text)
        doc = self.tokenizer(text)
        spans = []
        for mention in mentions:
            span = doc.char_span(mention["start"], mention["end"], alignment_mode="expand")
            if span is not None:
                spans.append([span.start, span.end - 1, mention["kind"], mention["text"], mention])
        ner = [[start, end, kind, surface] for start, end, kind, surface, _ in spans]
        relations = []
        if len(ner) >= 2:
            found = self.model.predict_relations(
                [token.text for token in doc],
                list(self.relation_to_type),
                threshold=self.threshold,
                ner=ner,
                top_k=1,
            )
            for item in found:
                head = next(
                    (s[4] for s in spans if [s[0], s[1] + 1] == list(item["head_pos"])), None
                )
                tail = next(
                    (s[4] for s in spans if [s[0], s[1] + 1] == list(item["tail_pos"])), None
                )
                if head is None or tail is None:
                    continue
                relations.append(
                    {
                        "subject": {
                            "start": head["start"],
                            "end": head["end"],
                            "text": head["text"],
                        },
                        "object": {
                            "start": tail["start"],
                            "end": tail["end"],
                            "text": tail["text"],
                        },
                        "type": self.relation_to_type[item["label"]],
                        "score": float(item["score"]),
                    }
                )
        return mentions, relations


class HybridCandidate:
    """
    Registry alias matches first, then GLiNER2 for everything the registry does not cover.
    """

    name = "gazetteer+gliner2"

    def __init__(self, vocabulary: dict, registry: Registry, threshold: float):
        self.registry = registry
        self.span_model = Gliner2Candidate(vocabulary, registry, threshold)
        self.version = f"alias matcher + {self.span_model.version}"

    def extract(self, text: str):
        """
        Extract mentions and relations from one document.

        :param text: Document text.
        :type text: str
        :return: Mentions and relations.
        :rtype: tuple[list[dict], list[dict]]
        """
        known = self.registry.find_mentions(text)
        mentions, relations = self.span_model.extract(text)
        extra = [
            m
            for m in mentions
            if not any(m["start"] < k["end"] and k["start"] < m["end"] for k in known)
        ]
        combined = sorted(known + extra, key=lambda mention: mention["start"])
        return combined, relations


class LlmCandidate:
    """
    Optional cheap language-model baseline (GPT-6 Luna only), hard-capped on spend.
    """

    name = "gpt-6-luna"

    def __init__(
        self,
        vocabulary: dict,
        registry: Registry,
        model_id: str,
        budget_usd: float,
        price_in: float,
        price_out: float,
    ):
        import openai

        self.client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.model_id = model_id
        self.vocabulary = vocabulary
        self.budget_usd = budget_usd
        self.price_in = price_in
        self.price_out = price_out
        self.spent_usd = 0.0
        self.tokens_in = 0
        self.tokens_out = 0
        self.version = f"openai {openai.__version__}, {model_id}"

    def extract(self, text: str):
        """
        Extract mentions and relations from one document.

        :param text: Document text.
        :type text: str
        :return: Mentions and relations.
        :rtype: tuple[list[dict], list[dict]]
        """
        if self.spent_usd >= self.budget_usd:
            raise RuntimeError("LLM budget exhausted")
        kinds = "; ".join(
            f"{key} = {label}" for key, label in self.vocabulary["entity_labels"].items()
        )
        relations = "; ".join(
            f"{key} = {label}" for key, label in self.vocabulary["relation_labels"].items()
        )
        prompt = (
            "Extract typed entities and relations from the text.\n"
            f"Entity kinds (key = label): {kinds}\n"
            f"Relation types (key = label): {relations}\n"
            'Return JSON only: {"entities":[{"text":"exact text from the document","kind":"<key>"}],'
            '"relations":[{"subject":"entity text","type":"<key>","object":"entity text"}]}\n\nText:\n'
            + text
        )
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        usage = response.usage
        self.tokens_in += usage.prompt_tokens
        self.tokens_out += usage.completion_tokens
        self.spent_usd += (
            usage.prompt_tokens * self.price_in + usage.completion_tokens * self.price_out
        ) / 1_000_000
        data = json.loads(response.choices[0].message.content)
        mentions = []
        for entity in data.get("entities", []):
            surface, kind = entity.get("text", ""), entity.get("kind")
            if kind not in self.vocabulary["entity_kinds"]:
                continue
            location = text.find(surface) if surface else -1
            if location < 0:
                mentions.append(
                    {"start": -1, "end": -1, "text": surface, "kind": kind, "score": 1.0}
                )
                continue
            for match in re.finditer(re.escape(surface), text):
                mentions.append(
                    {
                        "start": match.start(),
                        "end": match.end(),
                        "text": surface,
                        "kind": kind,
                        "score": 1.0,
                    }
                )
        relations_out = [
            {
                "subject": {"start": None, "end": None, "text": r.get("subject", "")},
                "object": {"start": None, "end": None, "text": r.get("object", "")},
                "type": r.get("type"),
                "score": 1.0,
            }
            for r in data.get("relations", [])
            if r.get("type") in self.vocabulary["relation_types"]
        ]
        return mentions, relations_out
