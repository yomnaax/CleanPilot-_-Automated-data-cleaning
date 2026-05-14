"""
Quick test for Regex Extractor - simplest way to test.

Run: python quick_test_regex.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.rule_extractor.regex_extractor import RegexExtractor
from app.db import models
import pandas as pd

# Create test data
test_data = {
    "email": ["john@example.com", "jane@test.org", "user@domain.com"],
    "phone": ["555-123-4567", "(555) 987-6543", "555.111.2222"],
    "date_iso": ["2024-01-15", "2024-02-20", "2024-03-10"],
    "url": ["https://example.com", "http://test.org", "https://api.com"],
    "random": ["some text", "more text", "just words"]
}

# Create DataFrame and save
df = pd.DataFrame(test_data)
test_file = Path("data/storage/quick_test.csv")
test_file.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(test_file, index=False)
print(f"✅ Created test file: {test_file}")

# Create mock dataset
class MockDataset:
    id = 1
    modality = models.Modality.TABULAR
    storage_path = str(test_file)

dataset = MockDataset()

# Test extractor
print("\n🔄 Running Regex Extractor...")
extractor = RegexExtractor()
rules = extractor.extract(dataset)

# Display results
print(f"\n📊 Extracted {len(rules)} rules:\n")
for i, rule in enumerate(rules, 1):
    print(f"{i}. {rule['targets']['columns'][0]}")
    print(f"   Pattern: {rule['predicate']}")
    print(f"   Confidence: {rule['confidence']:.2f}")
    print(f"   {rule['explanation']}")
    print()

if len(rules) > 0:
    print("✅ Regex Extractor is working!")
else:
    print("⚠️  No rules extracted. Check the test data.")

