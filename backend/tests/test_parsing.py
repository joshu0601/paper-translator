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
