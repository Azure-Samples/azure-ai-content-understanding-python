"""
Reflow Content Understanding JSON output to include line numbers inline with text.

This script reads the JSON output from Azure Content Understanding and generates
a new markdown output where line numbers (commonly found in legal documents,
depositions, and transcripts) are included inline with the corresponding text.

Content Understanding's default behavior groups line numbers (which appear on the
left margin of pages) separately from the main text content. This script uses
the bounding box coordinates from the 'source' field to determine vertical position
and match line numbers with their corresponding text lines.

Usage:
    python reflow_markdown_with_line_numbers.py <input_json_path> [--output <output_path>] [--page <page_number>]

Example:
    python reflow_markdown_with_line_numbers.py test_output/document.json --page 1 --output reflowed.md
"""

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class LineElement:
    """Represents a line or element from the document with its position."""
    content: str
    y_position: float  # Top Y coordinate
    x_position: float  # Left X coordinate
    page_number: int
    is_line_number: bool = False
    
    def __repr__(self):
        return f"LineElement(content='{self.content[:30]}...', y={self.y_position:.2f}, x={self.x_position:.2f}, is_num={self.is_line_number})"


def parse_source_coordinates(source: str) -> tuple[int, float, float, float, float]:
    """
    Parse the source coordinate string from Content Understanding.
    
    The source format is: D(pageNumber,x1,y1,x2,y2,x3,y3,x4,y4)
    where the points represent a quadrilateral (upper-left, upper-right, lower-right, lower-left)
    
    Args:
        source: The source string from Content Understanding JSON
        
    Returns:
        Tuple of (page_number, left_x, top_y, right_x, bottom_y)
    """
    # Match the D(...) pattern and extract values
    match = re.match(r'D\((\d+),([^)]+)\)', source)
    if not match:
        raise ValueError(f"Invalid source format: {source}")
    
    page_number = int(match.group(1))
    coords = [float(x) for x in match.group(2).split(',')]
    
    if len(coords) == 8:
        # Bounding polygon format: x1,y1,x2,y2,x3,y3,x4,y4
        # Points are: upper-left, upper-right, lower-right, lower-left
        x1, y1, x2, y2, x3, y3, x4, y4 = coords
        left_x = min(x1, x4)
        top_y = min(y1, y2)
        right_x = max(x2, x3)
        bottom_y = max(y3, y4)
    elif len(coords) == 4:
        # Axis-aligned bounding box format: left, top, width, height
        left_x, top_y, width, height = coords
        right_x = left_x + width
        bottom_y = top_y + height
    else:
        raise ValueError(f"Unexpected coordinate count in source: {source}")
    
    return page_number, left_x, top_y, right_x, bottom_y


def is_line_number(content: str) -> bool:
    """Check if the content appears to be a line number (1-99)."""
    return content.strip().isdigit() and 1 <= int(content.strip()) <= 99


def is_noise_element(content: str) -> bool:
    """Check if content is noise (bullets, single dots) that should be filtered."""
    content = content.strip()
    # Filter out single bullets/dots that CU uses for structure
    return content in ['·', '•', '∙'] or (len(content) == 1 and not content.isalnum())


def extract_lines_from_page(page_data: dict) -> list[LineElement]:
    """
    Extract all lines from a page and categorize them.
    
    Args:
        page_data: The page object from Content Understanding JSON
        
    Returns:
        List of LineElement objects with position information
    """
    elements = []
    page_number = page_data.get('pageNumber', 1)
    
    # Process lines array which contains the text content
    for line in page_data.get('lines', []):
        content = line.get('content', '').strip()
        source = line.get('source', '')
        
        if not source or not content:
            continue
            
        try:
            parsed_page, left_x, top_y, right_x, bottom_y = parse_source_coordinates(source)
            
            # Skip noise elements (bullets, etc.)
            if is_noise_element(content):
                continue
            
            element = LineElement(
                content=content,
                y_position=top_y,
                x_position=left_x,
                page_number=parsed_page,
                is_line_number=is_line_number(content)
            )
            elements.append(element)
            
        except ValueError as e:
            print(f"Warning: Could not parse source for line '{content[:30]}...': {e}")
            continue
    
    return elements


def group_lines_by_vertical_position(elements: list[LineElement], 
                                      y_tolerance: float = 0.15) -> list[list[LineElement]]:
    """
    Group elements that appear on the same horizontal line (same Y position).
    
    Args:
        elements: List of LineElement objects
        y_tolerance: Tolerance for considering elements on the same line (in inches for PDFs)
        
    Returns:
        List of groups, where each group contains elements on the same line
    """
    if not elements:
        return []
    
    # Sort by Y position (top to bottom)
    sorted_elements = sorted(elements, key=lambda e: e.y_position)
    
    groups = []
    current_group = [sorted_elements[0]]
    current_y = sorted_elements[0].y_position
    
    for element in sorted_elements[1:]:
        if abs(element.y_position - current_y) <= y_tolerance:
            # Same line
            current_group.append(element)
        else:
            # New line
            groups.append(current_group)
            current_group = [element]
            current_y = element.y_position
    
    # Don't forget the last group
    if current_group:
        groups.append(current_group)
    
    return groups


def reflow_page_with_line_numbers(page_data: dict, 
                                   separator: str = " | ") -> str:
    """
    Reflow a single page's content to include line numbers inline.
    
    Args:
        page_data: The page object from Content Understanding JSON
        separator: String to separate line number from content
        
    Returns:
        Reflowed markdown string for this page
    """
    elements = extract_lines_from_page(page_data)
    
    if not elements:
        return ""
    
    # Group by vertical position
    line_groups = group_lines_by_vertical_position(elements)
    
    output_lines = []
    
    for group in line_groups:
        # Sort elements within the group by X position (left to right)
        group.sort(key=lambda e: e.x_position)
        
        # Separate line numbers from content
        line_numbers = [e for e in group if e.is_line_number]
        content_elements = [e for e in group if not e.is_line_number]
        
        if not content_elements:
            # Skip lines with only line numbers (shouldn't happen but safety check)
            continue
        
        # Combine content elements
        combined_content = ' '.join(e.content for e in content_elements)
        
        # Prepend line number if found
        if line_numbers:
            # Use the first (leftmost) line number
            line_num = line_numbers[0].content
            output_lines.append(f"{line_num}{separator}{combined_content}")
        else:
            # No line number for this line (e.g., headers, footers)
            output_lines.append(combined_content)
    
    return '\n'.join(output_lines)


def reflow_document(json_data: dict, 
                    target_page: Optional[int] = None,
                    separator: str = " | ") -> str:
    """
    Reflow an entire document or specific page with line numbers inline.
    
    Args:
        json_data: The full JSON response from Content Understanding
        target_page: If specified, only process this page number (1-indexed)
        separator: String to separate line number from content
        
    Returns:
        Reflowed markdown string
    """
    contents = json_data.get('result', {}).get('contents', [])
    
    if not contents:
        raise ValueError("No contents found in JSON data")
    
    # Get the first content (document)
    content = contents[0]
    
    if content.get('kind') != 'document':
        print(f"Warning: Content kind is '{content.get('kind')}', expected 'document'")
    
    pages = content.get('pages', [])
    
    if not pages:
        raise ValueError("No pages found in document content")
    
    output_parts = []
    
    for page in pages:
        page_number = page.get('pageNumber', 0)
        
        if target_page is not None and page_number != target_page:
            continue
        
        page_output = reflow_page_with_line_numbers(page, separator)
        
        if page_output:
            if target_page is None:
                output_parts.append(f"<!-- Page {page_number} -->\n")
            output_parts.append(page_output)
            output_parts.append("")  # Blank line between pages
    
    return '\n'.join(output_parts)


def main():
    parser = argparse.ArgumentParser(
        description='Reflow Content Understanding JSON to include line numbers inline with text.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Process all pages:
    python reflow_markdown_with_line_numbers.py document.json
    
  Process specific page:
    python reflow_markdown_with_line_numbers.py document.json --page 30
    
  Custom output file and separator:
    python reflow_markdown_with_line_numbers.py document.json --output reflowed.md --separator " | "
"""
    )
    
    parser.add_argument('input_json', type=str, 
                        help='Path to the Content Understanding JSON output file')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output file path (default: print to stdout)')
    parser.add_argument('--page', '-p', type=int, default=None,
                        help='Process only this page number (1-indexed)')
    parser.add_argument('--separator', '-s', type=str, default=' | ',
                        help='Separator between line number and content (default: " | ")')
    
    args = parser.parse_args()
    
    # Read input JSON
    input_path = Path(args.input_json)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1
    
    with open(input_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # Process document
    try:
        result = reflow_document(json_data, args.page, args.separator)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    # Output result
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Output written to: {output_path}")
    else:
        print(result)
    
    return 0


if __name__ == '__main__':
    exit(main())
