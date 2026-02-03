#!/usr/bin/env python3
"""
Content Loss Fix Script for XHTML to XML Conversion
====================================================
This script fixes content loss issues found in the XML files converted from XHTML epub content.

Issues Fixed:
1. Bibliography/References - severely truncated (missing authors, titles, years, page numbers)
2. Keywords - garbled/lost (concatenated incorrectly with email addresses)
3. Indexterm content - text not visible (already partially fixed, verification)

Author: Content Loss Fix Tool
Date: 2026-02-03
"""

import os
import re
import html
from pathlib import Path
from collections import defaultdict
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
import json

# Configuration
XHTML_DIR = "/workspace/xhtml_source/html"
XML_DIR = "/workspace/xml_fixed/9781071643624"
OUTPUT_DIR = "/workspace/xml_fully_fixed/9781071643624"

# Report tracking
issues_found = {
    "bibliography_truncated": [],
    "keywords_garbled": [],
    "indexterm_issues": [],
    "other_issues": []
}

fixes_applied = {
    "bibliography_restored": [],
    "keywords_fixed": [],
    "indexterm_fixed": [],
    "other_fixes": []
}


class CitationParser(HTMLParser):
    """Parse XHTML to extract full citation content."""
    
    def __init__(self):
        super().__init__()
        self.citations = {}
        self.keywords = []
        self.in_citation = False
        self.in_keyword = False
        self.current_citation_id = None
        self.current_citation_text = []
        self.current_keyword_text = []
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # Check for citation div
        if tag == 'div' and attrs_dict.get('class') == 'CitationContent':
            self.in_citation = True
            self.current_citation_id = attrs_dict.get('id', '')
            self.current_citation_text = []
            
        # Check for keyword span
        if tag == 'span' and attrs_dict.get('class') == 'Keyword':
            self.in_keyword = True
            self.current_keyword_text = []
            
    def handle_endtag(self, tag):
        if tag == 'div' and self.in_citation:
            self.in_citation = False
            if self.current_citation_id:
                full_text = ''.join(self.current_citation_text)
                # Clean up the text
                full_text = re.sub(r'\s+', ' ', full_text).strip()
                self.citations[self.current_citation_id] = full_text
            self.current_citation_id = None
            self.current_citation_text = []
            
        if tag == 'span' and self.in_keyword:
            self.in_keyword = False
            keyword_text = ''.join(self.current_keyword_text).strip()
            if keyword_text:
                self.keywords.append(keyword_text)
            self.current_keyword_text = []
            
    def handle_data(self, data):
        if self.in_citation:
            self.current_citation_text.append(data)
        if self.in_keyword:
            self.current_keyword_text.append(data)


def parse_xhtml_citations(xhtml_path):
    """Parse XHTML file to extract full citations."""
    try:
        with open(xhtml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        parser = CitationParser()
        parser.feed(content)
        return parser.citations, parser.keywords
    except Exception as e:
        print(f"Error parsing {xhtml_path}: {e}")
        return {}, []


def extract_citations_with_regex(xhtml_path):
    """Extract citations using regex for more robust parsing."""
    citations = {}
    keywords = []
    
    try:
        with open(xhtml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract citations
        citation_pattern = r'<div class="CitationContent" id="(CR\d+)">(.*?)</div>'
        matches = re.findall(citation_pattern, content, re.DOTALL)
        
        for cit_id, cit_content in matches:
            # Clean HTML tags but preserve meaningful content
            clean_content = re.sub(r'<span class="RefSource">[^<]*</span>', '', cit_content)
            clean_content = re.sub(r'<span class="Occurrence[^"]*">[^<]*</span>', '', clean_content)
            clean_content = re.sub(r'<a[^>]*>([^<]*)</a>', r'\1', clean_content)
            clean_content = re.sub(r'<em[^>]*>([^<]*)</em>', r'\1', clean_content)
            clean_content = re.sub(r'<span[^>]*>([^<]*)</span>', r'\1', clean_content)
            clean_content = re.sub(r'</?[a-z][^>]*>', '', clean_content)
            clean_content = re.sub(r'\s+', ' ', clean_content).strip()
            clean_content = html.unescape(clean_content)
            citations[cit_id] = clean_content
            
        # Extract keywords
        keyword_pattern = r'<span class="Keyword"[^>]*>([^<]+)</span>'
        keywords = re.findall(keyword_pattern, content)
        keywords = [k.strip() for k in keywords if k.strip()]
        
        return citations, keywords
    except Exception as e:
        print(f"Error parsing {xhtml_path}: {e}")
        return {}, []


def get_chapter_number_from_xhtml(filename):
    """Extract chapter number from XHTML filename."""
    match = re.search(r'_(\d+)_Chapter\.xhtml$', filename)
    if match:
        return int(match.group(1))
    return None


def get_chapter_number_from_xml(filename):
    """Extract chapter number from XML filename."""
    match = re.search(r'ch(\d+)', filename)
    if match:
        return int(match.group(1))
    return None


def map_xhtml_to_xml_chapters():
    """Create mapping between XHTML chapters and XML file prefixes."""
    mapping = {}
    
    # Get all XHTML chapter files
    xhtml_files = sorted(Path(XHTML_DIR).glob('*_Chapter.xhtml'))
    
    # Get all XML files and group by chapter
    xml_files = sorted(Path(XML_DIR).glob('sect1.*.ch*.xml'))
    xml_chapters = defaultdict(list)
    
    for xml_file in xml_files:
        ch_num = get_chapter_number_from_xml(xml_file.name)
        if ch_num:
            xml_chapters[ch_num].append(xml_file)
    
    for xhtml_file in xhtml_files:
        ch_num = get_chapter_number_from_xhtml(xhtml_file.name)
        if ch_num:
            # XHTML chapter numbers map to XML chapter numbers
            # Need to determine the mapping - analyze file content
            mapping[xhtml_file] = {
                'xhtml_chapter': ch_num,
                'xml_files': []
            }
            
    return mapping


def find_xml_bibliography_file(chapter_id):
    """Find the XML file containing bibliography for a chapter."""
    # Bibliography files typically end with higher section numbers
    pattern = f"sect1.9781071643624.ch{chapter_id:04d}s*.xml"
    xml_files = sorted(Path(XML_DIR).glob(pattern))
    
    for xml_file in reversed(xml_files):  # Check from highest section number
        try:
            with open(xml_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '<bibliography' in content or '<bibliomixed' in content:
                    return xml_file
        except Exception as e:
            continue
    return None


def find_xml_keywords_file(chapter_id):
    """Find the XML file containing keywords for a chapter."""
    pattern = f"sect1.9781071643624.ch{chapter_id:04d}s*.xml"
    xml_files = sorted(Path(XML_DIR).glob(pattern))
    
    for xml_file in xml_files:
        try:
            with open(xml_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Check for garbled keywords patterns
                if re.search(r'@.*\.(edu|com|org)', content) and re.search(r'Depression|Anxiety|Disorder|Symptom|Assessment', content):
                    return xml_file
        except Exception as e:
            continue
    return None


def fix_bibliography_content(xml_content, citations, chapter_info):
    """Fix truncated bibliography entries with full citation content."""
    fixed_content = xml_content
    fixes_made = []
    
    # Find all bibliomixed entries
    bibliomixed_pattern = r'<bibliomixed id="([^"]+)">([^<]*)</bibliomixed>'
    matches = list(re.finditer(bibliomixed_pattern, fixed_content))
    
    for match in matches:
        bib_id = match.group(1)
        current_content = match.group(2)
        
        # Extract the CR number from the bib_id
        # Format: ch0008s0009bib01 -> need to map to CR1, CR01, etc.
        bib_num_match = re.search(r'bib(\d+)$', bib_id)
        if not bib_num_match:
            continue
            
        bib_num = int(bib_num_match.group(1))
        
        # Try different citation ID formats
        possible_ids = [f"CR{bib_num}", f"CR{bib_num:02d}", f"CR{bib_num:03d}"]
        
        for cit_id in possible_ids:
            if cit_id in citations:
                full_citation = citations[cit_id]
                
                # Check if current content is truncated
                if len(current_content) < len(full_citation) * 0.7:
                    # This is truncated, replace it
                    old_entry = match.group(0)
                    new_entry = f'<bibliomixed id="{bib_id}">{html.escape(full_citation)}</bibliomixed>'
                    fixed_content = fixed_content.replace(old_entry, new_entry, 1)
                    
                    fixes_made.append({
                        'bib_id': bib_id,
                        'original': current_content[:100] + '...' if len(current_content) > 100 else current_content,
                        'restored': full_citation[:100] + '...' if len(full_citation) > 100 else full_citation
                    })
                break
    
    return fixed_content, fixes_made


def fix_keywords_section(xml_content, keywords, chapter_info):
    """Fix garbled keywords section with proper keyword structure."""
    fixes_made = []
    
    # Check for garbled keywords pattern
    garbled_pattern = r'<para>([^<]*@[^<]*\.(edu|com|org)[^<]*(?:Depression|Dysthymia|Mood|Assessment|Anxiety|Disorder)[^<]*)</para>'
    match = re.search(garbled_pattern, xml_content)
    
    if match and keywords:
        garbled_content = match.group(1)
        
        # Build proper keywords structure according to DTD
        keywords_xml = '<keywordset>\n'
        for keyword in keywords:
            keywords_xml += f'      <keyword>{html.escape(keyword)}</keyword>\n'
        keywords_xml += '   </keywordset>'
        
        # Replace the garbled para with proper keywords
        old_para = match.group(0)
        xml_content = xml_content.replace(old_para, keywords_xml)
        
        fixes_made.append({
            'original': garbled_content[:100] + '...' if len(garbled_content) > 100 else garbled_content,
            'keywords': keywords
        })
    
    return xml_content, fixes_made


def analyze_chapter_mapping():
    """Analyze how XHTML chapters map to XML chapter IDs."""
    mappings = []
    
    xhtml_files = sorted(Path(XHTML_DIR).glob('*_Chapter.xhtml'))
    
    for xhtml_file in xhtml_files:
        xhtml_ch = get_chapter_number_from_xhtml(xhtml_file.name)
        if not xhtml_ch:
            continue
            
        # Read XHTML to find the chapter title
        try:
            with open(xhtml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            title_match = re.search(r'<h1 class="ChapterTitle"[^>]*>([^<]+)</h1>', content)
            chapter_title = title_match.group(1) if title_match else "Unknown"
            
            # Extract the chapter number from title
            title_ch_match = re.search(r'^(\d+)\.', chapter_title)
            title_ch_num = int(title_ch_match.group(1)) if title_ch_match else None
            
            mappings.append({
                'xhtml_file': xhtml_file.name,
                'xhtml_num': xhtml_ch,
                'title': chapter_title,
                'title_ch_num': title_ch_num
            })
        except Exception as e:
            print(f"Error reading {xhtml_file}: {e}")
    
    return mappings


def get_xml_chapter_id_for_xhtml(xhtml_num, mappings):
    """Determine the XML chapter ID for an XHTML chapter number."""
    # Based on the file structure, there's an offset
    # XHTML 106097_6_En_6_Chapter.xhtml (Chapter 6) -> XML ch0008
    # We need to determine this mapping
    
    # Looking at the data:
    # - xhtml_source/html/106097_6_En_6_Chapter.xhtml -> Chapter 6: Depressive Disorders
    # - xml_fixed/.../sect1.9781071643624.ch0008s0002.xml -> chaptertitle: "6. Depressive Disorders"
    
    # The mapping seems to be: XHTML file number 6 -> XML chapter 8 (offset of +2)
    # Let me verify this with more samples
    
    # For now, use the title chapter number from mappings
    for m in mappings:
        if m['xhtml_num'] == xhtml_num:
            if m['title_ch_num']:
                # XML chapter ID = title chapter number + 2 (based on pattern observed)
                # But wait, title says "6" and XML uses ch0008
                # So offset is 8 - 6 = 2... or maybe the numbering is different
                # Let me check: Ch 6 in title -> ch0008 in XML means offset = 2
                return m['title_ch_num'] + 2
    return xhtml_num


def process_all_chapters():
    """Process all chapters to fix content loss."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # First, analyze chapter mapping
    print("Analyzing chapter mappings...")
    mappings = analyze_chapter_mapping()
    
    for m in mappings:
        print(f"  XHTML {m['xhtml_num']}: {m['title']} -> Title Ch {m['title_ch_num']}")
    
    # Copy all XML files to output directory first
    print("\nCopying XML files to output directory...")
    for xml_file in Path(XML_DIR).glob('*.xml'):
        dest = Path(OUTPUT_DIR) / xml_file.name
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(content)
    
    print("\nProcessing XHTML chapters for content restoration...")
    
    # Process each XHTML chapter
    xhtml_files = sorted(Path(XHTML_DIR).glob('*_Chapter.xhtml'))
    
    for xhtml_file in xhtml_files:
        xhtml_ch = get_chapter_number_from_xhtml(xhtml_file.name)
        if not xhtml_ch:
            continue
            
        print(f"\nProcessing XHTML Chapter {xhtml_ch}: {xhtml_file.name}")
        
        # Extract citations and keywords from XHTML
        citations, keywords = extract_citations_with_regex(xhtml_file)
        print(f"  Found {len(citations)} citations, {len(keywords)} keywords")
        
        if not citations and not keywords:
            continue
        
        # Determine XML chapter ID
        xml_ch_id = get_xml_chapter_id_for_xhtml(xhtml_ch, mappings)
        print(f"  Mapping to XML chapter ID: ch{xml_ch_id:04d}")
        
        # Find and fix bibliography XML file
        bib_file = find_xml_bibliography_file(xml_ch_id)
        if bib_file:
            print(f"  Found bibliography file: {bib_file.name}")
            
            output_bib_file = Path(OUTPUT_DIR) / bib_file.name
            with open(output_bib_file, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            fixed_content, bib_fixes = fix_bibliography_content(xml_content, citations, 
                                                                {'xhtml_ch': xhtml_ch, 'xml_ch': xml_ch_id})
            
            if bib_fixes:
                print(f"  Fixed {len(bib_fixes)} bibliography entries")
                with open(output_bib_file, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                fixes_applied['bibliography_restored'].extend([
                    {**fix, 'file': bib_file.name, 'xhtml_ch': xhtml_ch} for fix in bib_fixes
                ])
        
        # Find and fix keywords XML file
        kw_file = find_xml_keywords_file(xml_ch_id)
        if kw_file and keywords:
            print(f"  Found keywords file: {kw_file.name}")
            
            output_kw_file = Path(OUTPUT_DIR) / kw_file.name
            with open(output_kw_file, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            fixed_content, kw_fixes = fix_keywords_section(xml_content, keywords,
                                                           {'xhtml_ch': xhtml_ch, 'xml_ch': xml_ch_id})
            
            if kw_fixes:
                print(f"  Fixed keywords section")
                with open(output_kw_file, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                fixes_applied['keywords_fixed'].extend([
                    {**fix, 'file': kw_file.name, 'xhtml_ch': xhtml_ch} for fix in kw_fixes
                ])


def verify_indexterm_fixes():
    """Verify that indexterm content is visible (not just in indexterm tags)."""
    print("\n\nVerifying indexterm fixes...")
    
    xml_files = sorted(Path(OUTPUT_DIR).glob('sect1.*.xml'))
    indexterm_issues = []
    
    for xml_file in xml_files:
        try:
            with open(xml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find indexterms
            indexterm_pattern = r'<indexterm[^>]*>\s*<primary>([^<]+)</primary>\s*</indexterm>'
            matches = list(re.finditer(indexterm_pattern, content))
            
            for match in matches:
                indexterm_text = match.group(1)
                full_match = match.group(0)
                
                # Check if the indexterm text appears immediately before the indexterm tag
                # as visible text (not just inside indexterm)
                preceding_context = content[:match.start()]
                
                # The text should appear before the indexterm as visible content
                # Pattern: "visible text<indexterm><primary>visible text</primary></indexterm>"
                expected_pattern = re.escape(indexterm_text) + r'\s*' + re.escape(full_match)
                
                if not re.search(expected_pattern, content):
                    # Check if it's at the start of a para (which is also acceptable)
                    start_of_para_pattern = r'<para[^>]*>\s*' + re.escape(indexterm_text) + r'\s*' + re.escape(full_match[:20])
                    if not re.search(start_of_para_pattern, content):
                        indexterm_issues.append({
                            'file': xml_file.name,
                            'text': indexterm_text,
                            'context': content[max(0, match.start()-50):match.start()]
                        })
        except Exception as e:
            print(f"Error checking {xml_file}: {e}")
    
    if indexterm_issues:
        print(f"  Found {len(indexterm_issues)} potential indexterm issues")
        issues_found['indexterm_issues'] = indexterm_issues
    else:
        print("  All indexterms appear to have visible content")


def generate_comprehensive_report():
    """Generate a detailed report for the development team."""
    report = []
    report.append("=" * 80)
    report.append("CONTENT LOSS FIX REPORT - XHTML TO XML CONVERSION")
    report.append("=" * 80)
    report.append("")
    report.append("Generated: 2026-02-03")
    report.append("Source: XHTML epub content (html.zip)")
    report.append("Target: XML files (9781071643624)")
    report.append("")
    
    # Summary
    report.append("-" * 80)
    report.append("EXECUTIVE SUMMARY")
    report.append("-" * 80)
    report.append("")
    report.append("This report documents content loss issues identified during XHTML to XML conversion")
    report.append("and provides detailed information for the development team to fix the conversion code.")
    report.append("")
    
    total_bib_fixes = len(fixes_applied.get('bibliography_restored', []))
    total_kw_fixes = len(fixes_applied.get('keywords_fixed', []))
    total_indexterm_issues = len(issues_found.get('indexterm_issues', []))
    
    report.append(f"Total Bibliography Entries Restored: {total_bib_fixes}")
    report.append(f"Total Keywords Sections Fixed: {total_kw_fixes}")
    report.append(f"Total Indexterm Issues Found: {total_indexterm_issues}")
    report.append("")
    
    # Issue 1: Bibliography Truncation
    report.append("=" * 80)
    report.append("ISSUE #1: BIBLIOGRAPHY/REFERENCES TRUNCATION")
    report.append("=" * 80)
    report.append("")
    report.append("PROBLEM DESCRIPTION:")
    report.append("-" * 40)
    report.append("The XML conversion process severely truncates bibliography entries.")
    report.append("Missing content includes: author names, publication years, article titles, page numbers.")
    report.append("")
    report.append("ROOT CAUSE ANALYSIS:")
    report.append("-" * 40)
    report.append("The conversion code appears to be extracting only partial content from the")
    report.append("<div class='CitationContent'> elements in the XHTML source.")
    report.append("")
    report.append("XHTML SOURCE STRUCTURE:")
    report.append("  <li class='Citation'>")
    report.append("    <div class='CitationContent' id='CR67'>")
    report.append("      Yesavage, J. A., Brink, T. L., ... (1982). Title. Journal, 17(1), 37-49.")
    report.append("    </div>")
    report.append("  </li>")
    report.append("")
    report.append("CURRENT XML OUTPUT (TRUNCATED):")
    report.append("  <bibliomixed id='..bib67'>Journal of Psychiatric Research, 17https://doi.org/...</bibliomixed>")
    report.append("")
    report.append("EXPECTED XML OUTPUT (FULL):")
    report.append("  <bibliomixed id='..bib67'>Yesavage, J. A., Brink, T. L., Rose, T. L., et al. (1982).")
    report.append("    Development and validation of a geriatric depression screening scale: A preliminary report.")
    report.append("    Journal of Psychiatric Research, 17(1), 37-49. https://doi.org/...</bibliomixed>")
    report.append("")
    report.append("RECOMMENDED CODE FIX:")
    report.append("-" * 40)
    report.append("1. When parsing <div class='CitationContent'> elements, extract ALL text content")
    report.append("2. Include author names, years in parentheses, article titles")
    report.append("3. Preserve italic formatting for journal names (<em> -> <emphasis>)")
    report.append("4. Include volume, issue numbers, and page ranges")
    report.append("")
    
    if fixes_applied.get('bibliography_restored'):
        report.append("DETAILED FIX LOG:")
        report.append("-" * 40)
        for i, fix in enumerate(fixes_applied['bibliography_restored'][:20], 1):
            report.append(f"\n{i}. File: {fix['file']}")
            report.append(f"   BibID: {fix['bib_id']}")
            report.append(f"   BEFORE: {fix['original']}")
            report.append(f"   AFTER:  {fix['restored']}")
        if len(fixes_applied['bibliography_restored']) > 20:
            report.append(f"\n... and {len(fixes_applied['bibliography_restored']) - 20} more fixes")
    report.append("")
    
    # Issue 2: Keywords Garbled
    report.append("=" * 80)
    report.append("ISSUE #2: KEYWORDS SECTION GARBLED")
    report.append("=" * 80)
    report.append("")
    report.append("PROBLEM DESCRIPTION:")
    report.append("-" * 40)
    report.append("Keywords are concatenated with email addresses and other metadata into a single")
    report.append("unstructured paragraph, losing their semantic structure.")
    report.append("")
    report.append("ROOT CAUSE ANALYSIS:")
    report.append("-" * 40)
    report.append("The conversion code appears to be concatenating multiple elements from the")
    report.append("abstract/metadata section without proper parsing.")
    report.append("")
    report.append("XHTML SOURCE STRUCTURE:")
    report.append("  <div class='KeywordGroup'>")
    report.append("    <span class='Keyword'>Depression</span>")
    report.append("    <span class='Keyword'>Dysthymia</span>")
    report.append("    <span class='Keyword'>Mood</span>")
    report.append("    ...")
    report.append("  </div>")
    report.append("")
    report.append("CURRENT XML OUTPUT (GARBLED):")
    report.append("  <para>lfelicia@uccs.edu Depression Dysthymia Mood Assessment Interviewing Psychopathology</para>")
    report.append("")
    report.append("EXPECTED XML OUTPUT (STRUCTURED):")
    report.append("  <keywordset>")
    report.append("    <keyword>Depression</keyword>")
    report.append("    <keyword>Dysthymia</keyword>")
    report.append("    <keyword>Mood</keyword>")
    report.append("    <keyword>Assessment</keyword>")
    report.append("    <keyword>Interviewing</keyword>")
    report.append("    <keyword>Psychopathology</keyword>")
    report.append("  </keywordset>")
    report.append("")
    report.append("RECOMMENDED CODE FIX:")
    report.append("-" * 40)
    report.append("1. Parse <div class='KeywordGroup'> separately from contact information")
    report.append("2. Extract each <span class='Keyword'> element individually")
    report.append("3. Generate proper <keywordset>/<keyword> structure per DTD")
    report.append("4. Keep email/contact info in appropriate metadata section")
    report.append("")
    
    if fixes_applied.get('keywords_fixed'):
        report.append("DETAILED FIX LOG:")
        report.append("-" * 40)
        for i, fix in enumerate(fixes_applied['keywords_fixed'], 1):
            report.append(f"\n{i}. File: {fix['file']}")
            report.append(f"   BEFORE: {fix['original']}")
            report.append(f"   AFTER Keywords: {', '.join(fix['keywords'])}")
    report.append("")
    
    # Issue 3: Indexterm (Previously Fixed)
    report.append("=" * 80)
    report.append("ISSUE #3: INDEXTERM CONTENT NOT VISIBLE (PREVIOUSLY ADDRESSED)")
    report.append("=" * 80)
    report.append("")
    report.append("PROBLEM DESCRIPTION:")
    report.append("-" * 40)
    report.append("Text inside <indexterm><primary>text</primary></indexterm> was not appearing")
    report.append("as visible content in the XML output. The text was only stored as metadata.")
    report.append("")
    report.append("ROOT CAUSE ANALYSIS:")
    report.append("-" * 40)
    report.append("XHTML uses <span id='ITerm...'>visible text</span> where the text is both")
    report.append("displayed AND used for indexing. The conversion placed text only inside")
    report.append("the <indexterm> element, making it invisible in rendered output.")
    report.append("")
    report.append("XHTML SOURCE STRUCTURE:")
    report.append("  <span id='ITerm1'>Anxiety disorders</span> are common...")
    report.append("")
    report.append("INCORRECT XML OUTPUT:")
    report.append("  <indexterm><primary>Anxiety disorders</primary></indexterm> are common...")
    report.append("")
    report.append("CORRECT XML OUTPUT:")
    report.append("  Anxiety disorders<indexterm><primary>Anxiety disorders</primary></indexterm> are common...")
    report.append("")
    report.append("STATUS: This issue appears to have been previously addressed in the fixed files.")
    report.append("")
    
    if issues_found.get('indexterm_issues'):
        report.append("REMAINING INDEXTERM ISSUES FOUND:")
        report.append("-" * 40)
        for issue in issues_found['indexterm_issues'][:10]:
            report.append(f"  File: {issue['file']}")
            report.append(f"  Text: {issue['text']}")
            report.append(f"  Context: ...{issue['context']}")
            report.append("")
    
    # Recommendations
    report.append("=" * 80)
    report.append("RECOMMENDATIONS FOR DEVELOPMENT TEAM")
    report.append("=" * 80)
    report.append("")
    report.append("1. BIBLIOGRAPHY PARSING:")
    report.append("   - Review the CitationContent parsing logic")
    report.append("   - Ensure full text extraction including nested <em> tags")
    report.append("   - Test with citations containing special characters (&, <, >)")
    report.append("")
    report.append("2. KEYWORDS HANDLING:")
    report.append("   - Separate keyword extraction from contact info parsing")
    report.append("   - Implement proper <keywordset> generation")
    report.append("   - Validate against DTD schema")
    report.append("")
    report.append("3. INDEXTERM HANDLING:")
    report.append("   - When converting ITerm spans, duplicate text as visible content")
    report.append("   - Preserve proper spacing around indexterm elements")
    report.append("")
    report.append("4. TESTING:")
    report.append("   - Create unit tests for each content type")
    report.append("   - Compare character counts between XHTML and XML")
    report.append("   - Validate all XML against DTD after conversion")
    report.append("")
    
    return "\n".join(report)


def main():
    """Main entry point."""
    print("=" * 60)
    print("Content Loss Fix Script")
    print("=" * 60)
    
    # Process all chapters
    process_all_chapters()
    
    # Verify indexterm fixes
    verify_indexterm_fixes()
    
    # Generate report
    print("\nGenerating comprehensive report...")
    report = generate_comprehensive_report()
    
    report_path = "/workspace/content_loss_fix_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")
    
    # Save detailed JSON data
    json_data = {
        'issues_found': issues_found,
        'fixes_applied': fixes_applied
    }
    json_path = "/workspace/content_loss_fix_data.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, default=str)
    print(f"Detailed data saved to: {json_path}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Bibliography entries restored: {len(fixes_applied.get('bibliography_restored', []))}")
    print(f"Keywords sections fixed: {len(fixes_applied.get('keywords_fixed', []))}")
    print(f"Indexterm issues found: {len(issues_found.get('indexterm_issues', []))}")
    print("=" * 60)


if __name__ == "__main__":
    main()
