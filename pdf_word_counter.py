import sqlite3
import os
import fitz  # PyMuPDF

# Path to Database
DB_PATH = "database.sqlite"


# Folder where your PDFs are stored
PDF_FOLDER = 'extracted'


# Connect to the database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get all articles with their associated PDF filenames
cursor.execute("""
               SELECT article_analyses.id, articles.file_name
               FROM article_analyses
                        JOIN articles ON article_analyses.article_id = articles.id
               """)
records = cursor.fetchall()

for analysis_id, file_name in records:
    pdf_path = os.path.join(PDF_FOLDER, file_name)

    if not os.path.isfile(pdf_path):
        print(f"[!] File not found: {pdf_path}")
        continue

    try:
        # Open and read PDF
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        # Count words
        word_count = len(text.split())

        # Update total_words in article_analyses
        cursor.execute("""
                       UPDATE article_analyses
                       SET total_words = ?
                       WHERE id = ?
                       """, (word_count, analysis_id))
        print(f"[✓] Updated ID {analysis_id} with {word_count} words")

    except Exception as e:
        print(f"[X] Error processing {file_name}: {e}")

# Commit and close
conn.commit()
conn.close()
