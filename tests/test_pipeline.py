from src.enrichment import extract_valid_email
from src.personalizer import _surgical_word_bound_enforcer, count_words

def test_email_extraction_and_false_positives():
    assert extract_valid_email("Contact me at hello [at] creator [dot] io for collabs") == "hello@creator.io"
    assert extract_valid_email("Install via npm i react@18.2.0 or image@2x.png") == "Not Found"

def test_word_count_bounds_enforcer():
    short_text = "Hi Alex, loved your video on Python agents. Best, NexusAI Team"
    enforced_email = _surgical_word_bound_enforcer(short_text, 64, 86, "Best, NexusAI Team")
    assert 60 <= count_words(enforced_email) <= 90

    long_dm = " ".join(["word"] * 45)
    enforced_dm = _surgical_word_bound_enforcer(long_dm, 17, 28, "Open to chat?")
    assert 15 <= count_words(enforced_dm) <= 30

if __name__ == "__main__":
    test_email_extraction_and_false_positives()
    test_word_count_bounds_enforcer()
    print("All pipeline unit tests passed!")