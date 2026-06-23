from app.services.verifiers.verifier import global_verification_engine
from app.services.search.adapters.base import RawBusinessCandidate

def test_verify_and_merge_no_conflict():
    c1 = RawBusinessCandidate(
        name="ABC Heart",
        phone="205-111-2222",
        website="http://abcheart.com",
        address="123 Main St",
        source_name="yelp",
        source_url="http://yelp.com/abc"
    )
    c2 = RawBusinessCandidate(
        name="ABC Heart Clinic",
        phone="205-111-2222",
        website="http://abcheart.com",
        address="123 Main St Suite A",
        source_name="yellowpages",
        source_url="http://yellowpages.com/abc"
    )
    
    merged, conflicts = global_verification_engine.verify_and_merge([c1, c2])
    
    assert merged["business_name"] == "ABC Heart Clinic"  # longest name preferred
    assert merged["phone"] == "(205) 111-2222"
    assert merged["website"] == "http://abcheart.com"
    # Merged address choice based on source weights or presence (Suite A is longest/first)
    assert merged["address"] is not None
    assert len(conflicts) == 1  # address differs ("123 Main St" vs "123 Main St Suite A")
    assert merged["verification_score"] > 80.0  # highly verified phone/web

def test_verify_and_merge_with_conflict():
    c1 = RawBusinessCandidate(
        name="ABC Heart",
        phone="205-111-2222",
        website="http://abcheart.com",
        source_name="yelp",
        source_url="http://yelp.com/abc"
    )
    c2 = RawBusinessCandidate(
        name="ABC Heart",
        phone="205-999-9999",
        website="http://abcheart.com",
        source_name="yellowpages",
        source_url="http://yellowpages.com/abc"
    )
    
    # Also pass official website details (weight 100)
    web_details = {
        "phone": "205-111-2222",
        "email": "info@abcheart.com"
    }
    
    merged, conflicts = global_verification_engine.verify_and_merge([c1, c2], web_details)
    
    # The phone from website/yelp (205-111-2222) has higher reliability weight sum than yellowpages
    assert merged["phone"] == "(205) 111-2222"
    assert merged["email"] == "info@abcheart.com"
    
    # Conflict should be tracked
    phone_conflict = next(c for c in conflicts if c["field_name"] == "phone")
    assert "(205) 111-2222" in phone_conflict["conflicting_values"]
    assert "(205) 999-9999" in phone_conflict["conflicting_values"]
