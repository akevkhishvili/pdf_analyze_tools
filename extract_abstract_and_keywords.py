import os
import sqlite3
import fitz  # PyMuPDF
import re

DB_PATH = r"Path to db"
PDF_FOLDER = "path to folder with pdfs"

# Connect to SQLite
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def extract_pdf_text(pdf_path):
    try:
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text("text") + "\n"
        return text
    except Exception as e:
        print(f"⚠️ Failed to read PDF {pdf_path}: {e}")
        return None

def extract_abstract_and_keywords(text):
    if not text:
        return None, None

    # Look for ABSTRACT block
    abstract_match = re.search(r'ABSTRACT\s*(.+?)(?:\nKeywords:|\Z)', text, re.DOTALL | re.IGNORECASE)
    abstract = abstract_match.group(1).strip() if abstract_match else None

    # Look for Keywords line
    keywords_match = re.search(r'Keywords?:\s*(.+)', text, re.IGNORECASE)
    keywords = keywords_match.group(1).strip() if keywords_match else None

    return abstract, keywords

# Get all articles
cursor.execute("SELECT id, file_name FROM articles")
articles = cursor.fetchall()

for article_id, file_name in articles:
    if not file_name:
        print(f"⚠️ Skipping article {article_id}: file_name is None")
        continue

    pdf_path = os.path.join(PDF_FOLDER, str(file_name))  # ensure it's a string

    if not os.path.exists(pdf_path):
        print(f"⚠️ Skipping article {article_id}: file not found → {file_name}")
        continue

    print(f"Processing article {article_id} → {file_name}")
    pdf_text = extract_pdf_text(pdf_path)
    if not pdf_text:
        print(f"⚠️ Skipping article {article_id}: PDF unreadable")
        continue

    abstract, keywords = extract_abstract_and_keywords(pdf_text)

    if abstract or keywords:
        cursor.execute("""
            INSERT INTO article_abstracts (article_id, abstract_text, key_words)
            VALUES (?, ?, ?)
        """, (article_id, abstract, keywords))
        conn.commit()
        print(f"✅ Inserted abstract + keywords for article {article_id}")
    else:
        print(f"⚠️ No abstract or keywords found in article {article_id}")

conn.close()
print("🎉 Done!")
