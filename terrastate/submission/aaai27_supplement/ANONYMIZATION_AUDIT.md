# Supplement Anonymization Audit

Status: **PASS**

Scope: `supplementary.tex` and the compiled `supplementary.pdf`.

- Visible author: `Anonymous Submission`.
- PDF metadata author: empty.
- No author name, affiliation, laboratory, email, acknowledgment, personal
  link, account, host name, job identifier, token, credential, or private
  filesystem path was found.
- No old public method name or internal development-stage narrative was found.
- No excluded checkpoint or experiment identifier was found.
- No training seed, training-repetition commentary, author identity, or
  server-specific implementation detail appears in the PDF.
- The title exactly matches the submitted paper title.
- The added Q3 matching definition contains only frozen protocol quantities
  and introduces no local path, account, host, or dataset pointer.
- The PDF uses the compact A--D appendix structure and contains no uploaded
  checkpoint, data, private download link, or figure.
- The only files intended for upload are the PDF and the separate ZIP; local
  fact-freeze, QA, audit, and Chinese-review files are excluded.

Method: source scan, extracted-PDF-text scan, metadata inspection, and visual
inspection of every rendered page.
