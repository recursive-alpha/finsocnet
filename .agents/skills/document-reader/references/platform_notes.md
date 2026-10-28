# Document Reader — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- PyMuPDF `page.get_text()`
- ebooklib chapters
- python-docx paragraphs
- ocrmypdf --skip-text

## Verify in the Phase spike

- [ ] OCR speed on a 300-page scanned book

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Verified by tests with generated PDF, DOCX, EPUB, HTML, MD and audio (fake Whisper) files. OCR needs the optional `ocr` extra (`ocrmypdf`); without it, text-less pages are counted in `extra.empty_pages`.
