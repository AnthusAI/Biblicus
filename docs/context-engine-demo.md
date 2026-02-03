Context Engine Demo (Biblicus)
==============================

This walkthrough exercises the Biblicus Context engine directly using the
WikiText2 fixture corpus, demonstrating compaction, expansion, and explicit
message control.

Run
---

```bash
conda run -n py311 --no-capture-output python scripts/demo_context_engine.py
```

Example output (abridged)
-------------------------

```
Context Engine Demo (Biblicus)
==============================
WikiText fixture ready

Corpus snapshot
===============
1. = Valkyria Chronicles III =
2. Senjo no Valkyria 3 : Unrecorded Chronicles ( Japanese : ... )
3. The game began development in 2010 , carrying over a large portion of the work done on Valkyria Chronicles II . While it retained the sta...
4. It met with positive sales in Japan , and was praised by both Japanese and western critics . After release , it received downloadable con...
5. = = Gameplay = =

Direct retrieval
================
Evidence count: 2
- train-1: Concept work for Valkyria Chronicles III began after development finished on Valkyria Chronicles II in early 2010 , with full development beginning shortly a...
- train-2: The majority of material created for previous games , such as the BLiTZ system and the design of maps , was carried over . Alongside this , improvements were...

Dual concept retrieval (full corpus)
====================================
Query (gaming): Valkyria Chronicles III
- train-1: Concept work for Valkyria Chronicles III began after development finished on Valkyria Chronicles II in early 2010 , with full development...
Query (geopolitics): United States
- train-1: " Crazy in Love " was released to radio in the United States on May 18 , 2003 under formats including Rhythmic , Top 40 , and Urban radio...

Default context assembly
========================
Context: default_context
Token estimate: 51
System prompt:
You are a support agent.

Concept work for Valkyria Chronicles III began after development finished on Valkyria Chronicles II in early 2010 , with full development beginning shortly after this . The director of Valkyria Chronicles II , Takeshi Ozawa , returned to that role for Valkyria Chronicles III . Develop...

Explicit context assembly with history
======================================
Context: explicit_context
Token estimate: 63
System prompt:
You are a researcher.

Concept work for Valkyria Chronicles III began after development finished on Valkyria Chronicles II in early 2010 , with full development beginning shortly after this . The director of Valkyria Chronicles II , Takeshi Ozawa , returned to that role for Valkyria Chronicles III . Develop...
History:
- user: What is Valkyria Chronicles?
- assistant: It is a tactical RPG series.
User message:
Summarize the evidence.

Expansion and pagination
========================
Offsets requested: [0, 1, 2]
Context: expanding_context
Token estimate: 365
System prompt:
Evidence:

A lookout aboard Weehawken spotted Atlanta at 04 : 10 on the morning of 17 June . When the latter ship closed to within about 1 @.@ 5 miles ( 2 @.@ 4 km ) of the two Union ships , she fired one round from her bow gun that passed over Weehawken and landed near Nahant . Shortly afterward , Atlanta ran aground on a sandbar ; she was briefly able to free herself , but the pressure of the...
User message:
Give highlights.

Regeneration and compaction
===========================
Pack budgets: [80, 20]
Context: compact_context
Token estimate: 18
System prompt:
Evidence: Please summarize the evidence with precision.

Concept work for...
User message:
Summarize quickly and focus on the key facts.
```

Notes
-----

- The output is abridged to keep the demo readable.
- The full output is reproducible by running the script above.
