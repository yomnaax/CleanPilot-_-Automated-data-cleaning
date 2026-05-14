"""
Test script for Regex Pattern Extractor.

Run this to test the regex extractor with a sample dataset.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.rule_extractor.regex_extractor import RegexExtractor
from app.db import models
from app.db.base import SessionLocal
import pandas as pd


def create_test_dataset():
    """Create a test CSV file with various patterns."""
    test_data = {
        "email": [
            "john.doe@example.com",
            "jane.smith@test.org",
            "user123@domain.co.uk",
            "admin@company.com",
            "contact@website.net"
        ],
        "phone": [
            "+1-555-123-4567",
            "(555) 987-6543",
            "555-111-2222",
            "+44 20 7946 0958",
            "555.333.4444"
        ],
        "date_iso": [
            "2024-01-15",
            "2024-02-20",
            "2024-03-10",
            "2024-04-05",
            "2024-05-25"
        ],
        "date_us": [
            "01/15/2024",
            "02/20/2024",
            "03/10/2024",
            "04/05/2024",
            "05/25/2024"
        ],
        "url": [
            "https://www.example.com",
            "http://test.org/page",
            "https://subdomain.example.com/path",
            "http://localhost:8000",
            "https://api.example.com/v1"
        ],
        "zipcode": [
            "12345",
            "90210",
            "10001-1234",
            "60601",
            "02134"
        ],
        "mixed_text": [
            "Some random text",
            "Another string",
            "Not a pattern",
            "Just words here",
            "More text"
        ],
        "numbers": [
            "12345",
            "67890",
            "11111",
            "99999",
            "00000"
        ]
    }
    
    df = pd.DataFrame(test_data)
    test_file = Path(__file__).parent.parent / "data" / "storage" / "test_regex_patterns.csv"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(test_file, index=False)
    print(f"✅ Created test dataset: {test_file}")
    return str(test_file)


def test_regex_extractor_direct():
    """Test the regex extractor directly without database."""
    print("\n" + "="*60)
    print("Testing Regex Extractor (Direct)")
    print("="*60)
    
    # Create test dataset
    test_file = create_test_dataset()
    
    # Create a mock dataset object
    class MockDataset:
        def __init__(self):
            self.id = 999
            self.modality = models.Modality.TABULAR
            self.storage_path = test_file
    
    dataset = MockDataset()
    
    # Test extractor
    extractor = RegexExtractor(min_match_ratio=0.8)
    rules = extractor.extract(dataset)
    
    # Display results
    print(f"\n📊 Extracted {len(rules)} rules:\n")
    for i, rule in enumerate(rules, 1):
        print(f"Rule {i}:")
        print(f"  Column: {rule['targets']['columns'][0]}")
        print(f"  Pattern: {rule['predicate']}")
        print(f"  Action: {rule['action']}")
        print(f"  Confidence: {rule['confidence']:.2f}")
        print(f"  Explanation: {rule['explanation']}")
        print()
    
    # Verify expected patterns
    expected_patterns = ["email", "phone", "date_iso", "date_us", "url", "zipcode"]
    found_patterns = [rule['targets']['columns'][0] for rule in rules]
    
    print("✅ Expected patterns found:")
    for pattern in expected_patterns:
        if pattern in found_patterns:
            print(f"  ✓ {pattern}")
        else:
            print(f"  ✗ {pattern} (not found)")
    
    return rules


def test_regex_extractor_with_db():
    """Test the regex extractor with actual database."""
    print("\n" + "="*60)
    print("Testing Regex Extractor (With Database)")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # Create test dataset file
        test_file = create_test_dataset()
        
        # Create dataset in database
        dataset = models.Dataset(
            name="Test Regex Patterns",
            purpose=models.DatasetPurpose.RULE_EXTRACTION,
            modality=models.Modality.TABULAR,
            domain=models.Domain.GENERAL,
            storage_path=test_file
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        print(f"✅ Created dataset in DB: ID={dataset.id}, Name={dataset.name}")
        
        # Extract rules
        extractor = RegexExtractor()
        rules = extractor.extract(dataset)
        
        print(f"\n📊 Extracted {len(rules)} rules")
        
        # Display results
        for i, rule in enumerate(rules, 1):
            print(f"\nRule {i}:")
            print(f"  Column: {rule['targets']['columns'][0]}")
            print(f"  Predicate: {rule['predicate']}")
            print(f"  Action: {rule['action']}")
            print(f"  Confidence: {rule['confidence']:.2f}")
            print(f"  Explanation: {rule['explanation']}")
        
        # Cleanup
        db.delete(dataset)
        db.commit()
        print(f"\n✅ Cleaned up test dataset from DB")
        
        return rules
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


def test_via_bootstrap_runner():
    """Test via the bootstrap runner (full pipeline)."""
    print("\n" + "="*60)
    print("Testing via Bootstrap Runner (Full Pipeline)")
    print("="*60)
    
    from app.services.rule_extractor.bootstrap_runner import schedule_extraction
    
    db = SessionLocal()
    
    try:
        # Create test dataset file
        test_file = create_test_dataset()
        
        # Create dataset in database
        dataset = models.Dataset(
            name="Test Regex Patterns (Full Pipeline)",
            purpose=models.DatasetPurpose.RULE_EXTRACTION,
            modality=models.Modality.TABULAR,
            domain=models.Domain.GENERAL,
            storage_path=test_file
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        print(f"✅ Created dataset: ID={dataset.id}")
        
        # Run extraction
        print("🔄 Running extraction...")
        run = schedule_extraction(
            db=db,
            dataset=dataset,
            include_rag=False,
            include_llm=False
        )
        
        print(f"✅ Extraction completed: Run ID={run.id}, Status={run.status}")
        print(f"   Summary: {run.summary}")
        
        # Get extracted rules
        from app.services import rule_store
        rules = rule_store.list_rules(db, dataset_id=dataset.id)
        
        print(f"\n📊 Found {len(rules)} rules in database:")
        for i, rule in enumerate(rules, 1):
            print(f"\nRule {i} (ID={rule.id}):")
            print(f"  Column: {rule.targets.get('columns', [])}")
            print(f"  Predicate: {rule.predicate}")
            print(f"  Action: {rule.action}")
            print(f"  Confidence: {rule.confidence}")
            print(f"  Explanation: {rule.explanation}")
        
        # Cleanup
        for rule in rules:
            db.delete(rule)
        db.delete(run)
        db.delete(dataset)
        db.commit()
        print(f"\n✅ Cleaned up test data from DB")
        
        return rules
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🧪 Regex Extractor Test Suite")
    print("="*60)
    
    # Test 1: Direct extraction (no DB)
    try:
        test_regex_extractor_direct()
    except Exception as e:
        print(f"❌ Direct test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: With database
    try:
        test_regex_extractor_with_db()
    except Exception as e:
        print(f"❌ DB test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Full pipeline
    try:
        test_via_bootstrap_runner()
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)

