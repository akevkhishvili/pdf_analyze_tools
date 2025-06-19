import os, re, threading
import fitz  # PyMuPDF
from transformers import pipeline
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

# ---------------- Utility Functions ----------------

def sanitize(name):
    # Replace underscores/dashes, trim whitespace, remove illegal chars, collapse spaces
    name = re.sub(r'[_\-]+', ' ', name)
    name = re.sub(r'[\\/:*?"<>|]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name or 'file'

# Free AI model
ai = pipeline("text2text-generation", model="google/flan-t5-small")

def get_title(text):
    prompt = f"Extract the exact and complete document title from the following text. The title may be long, so do not shorten it. Text: {text[:512]}"
    try:
        out = ai(prompt, max_new_tokens=60)[0]['generated_text'].strip()
        # Capitalize properly
        return out.title()
    except:
        # Fallback first line if error
        line = text.strip().splitlines()[0]
        return sanitize(line)[:60]

# ---------------- GUI App ----------------

class PDFRenamerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Folder Renamer – AI Enhanced")
        self.geometry("900x500")
        self.files = []
        self.folder = ""
        self.setup_ui()

    def setup_ui(self):
        # Top buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Select Folder", command=self.select_folder).pack(side=tk.LEFT, padx=5)
        self.start_btn = ttk.Button(btn_frame, text="Start Renaming", state=tk.DISABLED, command=self.start)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        # Progress bar
        self.progress = ttk.Progressbar(self, length=400)
        self.progress.pack(pady=5)

        # File table
        cols = ("old", "new", "status")
        self.tree = ttk.Treeview(self, columns=cols, show='headings', height=15)
        for c, w in zip(cols, (300, 300, 150)):
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=w)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def select_folder(self):
        folder = filedialog.askdirectory(title="Choose PDF folder")
        if not folder: return
        self.folder = folder
        self.files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
        self.tree.delete(*self.tree.get_children())
        for f in self.files:
            self.tree.insert('', 'end', values=(f, "", "Pending"))
        self.start_btn.config(state=tk.NORMAL)
        self.progress['value'] = 0

    def start(self):
        self.start_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.rename_all, daemon=True).start()

    def rename_all(self):
        total = len(self.files)
        for idx, fname in enumerate(self.files):
            item = self.tree.get_children()[idx]
            self.tree.see(item)
            self.tree.selection_set(item)
            self.tree.set(item, "status", "Processing")

            old_path = os.path.join(self.folder, fname)
            with fitz.open(old_path) as doc:
                text = doc[0].get_text().strip()
            title = get_title(text if text else fname)

            safe = sanitize(title)
            new_name = safe + ".pdf"
            new_path = os.path.join(self.folder, new_name)
            cnt = 1
            while os.path.exists(new_path):
                new_name = f"{safe} {cnt}.pdf"
                new_path = os.path.join(self.folder, new_name)
                cnt += 1

            try:
                os.rename(old_path, new_path)
                self.tree.set(item, "new", new_name)
                self.tree.set(item, "status", "Done")
            except Exception as e:
                self.tree.set(item, "status", f"Error")
                print("Rename error:", e)

            # Update progress bar
            self.progress['value'] = ((idx + 1) / total) * 100

        messagebox.showinfo("Complete", "All files processed.")
        self.start_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    PDFRenamerApp().mainloop()
