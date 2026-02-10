import pandas as pd
import numpy as np

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import inch

from datetime import datetime
from typing import List, Dict, Optional
import io

def json_songs_to_df(songs: List[dict]):
    """
    Converts a list of dicts of song responses into a dataframe. Used for /export-songs command
    Args:
        songs: a list of songs as returned by the main API
    """
    # flatten into rows
    rows = []
    for song in songs:
        canonical_title = song['title']
        link = song['link']
        for item in song['alt_names']:
            alt_title = item['title']
            if alt_title == canonical_title:
                if len(song['alt_names']) > 1:
                    continue
                else:
                    alt_title = None
            rows.append((canonical_title, alt_title, link))

    # construct df and process to match format specified by guide 
    df = pd.DataFrame(data = rows, columns = ['Song', 'Alt Names', 'Link'])
    df = df.sort_values(by = ['Song', 'Alt Names'], ascending = [True, True], 
                        key = lambda col: col.str.lower())
    dup_mask = df.duplicated(subset = 'Song', keep = 'first')
    df.loc[dup_mask, ['Song', 'Link']] = None
    return df


MAX_MESSAGE_LEN = 2000
def partition_song_summary_str(full_output_str: str, slack: int):
    """
    Partitions a string into chunks (separated by '\\n\\n') and merges them such that
    each merged chunk is no longer than 2000 characters. Returns a list of strings.
    Args:
        full_output_str: the string to be partitioned
        slack: an int which is subtracted the maximum message length. This is used to ensure
            that each message does not exceed 2000 - slack characters
    """
    constraint = MAX_MESSAGE_LEN - slack

    # chop full message into chunks split by \n\n
    chunks = full_output_str.split('\n\n')
    merged_chunks = []

    # greedy merging
    current = ""
    for chunk in chunks:
        sep = "\n\n" if current else ""
        if len(current) + len(sep) + len(chunk) <= constraint:
            current += sep + chunk
        else: 
            merged_chunks.append(current)
            current = chunk
    if current:
        merged_chunks.append(current)

    return merged_chunks

def generate_songs_pdf_table(data: List[Dict], buffer: io.BytesIO, user_name: Optional[str] = None):
    """
    Generate a PDF report of songs data using table layout.

    Args:
        data: List of song dictionaries
        filename: Output PDF filename
        user_name: Optional user name to include in titles
    """

    # Create the PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    # Get sample styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=12
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.gray,
        spaceAfter=24
    )

    story = []

    title_text = f"Songs Report for {user_name}"

    story.append(Paragraph(title_text, title_style))

    # Generation timestamp
    generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story.append(Paragraph(f"Generated on: {generation_time}", subtitle_style))

    # Add a spacer
    story.append(Spacer(1, 0.25 * inch))

    # Prepare table data
    table_data = []

    # Table header 
    table_data.append([
        Paragraph('<b>Song</b>', styles['Normal']),
        Paragraph('<b>Alt Names</b>', styles['Normal']),
        Paragraph('<b>Link</b>', styles['Normal'])
    ])

    # Process each song for the table
    for song in data:
        # Song title
        title = str(song['title'])

        # Alt Names
        alt_names = song.get('alt_names', [])
        filtered_alt_names = []
        for alt_name in alt_names:
            alt_title = alt_name.get('title', '')
            if str(alt_title).lower() != str(title).lower():
                filtered_alt_names.append(str(alt_title))

        # Create formatted alternate names text
        if filtered_alt_names:
            alt_names_text = "<br/>".join([f"• {name}" for name in filtered_alt_names])
        else:
            alt_names_text = "None"

        # Video link - handle None case
        link = song.get('link')
        link_text = str(link) if link else "No link"

        # Add row to table data with reordered columns:
        # 1. Song, 2. Alt Names, 3. Link
        table_data.append([
            Paragraph(title, styles['Normal']),
            Paragraph(alt_names_text, styles['Normal']),
            Paragraph(link_text, styles['Normal'])
        ])

    # Create the table with adjusted column widths for new order
    # Column widths: Song, Alt Names, Link
    table = Table(table_data, colWidths=[2*inch, 2.5*inch, 2.5*inch])

    # Apply table styles
    table.setStyle(TableStyle([
        # Header row styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

        # Data rows styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),

        # Grid lines
        ('GRID', (0, 0), (-1, -1), 1, colors.black),

        # Vertical alignment
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    story.append(table)

    # Build the PDF
    doc.build(story)
    buffer.seek(0)

