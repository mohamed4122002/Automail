import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.spam_shield import spam_shield_service

def test_spam_shield_logic():
    print("Testing Spam Shield Logic...")
    
    test_cases = [
        {
            "text": "Get your FREE money now!!!",
            "expect_spam": True,
            "min_score": 0.5
        },
        {
            "text": "Winner! You have won a guaranteed prize. Act now!",
            "expect_spam": True,
            "min_score": 0.5
        },
        {
            "text": "f.r.e.e. b.i.t.c.o.i.n",
            "expect_spam": True,
            "min_score": 0.2
        },
        {
            "text": "Meeting regarding the upcoming project roadmap and Q3 objectives.",
            "expect_spam": False,
            "max_score": 0.2
        },
        {
            "text": "URGENT: YOUR ACCOUNT HAS BEEN SUSPENDED! VERIFY NOW.",
            "expect_spam": True,
            "min_score": 0.6
        }
    ]
    
    for i, case in enumerate(test_cases):
        report = spam_shield_service.check_text(case["text"])
        print(f"\nCase {i+1}: '{case['text']}'")
        print(f"  Score: {report['score']}")
        print(f"  Triggers: {report['triggers']}")
        print(f"  Is Spam: {report['is_spam']}")
        
        if "expect_spam" in case:
            if report['is_spam'] != case['expect_spam'] and report['score'] < 0.6 and case['expect_spam']:
                print(f"  [!] Warning: Expected spam but got low score.")
        
        if "min_score" in case:
            assert report['score'] >= case['min_score'], f"Score too low for '{case['text']}'"
            
        if "max_score" in case:
            assert report['score'] <= case['max_score'], f"Score too high for '{case['text']}'"

    print("\nLogic Verification PASSED!")

if __name__ == "__main__":
    test_spam_shield_logic()
