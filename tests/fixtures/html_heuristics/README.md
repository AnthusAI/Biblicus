# HTML heuristic extraction fixtures

All HTML files in this directory are **original synthetic documents** written for
Biblicus tests, or **minimal structural snippets** created for this repository.

## License

The files in this directory are released under the **MIT License** (same as Biblicus).
You may copy and adapt them freely in other open-source projects.

They intentionally avoid reproducing full text from third-party articles, blogs, or
paywalled publishers. They model common real-world markup patterns (JSON-LD,
Open Graph, reference lists, footer links) without embedding copyrighted prose.

## Files

| File | What it exercises |
|------|-------------------|
| `synthetic_blog_json_ld.html` | `BlogPosting` JSON-LD, author, date, References list |
| `synthetic_news_open_graph.html` | Open Graph / `article:*` meta tags |
| `synthetic_references_only.html` | Bibliography `<h2>References</h2>` + `<ol>` |
| `synthetic_footer_links.html` | External links in page footer |
| `synthetic_sparse.html` | Minimal HTML with almost no metadata (LLM/heuristic gap case) |
| `synthetic_citations_weak.html` | Reference list without years/DOIs (partial heuristic + LLM merge) |
