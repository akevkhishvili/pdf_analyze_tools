import fitz
import os
import sys
import subprocess
import requests
import csv
from urllib.parse import urlparse
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import re

# Utility to sanitize filenames
def sanitize_filename(name):
    # remove only invalid characters for file names, but keep spaces
    name = re.sub(r'[\\/:*?"<>|]', '', name)  # remove bad chars
    name = name.strip()
    return name or 'file'

class PDFLinkDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Link Downloader")
        self.geometry("900x550")
        self.resizable(False, False)

        self.cancel_flag = threading.Event()
        self.pdf_path = None
        self.links = []  # list of dicts: {'url':..., 'title':...}
        self.session = requests.Session()

        # Buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5)

        # Select PDF
        self.select_button = ttk.Button(btn_frame, text="Select PDF", command=self.select_pdf)
        self.select_button.pack(side=tk.LEFT, padx=5)

        # Download all
        self.download_button = ttk.Button(btn_frame, text="Download All", state=tk.DISABLED, command=self.start_downloads)
        self.download_button.pack(side=tk.LEFT, padx=5)

        # Cancel
        self.cancel_button = ttk.Button(btn_frame, text="Cancel", state=tk.DISABLED, command=self.cancel_downloads)
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        # Open folder
        self.open_button = ttk.Button(btn_frame, text="Open Folder", state=tk.DISABLED, command=self.open_folder)
        self.open_button.pack(side=tk.LEFT, padx=5)

        # Checkbox: name by URL
        self.use_url_name = tk.BooleanVar()
        self.url_name_checkbox = ttk.Checkbutton(
            btn_frame,
            text="Name files by URL",
            variable=self.use_url_name
        )
        self.url_name_checkbox.pack(side=tk.LEFT, padx=5)

        # Treeview for title, url, and progress
        columns = ("title", "url", "progress")
        self.tree = ttk.Treeview(self, columns=columns, show='headings')
        self.tree.heading('title', text='Title')
        self.tree.column('title', width=300)
        self.tree.heading('url', text='URL')
        self.tree.column('url', width=400)
        self.tree.heading('progress', text='Progress')
        self.tree.column('progress', width=150)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def select_pdf(self):
        path = filedialog.askopenfilename(title="Select PDF File", filetypes=[("PDF files","*.pdf")])
        if not path:
            return
        self.pdf_path = path
        self.load_links()

    def load_links(self):
        loader = tk.Toplevel(self)
        loader.title("Extracting...")
        loader.geometry("300x80")
        loader.resizable(False, False)
        ttk.Label(loader, text="Extracting links...").pack(pady=10)
        pb = ttk.Progressbar(loader, mode='indeterminate')
        pb.pack(fill=tk.X, padx=20, pady=5)
        pb.start(); loader.update()

        # Extract URL and link text
        doc = fitz.open(self.pdf_path)
        self.links.clear()
        seen_urls = set()
        for page in doc:
            for link in page.get_links():
                if 'uri' in link and urlparse(link['uri']).scheme in ('http', 'https'):
                    uri = link['uri']
                    if uri in seen_urls:
                        continue  # skip duplicate
                    seen_urls.add(uri)
                    rect = fitz.Rect(link['from'])
                    title = page.get_text('text', clip=rect).strip() or uri
                    self.links.append({'url': uri, 'title': title})
        doc.close()

        # Save CSV with title and url
        base = self.get_base_folder()
        csv_dir = os.path.join(base, 'dist/extracted')
        os.makedirs(csv_dir, exist_ok=True)
        csv_path = os.path.join(csv_dir, 'extracted_urls.csv')
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['title','url'])
                for ld in self.links:
                    w.writerow([ld['title'], ld['url']])
        except Exception as e:
            print(f"Error writing CSV: {e}")

        pb.stop(); loader.destroy()

        if not self.links:
            messagebox.showinfo("No Links", "No downloadable HTTP/HTTPS links found.")
            return

        # Populate treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, ld in enumerate(self.links):
            self.tree.insert('', 'end', iid=idx, values=(ld['title'], ld['url'], '0%'))

        self.download_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        self.open_button.config(state=tk.NORMAL)

    def get_base_folder(self):
        if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def start_downloads(self):
        self.select_button.config(state=tk.DISABLED)
        self.download_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.cancel_flag.clear()

        base = self.get_base_folder()
        save_dir = os.path.join(base, 'dist/extracted')
        os.makedirs(save_dir, exist_ok=True)

        threading.Thread(target=self.download_sequence, args=(save_dir,), daemon=True).start()

    def cancel_downloads(self):
        self.cancel_flag.set()
        self.cancel_button.config(state=tk.DISABLED)

    def download_sequence(self, save_dir):
        for idx, ld in enumerate(self.links):
            if self.cancel_flag.is_set(): break
            self.update_progress(idx, 0)
            self.download_file(ld, save_dir, idx)
        self.after(0, self.finish)

    def download_file(self, ld, save_dir, idx):
        url, title = ld['url'], ld['title']
        try:
            r = self.session.get(url, stream=True, timeout=10)
            r.raise_for_status()
            # filename logic
            if self.use_url_name.get():
                parsed = urlparse(url)
                name = sanitize_filename(parsed.netloc + parsed.path)
            else:
                name = sanitize_filename(title)
            dst = os.path.join(save_dir, name)
            # ensure extension if from url
            ext = os.path.splitext(urlparse(url).path)[1]
            if ext and not dst.lower().endswith(ext.lower()): dst += ext
            base, ext = os.path.splitext(dst)
            count=1
            while os.path.exists(dst): dst = f"{base}_{count}{ext}"; count+=1

            total = int(r.headers.get('content-length', 0))
            written = 0; last_pct = -1; chunk_size=8192
            with open(dst,'wb') as f:
                for chunk in r.iter_content(chunk_size):
                    if self.cancel_flag.is_set(): return
                    if chunk:
                        f.write(chunk)
                        if total:
                            written += len(chunk)
                            pct=int(written*100/total)
                            if pct!=last_pct:
                                last_pct=pct; self.update_progress(idx,pct)
            if total: self.update_progress(idx,100)
        except Exception:
            self.tree.set(idx,'progress','Error')

    def update_progress(self, idx, pct):
        self.tree.set(idx, 'progress', f"{pct}%")

    def open_folder(self):
        base = self.get_base_folder(); folder=os.path.join(base, 'dist/extracted')
        if not os.path.exists(folder):
            messagebox.showerror("Error", f"Folder not found: {folder}")
            return
        try:
            if os.name=='nt': os.startfile(folder)
            elif sys.platform=='darwin': subprocess.call(['open',folder])
            else: subprocess.call(['xdg-open',folder])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def finish(self):
        self.select_button.config(state=tk.NORMAL)
        self.download_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        if self.cancel_flag.is_set(): messagebox.showinfo("Cancelled","Downloads cancelled.")
        else: messagebox.showinfo("Done","All downloads complete.")

if __name__=='__main__': PDFLinkDownloaderApp().mainloop()
