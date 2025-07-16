#!/usr/bin/env python3
"""
Test the hackathon solution with various scenarios
"""

import json
import os
from pathlib import Path

def test_hackathon_solution():
    """Test the generated JSON output"""
    
    # Read the output file
    output_file = Path("/app/output/test_document.json")
    
    if not output_file.exists():
        print("❌ Output file not found!")
        return False
    
    try:
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        # Test required fields
        if 'title' not in data:
            print("❌ Missing 'title' field")
            return False
        
        if 'outline' not in data:
            print("❌ Missing 'outline' field")
            return False
        
        print(f"✅ Title: {data['title']}")
        print(f"✅ Found {len(data['outline'])} headings")
        
        # Test heading structure
        valid_levels = ['H1', 'H2', 'H3']
        for i, heading in enumerate(data['outline']):
            if 'level' not in heading:
                print(f"❌ Heading {i}: Missing 'level' field")
                return False
            
            if 'text' not in heading:
                print(f"❌ Heading {i}: Missing 'text' field")
                return False
            
            if 'page' not in heading:
                print(f"❌ Heading {i}: Missing 'page' field")
                return False
            
            if heading['level'] not in valid_levels:
                print(f"❌ Heading {i}: Invalid level '{heading['level']}'")
                return False
            
            if not isinstance(heading['page'], int) or heading['page'] < 1:
                print(f"❌ Heading {i}: Invalid page number '{heading['page']}'")
                return False
        
        # Test specific content
        h1_headings = [h for h in data['outline'] if h['level'] == 'H1']
        h2_headings = [h for h in data['outline'] if h['level'] == 'H2']
        h3_headings = [h for h in data['outline'] if h['level'] == 'H3']
        
        print(f"✅ H1 headings: {len(h1_headings)}")
        print(f"✅ H2 headings: {len(h2_headings)}")
        print(f"✅ H3 headings: {len(h3_headings)}")
        
        # Check for expected content
        expected_h1 = ["1. Introduction", "2. Machine Learning Fundamentals", "CONCLUSION", "REFERENCES"]
        found_h1 = [h['text'] for h in h1_headings]
        
        for expected in expected_h1:
            if expected in found_h1:
                print(f"✅ Found expected H1: {expected}")
            else:
                print(f"⚠️  Missing expected H1: {expected}")
        
        # Check page distribution
        pages = [h['page'] for h in data['outline']]
        unique_pages = set(pages)
        print(f"✅ Content spans {len(unique_pages)} pages: {sorted(unique_pages)}")
        
        # Validate JSON format
        json_str = json.dumps(data, indent=2)
        print(f"✅ Valid JSON format ({len(json_str)} characters)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading output: {e}")
        return False

def test_performance():
    """Test performance constraints"""
    import time
    import subprocess
    
    print("\n📊 Performance Testing")
    
    # Test execution time
    start_time = time.time()
    result = subprocess.run(['python', '/app/hackathon_solution.py'], 
                          capture_output=True, text=True, cwd='/app')
    end_time = time.time()
    
    execution_time = end_time - start_time
    print(f"✅ Execution time: {execution_time:.2f} seconds")
    
    if execution_time > 10:
        print("⚠️  Execution time exceeds 10 seconds")
    else:
        print("✅ Execution time within constraints")
    
    # Test memory usage (approximate)
    import psutil
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"✅ Memory usage: {memory_mb:.1f} MB")
    
    return execution_time < 10

if __name__ == "__main__":
    print("🧪 Testing Hackathon Solution")
    print("=" * 40)
    
    # Test output quality
    output_test = test_hackathon_solution()
    
    # Test performance
    performance_test = test_performance()
    
    print("\n" + "=" * 40)
    if output_test and performance_test:
        print("🎉 All tests passed! Solution ready for submission.")
    else:
        print("❌ Some tests failed. Please review the issues.")