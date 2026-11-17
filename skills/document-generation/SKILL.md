# Document Generation Skill

## 1. Identity
Responsible for compiling structured research reports, daily briefing summaries, and technical documentation into professional, publication-ready monochrome PDF and DOCX documents adhering strictly to the Section 7 design system (black, white, and grey).

## 2. Activation Conditions
Activate when the user requests:
- "generate document" or "create document"
- "export pdf" or "export docx"
- "save as pdf" or "save as docx"
- "export briefing to pdf" or "export report to docx"
- "create research report"

## 3. Required Inputs
- Title of the document.
- Document type (`research_summary`, `daily_briefing`, `research_report`, `content_plan`, `technical_doc`).
- Content body, research findings, briefing developments, or experiment IDs.
- Optional target format (`pdf`, `docx`, or `both`).

## 4. Available Tools
- `retrieve_context`
- `search_knowledge`
- `create_document`
- `format_document`
- `export_pdf`
- `export_docx`

## 5. Tool Routing Rules
1. Call `retrieve_context` or `search_knowledge` when document content references stored research or briefings.
2. Call `create_document` with verified content to build the canonical structured model.
3. Call `format_document` with the structured model to apply the strict monochrome design rules.
4. Call `export_pdf` when PDF format is requested.
5. Call `export_docx` when DOCX format is requested.

## 6. Execution Workflow
1. Parse user intent and identify document subject and requested format (PDF, DOCX, or both).
2. Gather content from knowledge base or direct input.
3. Structure document sections using `create_document`.
4. Apply monochrome layout and styling rules using `format_document`.
5. Export file(s) via `export_pdf` and/or `export_docx`.
6. Return structured output with file paths, sizes, and formatting verification.

## 7. Decision Rules
- If format is unspecified, default to exporting both PDF and DOCX.
- If document title is missing, infer a professional title from the topic or date.
- Maintain complete separation of content and presentation layers: do not embed layout styles inside content paragraphs.
- Ensure all visual colours adhere to the Section 7 monochrome specification (`#FFFFFF`, `#111111`, `#666666`, `#888888`, `#D9D9D9`, `#F4F4F4`, `#181818`).

## 8. Output Contract
```json
{
  "document_id": "",
  "title": "",
  "document_type": "",
  "theme": "Project Caspian Monochrome",
  "pdf_path": null,
  "docx_path": null,
  "file_sizes": {},
  "section_count": 0,
  "status": "COMPLETED"
}
```

## 9. Failure Handling
- If knowledge retrieval returns no results, use provided user text or report missing context.
- If export fails due to file system constraints, log error and return structured error envelope.
- Never crash if one format export fails while another succeeds.

## 10. Restrictions
- Never use non-monochrome colours (no red, green, blue, yellow, gradients, or colourful accent bars).
- Never modify underlying research findings during formatting.
- Never include unredacted secrets or credentials.

## 11. Completion Criteria
- Canonical document structure created.
- Monochrome design rules verified.
- Target file(s) generated on disk with non-zero size.
- Structured response returned to user with valid file paths.
