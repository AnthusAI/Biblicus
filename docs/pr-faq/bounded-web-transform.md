# Bounded web transformation PR-FAQ

Biblicus supplies the missing text transformation commands for the already-authorized Papyrus URL-only importer. An integration can select source-grounded article passages and generate a title, subtitle, and summary through its trusted host gateway.

Why Biblicus? It already owns URL conversion and text transformation; Papyrus continues to orchestrate intake without copying extraction logic. These commands accept already-extracted text and never fetch the source URI or run converters.

How is spending bounded? Article selection uses one request; each metadata field uses one map and one reduce request. The full workflow needs seven requests. The trusted gateway admits each request, counts tokens, and handles cancellation. Workers never retry or discover credentials.

What is excluded? Source fetching changes, classification labels, tools, deployments, live grants, paid validation, and changes to the existing paper/GROBID path.

Approval basis: parent explicitly authorized implementing this missing dependency end to end; this draft records that existing scope, not a request for new product scope.
