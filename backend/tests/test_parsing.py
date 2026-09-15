from app.services.demo import AUTHORS, TITLE, build_demo_pdf
from app.services.parsing import classify_section, parse
from app.services.pdf import extract


def test_classify_section():
    assert classify_section("Introduction") == "introduction"
    assert classify_section("Related Work") == "related_work"
    assert classify_section("Experimental Results") == "experiment"
    assert classify_section("Conclusion and Future Work") == "conclusion"
    assert classify_section("REFERENCES") == "references"
    assert classify_section("Some Custom Heading") == "other"


def test_table_caption_chain_stops_at_prose():
    from app.services.parsing.structure import _table_cell_blocks
    from app.services.pdf.extractor import Block

    def block(y0, y1, text):
        return Block(page=4, bbox=(307, y0, 527, y1), text=text, font_size=10, bold_ratio=0, char_count=len(text))

    caption = block(60, 72, "Table 1: Number of questions in each QA dataset.")
    header = block(75, 86, "Dataset Train Dev Test")
    row1 = block(88, 99, "NQ 79,168 8,757 3,610")
    row2 = block(101, 112, "TriviaQA 78,785 8,837 11,313")
    prose = block(116, 400, "as well as various Web sources and is intended for open-domain QA from unstructured corpora. "
                            "SQuAD v1.1 is a popular benchmark dataset for reading comprehension. " * 4)
    cells = _table_cell_blocks([caption, header, row1, row2, prose], [])
    assert {id(header), id(row1), id(row2)} <= cells
    assert id(prose) not in cells


def test_demo_pdf_structure():
    extracted = extract(build_demo_pdf())
    assert extracted.page_count >= 3
    parsed = parse(extracted)

    assert parsed.title == TITLE
    assert parsed.authors == [a.strip() for a in AUTHORS.replace("and ", "").split(",")]
    assert parsed.abstract and parsed.abstract.startswith("Mobile Edge Computing")

    kinds = [s.kind for s in parsed.sections]
    for expected in ("abstract", "introduction", "related_work", "conclusion", "references"):
        assert expected in kinds

    numbered = [s.number for s in parsed.sections if s.number]
    assert numbered == ["1", "2", "3", "4", "5", "6", "7"]

    intro = next(s for s in parsed.sections if s.kind == "introduction")
    assert len(intro.paragraphs) == 3  # paragraph merging must not glue paragraphs together

    refs = next(s for s in parsed.sections if s.kind == "references")
    assert len(refs.paragraphs) == 8 and all(p.kind == "reference" for p in refs.paragraphs)

    captions = [p for s in parsed.sections for p in s.paragraphs if p.kind == "caption"]
    assert len(captions) == 3
    assert [f.label for f in parsed.figures] == ["Figure 1"]
    assert any(t.label == "Table 1" for t in parsed.tables)
