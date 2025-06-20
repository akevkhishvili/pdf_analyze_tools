import os
import json
import difflib

# Parameters
json_input_path = './assets/articles.json'
pdf_folder_path = './dist/extracted'
json_output_path = './assets/articles_with_filenames.json'
similarity_threshold = 0.6

# Load the JSON data
with open(json_input_path, 'r', encoding='utf-8') as f:
    articles = json.load(f)

# Collect PDF filenames (without extension)
pdf_files = [f for f in os.listdir(pdf_folder_path) if f.lower().endswith('.pdf')]
pdf_names = [os.path.splitext(f)[0] for f in pdf_files]

# Function to find best fuzzy match
def find_best_match(title, names, threshold=0.6):
    # Get close matches (up to 1 best candidate)
    matches = difflib.get_close_matches(title, names, n=1, cutoff=threshold)
    return matches[0] if matches else None

# Match each article title to the best PDF filename
for article in articles:
    title = article['article_title']
    best_name = find_best_match(title, pdf_names, threshold=similarity_threshold)
    if best_name:
        # Reconstruct full file name
        matched_filename = best_name + '.pdf'
    else:
        matched_filename = None  # No good match found
    article['file_name'] = matched_filename

# Save the updated JSON
with open(json_output_path, 'w', encoding='utf-8') as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)

print(f"Processed {len(articles)} articles. Results saved to {json_output_path}")
