#!/usr/bin/env python3
"""
Comprehensive Keywords Fix Script - Fix all garbled keywords in XML files
"""

import os
import re
import html
from pathlib import Path

OUTPUT_DIR = "/workspace/xml_fully_fixed/9781071643624"
XHTML_DIR = "/workspace/xhtml_source/html"

def extract_keywords_from_xhtml(xhtml_path):
    """Extract keywords from XHTML file."""
    try:
        with open(xhtml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract keywords
        keyword_pattern = r'<span class="Keyword"[^>]*>([^<]+)</span>'
        keywords = re.findall(keyword_pattern, content)
        keywords = [k.strip() for k in keywords if k.strip()]
        
        return keywords
    except Exception as e:
        print(f"Error parsing {xhtml_path}: {e}")
        return []


def get_xhtml_chapter_file(xml_chapter):
    """Map XML chapter ID to XHTML file."""
    # Based on mapping: XML ch0008 -> XHTML Chapter 6 (offset -2)
    xhtml_chapter = xml_chapter - 2
    
    xhtml_files = list(Path(XHTML_DIR).glob(f'*_{xhtml_chapter}_Chapter.xhtml'))
    if xhtml_files:
        return xhtml_files[0]
    return None


def fix_all_garbled_keywords():
    """Find and fix all files with garbled keywords."""
    fixes = []
    
    # Find all XML files
    xml_files = sorted(Path(OUTPUT_DIR).glob('*.xml'))
    
    # Pattern to detect garbled keywords - very flexible
    garbled_patterns = [
        # Pattern 1: email (with possible spaces) followed by capitalized words
        (r'<para>([a-z0-9_. +-]+@[a-z0-9_ -]+\.\s*[a-z]+)\s+([A-Z][A-Za-z -]+(?:\s+[A-Za-z -]+)*)</para>', 'full'),
        # Pattern 2: just the full para content with email
        (r'<para>([^<]+@[^<]+)</para>', 'simple'),
    ]
    
    for xml_file in xml_files:
        try:
            with open(xml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip if no @ symbol
            if '@' not in content:
                continue
            
            # Skip files that already have keywordset
            if '<keywordset>' in content:
                continue
            
            # Check for garbled pattern
            for pattern, ptype in garbled_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    # Extract chapter number
                    ch_match = re.search(r'ch(\d+)', xml_file.name)
                    if not ch_match:
                        continue
                    
                    xml_ch = int(ch_match.group(1))
                    
                    # Get corresponding XHTML file
                    xhtml_file = get_xhtml_chapter_file(xml_ch)
                    if not xhtml_file:
                        print(f"  WARNING: No XHTML file found for chapter {xml_ch} (file: {xml_file.name})")
                        continue
                    
                    # Extract keywords from XHTML
                    keywords = extract_keywords_from_xhtml(xhtml_file)
                    if not keywords:
                        print(f"  WARNING: No keywords found in {xhtml_file.name}")
                        continue
                    
                    # Build proper keywords structure
                    keywords_xml = '<keywordset>\n'
                    for keyword in keywords:
                        keywords_xml += f'      <keyword>{html.escape(keyword)}</keyword>\n'
                    keywords_xml += '   </keywordset>'
                    
                    # Replace
                    old_para = match.group(0)
                    new_content = content.replace(old_para, keywords_xml, 1)
                    
                    with open(xml_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    fixes.append({
                        'file': xml_file.name,
                        'original': match.group(0)[:100],
                        'keywords': keywords
                    })
                    
                    print(f"FIXED: {xml_file.name}")
                    print(f"  XHTML: {xhtml_file.name}")
                    print(f"  Keywords: {keywords}")
                    
                    break  # Move to next file
                    
        except Exception as e:
            print(f"Error processing {xml_file}: {e}")
    
    return fixes


def main():
    print("Comprehensive Keywords Fix")
    print("=" * 60)
    
    fixes = fix_all_garbled_keywords()
    
    print(f"\n{'=' * 60}")
    print(f"Total files fixed: {len(fixes)}")
    
    return fixes


if __name__ == "__main__":
    main()
