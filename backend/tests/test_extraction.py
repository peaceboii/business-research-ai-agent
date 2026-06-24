from app.utils.extraction_utils import extract_phone_from_text, extract_address_from_text

def test_extract_phone_us():
    assert extract_phone_from_text("Call us at (205) 555-0199 or email") == "(205) 555-0199"
    assert extract_phone_from_text("Phone: 1-800-431-7201") == "1-800-431-7201"
    assert extract_phone_from_text("Mobile +1-512-451-8310") == "+1-512-451-8310"

def test_extract_phone_india():
    assert extract_phone_from_text("Contact 9876543210 for details") == "9876543210"
    assert extract_phone_from_text("Landline +91 44 2815 1234") == "+91 44 2815 1234"

def test_extract_phone_negative():
    # Should not match random numbers/dates
    assert extract_phone_from_text("Date: 2026-06-24") is None
    assert extract_phone_from_text("Total candidates: 123") is None

def test_extract_address_us():
    text = "We are located at 1201 San Jacinto Blvd, Austin, TX 78701 in the city center."
    assert extract_address_from_text(text) == "1201 San Jacinto Blvd, Austin, TX 78701"
    
    # Address without zip code
    text_no_zip = "Our office is 1201 San Jacinto Blvd, Austin, TX. Welcome!"
    assert extract_address_from_text(text_no_zip) == "1201 San Jacinto Blvd, Austin, TX"

def test_extract_address_markers():
    text = "Address: 7517 Price Burgs Road, Birmingham"
    assert extract_address_from_text(text) == "7517 Price Burgs Road, Birmingham"
    
    text_colony = "Shop 12, Anna Nagar, Chennai 600040"
    assert extract_address_from_text(text_colony) == "12, Anna Nagar, Chennai 600040"

def test_extract_address_negative():
    assert extract_address_from_text("Our top dentists are available 24/7.") is None
    assert extract_address_from_text("Click here to buy rent or sell space.") is None
