from app.services.search.query_understanding import parse_query

def test_parse_query_with_in():
    res = parse_query("Cardiologists in Birmingham")
    assert res["category"] == "Cardiologists"
    assert res["location"] == "Birmingham"

def test_parse_query_with_near():
    res = parse_query("Dentists near Austin")
    assert res["category"] == "Dentists"
    assert res["location"] == "Austin"

def test_parse_query_capitalized_prefix():
    res = parse_query("Birmingham plumbers")
    assert res["category"] == "plumbers"
    assert res["location"] == "Birmingham"

def test_parse_query_capitalized_suffix():
    res = parse_query("cardiologists Birmingham")
    assert res["category"] == "cardiologists"
    assert res["location"] == "Birmingham"

def test_parse_query_fallback():
    res = parse_query("plumbers")
    assert res["category"] == "plumbers"
    assert res["location"] is None
