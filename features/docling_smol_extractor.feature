Feature: DoclingSmol extractor plugin
  The DoclingSmol extractor uses the SmolDocling-256M vision-language model for document understanding.

  Scenario: DoclingSmol extractor requires an optional dependency
    Given I initialized a corpus at "corpus"
    And the Docling dependency is unavailable
    And a Portable Document Format file "hello.pdf" exists with text "Hello"
    When I ingest the file "hello.pdf" into corpus "corpus"
    And I attempt to build a "docling-smol" extraction run in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "biblicus[docling]"

  Scenario: DoclingSmol extractor requires MLX backend when configured
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available without MLX support
    And a Portable Document Format file "hello.pdf" exists with text "Hello"
    When I ingest the file "hello.pdf" into corpus "corpus"
    And I attempt to build a "docling-smol" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: docling-smol
      config:
        backend: mlx
      """
    Then the command fails with exit code 2
    And standard error includes "biblicus[docling-mlx]"

  Scenario: DoclingSmol extractor skips text items
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available
    When I ingest the text "alpha" with title "Alpha" and tags "a" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus"
    Then the extraction run does not include extracted text for the last ingested item

  Scenario: DoclingSmol extractor skips Markdown items
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available
    And a file "doc.md" exists with contents "# Hello"
    When I ingest the file "doc.md" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus"
    Then the extraction run does not include extracted text for the last ingested item

  Scenario: DoclingSmol extractor skips audio items
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available
    And a binary file "audio.mp3" exists
    When I ingest the file "audio.mp3" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus"
    Then the extraction run does not include extracted text for the last ingested item

  Scenario: DoclingSmol extractor produces extracted text for a PDF
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available that returns text "Extracted by Docling" for filename "doc.pdf"
    And a Portable Document Format file "doc.pdf" exists with text "Original"
    When I ingest the file "doc.pdf" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus"
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "Extracted by Docling"
    And the extraction run item provenance uses extractor "docling-smol"

  Scenario: DoclingSmol extractor produces extracted text for DOCX
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available that returns text "DOCX content" for filename "doc.docx"
    And a binary file "doc.docx" exists
    When I ingest the file "doc.docx" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "DOCX content"

  Scenario: DoclingSmol extractor produces extracted text for XLSX
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available that returns text "XLSX content" for filename "data.xlsx"
    And a binary file "data.xlsx" exists
    When I ingest the file "data.xlsx" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "XLSX content"

  Scenario: DoclingSmol extractor produces extracted text for PPTX
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available that returns text "PPTX content" for filename "slides.pptx"
    And a binary file "slides.pptx" exists
    When I ingest the file "slides.pptx" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "PPTX content"

  Scenario: DoclingSmol extractor produces extracted text for HTML
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available that returns text "HTML content" for filename "page.html"
    And a text file "page.html" exists with contents "<html><body>Test</body></html>"
    When I ingest the file "page.html" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "HTML content"

  Scenario: DoclingSmol extractor produces extracted text for PNG images
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available that returns text "Image text" for filename "scan.png"
    And a binary file "scan.png" exists
    When I ingest the file "scan.png" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "Image text"

  Scenario: DoclingSmol extractor produces extracted text for JPEG images
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available that returns text "JPEG text" for filename "photo.jpg"
    And a binary file "photo.jpg" exists
    When I ingest the file "photo.jpg" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "JPEG text"

  Scenario: DoclingSmol extractor produces extracted text for uncommon image types
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available that returns text "SVG text" for filename "image.svg"
    And a binary file "image.svg" exists
    When I ingest the file "image.svg" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "SVG text"

  Scenario: DoclingSmol extractor records empty output when it cannot extract text
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available that returns empty output for filename "empty.pdf"
    And a Portable Document Format file "empty.pdf" exists with no extractable text
    When I ingest the file "empty.pdf" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item is empty
    And the extraction run stats include extracted_empty_items 1

  Scenario: DoclingSmol extractor records per-item errors and continues
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available that raises a RuntimeError for filename "boom.pdf"
    And a Portable Document Format file "boom.pdf" exists with text "will error"
    And a fake Docling library is available that returns text "ok" for filename "ok.pdf"
    And a Portable Document Format file "ok.pdf" exists with text "good"
    When I ingest the file "boom.pdf" into corpus "corpus"
    And I ingest the file "ok.pdf" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "ok"
    And the extraction run includes an errored result for the first ingested item
    And the extraction run error type for the first ingested item equals "RuntimeError"
    And the extraction run stats include errored_items 1

  Scenario: DoclingSmol extractor uses transformers backend when configured
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available with transformers backend that returns text "Transformers output" for filename "doc.pdf"
    And a Portable Document Format file "doc.pdf" exists with text "Test"
    When I ingest the file "doc.pdf" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: docling-smol
      config:
        backend: transformers
      """
    Then the extracted text for the last ingested item equals "Transformers output"

  Scenario: DoclingSmol extractor outputs HTML when configured
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available that returns HTML "<p>Content</p>" for filename "doc.pdf"
    And a Portable Document Format file "doc.pdf" exists with text "Test"
    When I ingest the file "doc.pdf" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: docling-smol
      config:
        output_format: html
      """
    Then the extracted text for the last ingested item equals "<p>Content</p>"

  Scenario: DoclingSmol extractor outputs plain text when configured
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available that returns plain text "Plain content" for filename "doc.pdf"
    And a Portable Document Format file "doc.pdf" exists with text "Test"
    When I ingest the file "doc.pdf" into corpus "corpus"
    And I build a "docling-smol" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: docling-smol
      config:
        output_format: text
      """
    Then the extracted text for the last ingested item equals "Plain content"

  Scenario: DoclingSmol extractor rejects invalid output format
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available
    And a Portable Document Format file "doc.pdf" exists with text "Test"
    When I ingest the file "doc.pdf" into corpus "corpus"
    And I attempt to build a "docling-smol" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: docling-smol
      config:
        output_format: invalid
      """
    Then the command fails with exit code 2

  Scenario: DoclingSmol extractor rejects invalid backend
    Given I initialized a corpus at "corpus"
    And a fake Docling library is available
    And a Portable Document Format file "doc.pdf" exists with text "Test"
    When I ingest the file "doc.pdf" into corpus "corpus"
    And I attempt to build a "docling-smol" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: docling-smol
      config:
        backend: invalid
      """
    Then the command fails with exit code 2
