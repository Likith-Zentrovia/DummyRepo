#!/usr/bin/env python3
"""
Keywords Fix Script - Fix garbled keywords in XML files
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


def find_garbled_keywords_files():
    """Find all XML files with garbled keywords."""
    files = []
    xml_files = sorted(Path(OUTPUT_DIR).glob('*.xml'))
    
    for xml_file in xml_files:
        try:
            with open(xml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for garbled keywords pattern - email with potential spaces, followed by keywords
            # Pattern handles emails like: lfelicia@uccs. edu, j. ehrenreich@miami. edu
            if re.search(r'<para>[a-z0-9_.+-]+\s*@\s*[a-z0-9-]+\.\s*[a-z]+\s+[A-Z][a-z-]+(\s+[A-Z][a-z-]+)+</para>', content, re.IGNORECASE):
                files.append(xml_file)
        except Exception as e:
            continue
    
    return files


def get_chapter_from_xml_file(xml_file):
    """Extract chapter number from XML file name."""
    match = re.search(r'ch(\d+)', xml_file.name)
    if match:
        return int(match.group(1))
    return None


def get_xhtml_chapter_file(xml_chapter):
    """Map XML chapter ID to XHTML file."""
    # Based on mapping: XML ch0008 -> XHTML Chapter 6 (offset -2)
    xhtml_chapter = xml_chapter - 2
    
    xhtml_files = list(Path(XHTML_DIR).glob(f'*_{xhtml_chapter}_Chapter.xhtml'))
    if xhtml_files:
        return xhtml_files[0]
    return None


def fix_keywords_in_file(xml_file, keywords):
    """Fix the garbled keywords section in an XML file."""
    with open(xml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the garbled para - email followed by space-separated keywords
    # Handle emails with spaces like: lfelicia@uccs. edu, j. ehrenreich@miami. edu
    garbled_pattern = r'<para>([a-z0-9_. +-]+@[a-z0-9-]+\.\s*[a-z]+\s+[A-Z][a-z-]+(?:\s+[A-Za-z-]+)*)</para>'
    
    match = re.search(garbled_pattern, content, re.IGNORECASE)
    if match and keywords:
        original_content = match.group(1)
        
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
        
        return {
            'file': xml_file.name,
            'original': original_content[:100] + '...' if len(original_content) > 100 else original_content,
            'keywords': keywords
        }
    
    return None


def main():
    print("Fixing Keywords Sections")
    print("=" * 60)
    
    # Find all files with garbled keywords
    garbled_files = find_garbled_keywords_files()
    print(f"Found {len(garbled_files)} files with garbled keywords")
    
    fixes = []
    
    for xml_file in garbled_files:
        xml_ch = get_chapter_from_xml_file(xml_file)
        if not xml_ch:
            continue
        
        # Find corresponding XHTML file
        xhtml_file = get_xhtml_chapter_file(xml_ch)
        if not xhtml_file:
            print(f"  WARNING: No XHTML file found for chapter {xml_ch}")
            continue
        
        # Extract keywords from XHTML
        keywords = extract_keywords_from_xhtml(xhtml_file)
        if not keywords:
            print(f"  WARNING: No keywords found in {xhtml_file.name}")
            continue
        
        print(f"\nProcessing: {xml_file.name}")
        print(f"  XHTML source: {xhtml_file.name}")
        print(f"  Keywords found: {keywords}")
        
        # Fix the file
        fix_result = fix_keywords_in_file(xml_file, keywords)
        if fix_result:
            fixes.append(fix_result)
            print(f"  FIXED!")
    
    print(f"\n{'=' * 60}")
    print(f"Total files fixed: {len(fixes)}")
    
    return fixes


if __name__ == "__main__":
    main()
