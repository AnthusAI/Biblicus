"""Coverage-focused unit tests for HTML heuristic extraction branches."""

from __future__ import annotations

import sys

import pytest

from biblicus import html_heuristics
from biblicus.html_heuristics import (
    HtmlHeuristicDocument,
    extract_html_heuristics,
    heuristic_document_to_structured,
    structured_metadata_is_sufficient,
)


def _wrap_head_and_body(head_markup: str = "", body_markup: str = "") -> str:
    return f"<html><head>{head_markup}</head><body>{body_markup}</body></html>"


def _json_ld_script(payload_text: str) -> str:
    return f'<script type="application/ld+json">{payload_text}</script>'


def test_document_without_title_or_meta_reports_title_authors_and_citations_missing():
    """A bare page produces every missing-field warning and no html_meta layer."""
    doc = extract_html_heuristics(_wrap_head_and_body(body_markup="<p>Plain text only.</p>"))
    warning_codes = {warning["code"] for warning in doc.warnings}
    assert warning_codes == {"title_missing", "authors_missing", "citations_missing"}
    assert "html_meta" not in doc.raw_metadata
    assert doc.body_text == "Plain text only."


def test_empty_document_has_no_body_and_no_footer_candidates():
    """An empty document has no body element, so body and footer extraction are skipped."""
    doc = extract_html_heuristics("")
    assert doc.body_html == ""
    assert doc.reference_candidates == []


def test_body_without_child_elements_yields_no_footer_candidates():
    """A body with only text and no elements yields no footer link candidates."""
    candidates = html_heuristics._extract_footer_link_candidates(
        html_heuristics._build_soup("<html><body></body></html>"),
        source_uri="",
        bottom_fraction=0.25,
    )
    assert candidates == []


def test_structured_metadata_is_sufficient_rejects_non_dict_payload():
    """Non-dictionary payloads are never sufficient."""
    assert structured_metadata_is_sufficient(None) is False
    assert structured_metadata_is_sufficient(["not", "a", "dict"]) is False


def test_structured_metadata_is_sufficient_accepts_authors_without_citations():
    """Authors alone are sufficient when there are no citations."""
    assert structured_metadata_is_sufficient({"authors": [{"name": "A"}]}) is True
    assert structured_metadata_is_sufficient({"authors": "bad", "citations": "bad"}) is False


def test_structured_metadata_is_sufficient_counts_identifier_citations_as_strong():
    """A citation with a DOI or URL is strong, and non-dict entries are skipped."""
    structured = {
        "authors": [],
        "citations": ["not a citation", {"doi": "10.1000/abc"}],
    }
    assert structured_metadata_is_sufficient(structured) is True
    assert structured_metadata_is_sufficient({"citations": [{"url": "https://x.test"}]}) is True


def test_structured_metadata_is_sufficient_counts_complete_bibliographic_citation_as_strong():
    """A citation with a long title, a year, and an author is strong."""
    structured = {
        "citations": [
            {"title": "A sufficiently long title", "year": 2020, "authors": ["Ada Lovelace"]}
        ]
    }
    assert structured_metadata_is_sufficient(structured) is True


def test_structured_metadata_is_sufficient_rejects_weak_citations_without_enough_authors():
    """Weak citations fail unless there are at least three and some authors."""
    weak_citation = {"title": "Short", "year": None, "authors": "not-a-list"}
    assert structured_metadata_is_sufficient({"citations": [weak_citation]}) is False
    three_weak_citations = [weak_citation, weak_citation, weak_citation]
    assert not structured_metadata_is_sufficient({"authors": [], "citations": three_weak_citations})
    assert structured_metadata_is_sufficient(
        {"authors": [{"name": "A"}], "citations": three_weak_citations}
    )


def test_build_soup_raises_value_error_when_beautifulsoup_is_missing(monkeypatch):
    """Missing beautifulsoup4 yields a clear ValueError."""
    monkeypatch.setitem(sys.modules, "bs4", None)
    with pytest.raises(ValueError, match="beautifulsoup4"):
        html_heuristics._build_soup("<html></html>")


def test_build_soup_uses_builtin_parser_when_lxml_is_missing(monkeypatch):
    """Missing lxml falls through to the built-in html.parser."""
    monkeypatch.setitem(sys.modules, "lxml", None)
    soup = html_heuristics._build_soup("<html><body><p>hello</p></body></html>")
    assert soup.find("p").get_text() == "hello"


def test_json_ld_skips_empty_and_malformed_scripts():
    """Empty and undecodable JSON-LD scripts are ignored."""
    head = _json_ld_script("   ") + _json_ld_script("{not json")
    doc = extract_html_heuristics(_wrap_head_and_body(head_markup=head))
    assert "json_ld" not in doc.raw_metadata


def test_json_ld_flattens_lists_graphs_and_ignores_scalars():
    """List payloads, @graph payloads, and scalar entries are flattened into dict rows."""
    list_payload = (
        '[{"@type": "Article", "headline": "Listed Headline"}, 42, '
        '{"@graph": [{"@type": "Person", "name": "Ignored"}, "skip"]}]'
    )
    doc = extract_html_heuristics(_wrap_head_and_body(head_markup=_json_ld_script(list_payload)))
    assert doc.title == "Listed Headline"
    assert len(doc.raw_metadata["json_ld"]) == 2


def test_json_ld_merges_first_article_and_keeps_existing_fields_for_later_articles():
    """Later article rows do not overwrite title, publication date, or updated date."""
    payload = (
        '[{"@type": ["schema:Thing", "https://schema.org/NewsArticle"], '
        '"headline": "First", "datePublished": "2020-01-02T10:00:00Z", '
        '"dateModified": "2020-02-03"},'
        '{"@type": "BlogPosting", "name": "Second", "dateCreated": "2021", '
        '"dateUpdated": "2021-05"},'
        '{"@type": "Report"},'
        '{"@type": 7, "headline": "Untyped"}]'
    )
    doc = extract_html_heuristics(_wrap_head_and_body(head_markup=_json_ld_script(payload)))
    assert doc.title == "First"
    assert doc.publication_date == "2020-01-02"
    assert doc.publication_date_raw == "2020-01-02T10:00:00Z"
    assert doc.updated_at == "2020-02-03"
    assert doc.layers.count("json_ld") == 1


def test_json_ld_author_shapes_string_dict_and_unusable_values():
    """Authors may be strings or dicts; scalars and nameless dicts contribute nothing."""
    payload = (
        '[{"@type": "Article", "headline": "String Author", "author": "Grace Hopper"},'
        '{"@type": "Article", "author": [{"givenName": "Alan"}, {"url": "x"}, 5, "  "]},'
        '{"@type": "Article", "author": {"familyName": "Shannon"}}]'
    )
    doc = extract_html_heuristics(_wrap_head_and_body(head_markup=_json_ld_script(payload)))
    names = [author["name"] for author in doc.authors]
    assert names == ["Grace Hopper", "Alan", "Shannon"]


def test_json_ld_author_names_helper_handles_each_value_shape():
    """The JSON-LD author name helper accepts strings and dicts only."""
    assert html_heuristics._json_ld_author_names("  ") == []
    assert html_heuristics._json_ld_author_names("Name One") == ["Name One"]
    assert html_heuristics._json_ld_author_names(None) == []
    assert html_heuristics._json_ld_author_names({"email": "a@b"}) == []
    assert html_heuristics._json_ld_types({}) == set()


def test_open_graph_does_not_override_existing_json_ld_values():
    """Open Graph values are ignored when JSON-LD already set title and dates."""
    head = _json_ld_script(
        '{"@type": "Article", "headline": "LD Title", "datePublished": "2019-01-01", '
        '"dateModified": "2019-02-02"}'
    ) + (
        '<meta property="og:title" content="OG Title">'
        '<meta property="article:published_time" content="2018-01-01">'
        '<meta property="article:modified_time" content="2018-02-02">'
    )
    doc = extract_html_heuristics(_wrap_head_and_body(head_markup=head))
    assert doc.title == "LD Title"
    assert doc.publication_date == "2019-01-01"
    assert doc.updated_at == "2019-02-02"
    assert not doc.authors


def test_open_graph_fills_fields_and_alternate_author_and_date_keys():
    """Open Graph provides title, alternate published time, modified time, and author."""
    head = (
        '<meta property="og:title" content="OG Only Title">'
        '<meta property="og:article:published_time" content="2022/03/04">'
        '<meta property="article:modified_time" content="2022-03-05T00:00:00Z">'
        '<meta property="og:article:author" content="Barbara Liskov">'
        '<meta property="og:unused" content="ignored">'
        '<meta content="no property">'
    )
    doc = extract_html_heuristics(_wrap_head_and_body(head_markup=head))
    assert doc.title == "OG Only Title"
    assert doc.publication_date == "2022-03-04"
    assert doc.updated_at == "2022-03-05"
    assert doc.authors[0]["name"] == "Barbara Liskov"
    assert "og:unused" not in doc.raw_metadata["open_graph"]


def test_twitter_card_supplies_title_and_creator_handle():
    """Twitter card title fills a missing title and the creator handle becomes an author."""
    head = (
        '<meta name="twitter:title" content="Tweet Title">'
        '<meta name="twitter:creator" content="@Ken Thompson">'
    )
    doc = extract_html_heuristics(_wrap_head_and_body(head_markup=head))
    assert doc.title == "Tweet Title"
    assert doc.authors[0]["name"] == "Ken Thompson"
    assert "twitter_card" in doc.layers


def test_twitter_card_without_creator_or_with_bare_at_sign_adds_no_author():
    """A missing creator or a creator of only "@" contributes no author."""
    without_creator = extract_html_heuristics(
        _wrap_head_and_body(head_markup='<meta name="twitter:card" content="summary">')
    )
    bare_handle = extract_html_heuristics(
        _wrap_head_and_body(head_markup='<meta name="twitter:creator" content="@">')
    )
    assert without_creator.authors == []
    assert without_creator.title is None
    assert bare_handle.authors == []


def test_twitter_merge_keeps_existing_title():
    """Twitter merge never replaces a title already present."""
    doc = HtmlHeuristicDocument(title="Existing")
    html_heuristics._merge_twitter(doc, {"twitter:title": "Other"})
    assert doc.title == "Existing"


def test_html_meta_supplies_date_author_and_title_fallback():
    """Dublin Core dates and the meta author fill missing fields."""
    head = (
        "<title>  </title>"
        '<meta name="author" content="Donald Knuth">'
        '<meta name="dc.date" content="1968">'
        '<meta name="citation_publication_date" content="1999-09-09">'
    )
    doc = extract_html_heuristics(_wrap_head_and_body(head_markup=head))
    assert doc.title is None
    assert doc.publication_date == "1968-01-01"
    assert doc.publication_date_raw == "1968"
    assert "html_meta" in doc.layers
    assert doc.authors[0]["name"] == "Donald Knuth"


def test_html_meta_date_does_not_override_existing_publication_date():
    """The meta date is ignored once a publication date exists."""
    doc = HtmlHeuristicDocument(publication_date="2000-01-01", layers=["html_meta"])
    html_heuristics._merge_html_meta(doc, {"meta_date": "1990"})
    assert doc.publication_date == "2000-01-01"
    other = HtmlHeuristicDocument(layers=["html_meta"])
    html_heuristics._merge_html_meta(other, {"meta_date": "1990-05"})
    assert other.publication_date == "1990-05-01"
    assert other.layers == ["html_meta"]


def test_html_meta_date_without_author_adds_html_meta_layer():
    """A meta date alone records the html_meta layer."""
    doc = extract_html_heuristics(
        _wrap_head_and_body(head_markup='<meta name="dcterms.created" content="2003-04">')
    )
    assert doc.publication_date == "2003-04-01"
    assert doc.layers == ["html_meta"]


def test_html_meta_extraction_without_title_element():
    """A page without a title element still extracts meta values."""
    soup = html_heuristics._build_soup(
        '<html><head><meta name="author" content="X Y"></head><body></body></html>'
    )
    assert html_heuristics._extract_html_meta(soup) == {"meta_author": "X Y"}


def test_byline_extraction_skips_empty_and_overlong_text():
    """Byline nodes with empty or overlong text are ignored."""
    overlong_text = "word " * 40
    body = (
        '<header><span class="byline"></span>'
        f'<div class="author">{overlong_text}</div>'
        '<p class="author">Edsger Dijkstra</p>'
        '<p class="other">Not a byline</p></header>'
    )
    doc = extract_html_heuristics(_wrap_head_and_body(body_markup=body))
    assert [author["name"] for author in doc.authors] == ["Edsger Dijkstra"]


def test_reference_section_skips_empty_items_and_foreign_lists():
    """Empty list items are skipped and lists owned by later headings are excluded."""
    body = (
        "<article><h2>References</h2>"
        "<ol><li> </li><li>Hopper, Grace. 1952. The Education of a Computer</li></ol>"
        "<h2>Other Section</h2><ul><li>Unrelated item here</li></ul>"
        "<h2></h2></article>"
    )
    doc = extract_html_heuristics(_wrap_head_and_body(body_markup=body))
    raws = [candidate["raw"] for candidate in doc.reference_candidates]
    assert raws == ["Hopper, Grace. 1952. The Education of a Computer"]
    assert doc.citations[0]["year"] == 1952
    assert "reference_section" in doc.layers


def test_link_candidates_skip_non_http_short_and_duplicate_anchors():
    """Non-http, short-text, and duplicate anchors are not link candidates."""
    soup = html_heuristics._build_soup(
        "<div>"
        '<a href="mailto:a@b.test">Mail the author</a>'
        '<a href="#section">Jump to section</a>'
        '<a href="https://external.test/a">ab</a>'
        '<a href="https://external.test/a">External Paper</a>'
        '<a href="https://external.test/a">External Paper</a>'
        '<a href="https://source.test/self">Same host link</a>'
        "</div>"
    )
    candidates = html_heuristics._extract_link_candidates_from_node(
        soup.find("div"),
        source_uri="https://source.test/page",
        source_label="footer_links",
    )
    assert [candidate["url"] for candidate in candidates] == ["https://external.test/a"]


def test_footer_element_links_add_footer_layers():
    """A footer element contributes footer_element and footer_links layers."""
    body = (
        "<p>Intro</p>"
        '<footer><a href="https://elsewhere.test/paper">Elsewhere Paper Title</a></footer>'
    )
    doc = extract_html_heuristics(
        _wrap_head_and_body(body_markup=body), source_uri="https://home.test/post"
    )
    assert "footer_element" in doc.layers
    assert "footer_links" in doc.layers
    assert doc.links[0]["href"] == "https://elsewhere.test/paper"


def test_normalize_reference_candidates_skips_invalid_empty_and_duplicate_titles():
    """Non-dict, empty, and duplicate-title candidates are dropped."""
    rows = html_heuristics._normalize_reference_candidates(
        [
            "not-a-dict",
            {"raw": "", "title": ""},
            {"raw": "Doe, J. 2001. Title One doi 10.1234/abcd", "source": "reference_section"},
            {"raw": "doe, j. 2001. title one doi 10.1234/abcd"},
        ]
    )
    assert len(rows) == 1
    assert rows[0]["doi"] == "10.1234/abcd"
    assert rows[0]["candidate_source"] == "reference_section"


def test_dedupe_reference_candidates_skips_keyless_and_repeated_entries():
    """Candidates without url or raw text, and repeated keys, are removed."""
    deduped = html_heuristics._dedupe_reference_candidates(
        [
            {"raw": "", "url": ""},
            {"raw": "Line", "url": "https://a.test"},
            {"raw": "Other", "url": "https://A.test"},
            {"raw": "Raw only"},
        ]
    )
    assert [candidate["raw"] for candidate in deduped] == ["Line", "Raw only"]


def test_merge_authors_splits_conjunctions_and_skips_blank_names():
    """Names joined by "and" are split, blanks ignored, and empty input adds no layer."""
    doc = HtmlHeuristicDocument()
    html_heuristics._merge_authors(doc, ["  ", "Ada Lovelace and Charles Babbage"], layer="x")
    assert [author["name"] for author in doc.authors] == ["Ada Lovelace", "Charles Babbage"]
    assert doc.layers == ["x"]
    html_heuristics._merge_authors(doc, [" "], layer="y")
    assert doc.layers == ["x"]


def test_guess_title_from_reference_line_variants():
    """Title guessing handles empty, sentence-split, and single-segment lines."""
    assert html_heuristics._guess_title_from_reference_line(" ") == ""
    assert (
        html_heuristics._guess_title_from_reference_line("Doe, J. 2020. A Long Enough Title")
        == "A Long Enough Title"
    )
    assert html_heuristics._guess_title_from_reference_line("Single segment") == "Single segment"


def test_guess_authors_from_reference_line_variants():
    """Author guessing handles empty, long, et al, comma, conjunction, and bare heads."""
    assert html_heuristics._guess_authors_from_reference_line("") == []
    assert html_heuristics._guess_authors_from_reference_line("x" * 130 + ". Title") == []
    assert html_heuristics._guess_authors_from_reference_line("Smith et al. Title") == ["Smith"]
    assert html_heuristics._guess_authors_from_reference_line("Smith, Jones. Title") == [
        "Smith",
        "Jones",
    ]
    assert html_heuristics._guess_authors_from_reference_line("Smith and Jones. Title") == [
        "Smith",
        "Jones",
    ]
    assert html_heuristics._guess_authors_from_reference_line("Solo. Title") == ["Solo"]
    assert html_heuristics._guess_authors_from_reference_line("X. Title") == []


def test_resolve_href_variants():
    """Hrefs resolve to None for fragments, pass through absolute, and join relative."""
    assert html_heuristics._resolve_href("", "") is None
    assert html_heuristics._resolve_href("#top", "") is None
    assert html_heuristics._resolve_href("http://a.test/x", "") == "http://a.test/x"
    assert html_heuristics._resolve_href("/x", "https://b.test/y") == "https://b.test/x"
    assert html_heuristics._resolve_href("relative/x", "") == "relative/x"


def test_normalize_date_token_variants():
    """Date tokens normalize to ISO days, or None when unrecognized."""
    assert html_heuristics._normalize_date_token("") is None
    assert html_heuristics._normalize_date_token("2020-01-02T03:04:05Z") == "2020-01-02"
    assert html_heuristics._normalize_date_token("2020/01") == "2020-01-01"
    assert html_heuristics._normalize_date_token("2020") == "2020-01-01"
    assert html_heuristics._normalize_date_token("January 2020") is None


def test_normalize_person_name_and_first_non_empty_helpers():
    """Person names normalize family-first, and first_non_empty returns empty when none."""
    assert html_heuristics._normalize_person_name("  ") == ""
    assert html_heuristics._normalize_person_name("Plato") == "plato"
    assert html_heuristics._normalize_person_name("Ada King Lovelace") == "lovelace ada king"
    assert html_heuristics._first_non_empty([None, " ", "x"]) == "x"
    assert html_heuristics._first_non_empty([None, ""]) == ""


def test_heuristic_document_to_structured_counts_identifier_citations():
    """Structured output counts citations that carry any identifier."""
    doc = HtmlHeuristicDocument(
        citations=[{"doi": "10.1/x"}, {"title": "no ids"}],
        reference_candidates=[{}, {}],
    )
    structured = heuristic_document_to_structured(doc)
    assert structured["summary"]["citations_with_identifiers"] == 1
    assert structured["summary"]["reference_candidates_count"] == 2
