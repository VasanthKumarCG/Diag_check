from src.rag.text import chunk_text, build_search_text

def test_chunking_preserves_content():
    text="Sentence one. Sentence two. Sentence three."
    chunks=chunk_text(text,max_chars=25,overlap_chars=0)
    assert len(chunks)>=2
    assert "Sentence one." in " ".join(chunks)

def test_query_contains_core_context():
    q=build_search_text({"sw_release":"R1","primary_ecu":"UCAP-10","related_ecus":["BCP"],"dtc_codes":["U010000"],"observed_symptoms":"Lost communication"})
    assert "UCAP-10" in q and "U010000" in q and "R1" in q
