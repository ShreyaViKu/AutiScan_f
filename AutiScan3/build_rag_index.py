import os
import re
import json
import html
from html.parser import HTMLParser
import google.generativeai as genai
from dotenv import load_dotenv

# Load env variables for Gemini API key
load_dotenv()
api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print("Error: GEMINI_API_KEY not found in environment.")
    exit(1)

genai.configure(api_key=api_key)

class AutismHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks = []
        self.current_title = ""
        self.current_header = ""
        self.current_text = []
        self.in_ignored = False
        # Ignore scripts, styles, header nav, and footer to focus on main content
        self.ignored_tags = {'script', 'style', 'header', 'footer', 'nav', 'head'}
        self.current_tag = None
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag in self.ignored_tags:
            self.in_ignored = True
            
        # Class check for nav elements we might have missed
        # e.g., knowledge-nav, sidebar-nav
        for name, value in attrs:
            if name == 'class' and any(x in value for x in ['nav', 'sidebar', 'menu', 'footer']):
                self.in_ignored = True
            
        # A new header starts a new section chunk
        if tag in ['h1', 'h2', 'h3', 'h4']:
            self.save_current_chunk()
            
    def handle_endtag(self, tag):
        if tag in self.ignored_tags:
            self.in_ignored = False
        self.current_tag = None
        
    def handle_data(self, data):
        if self.in_ignored:
            return
        
        # Clean up whitespace and HTML entities
        data = html.unescape(data)
        data = re.sub(r'\s+', ' ', data).strip()
        if not data:
            return
            
        if self.current_tag in ['h1', 'h2', 'h3', 'h4']:
            self.current_header = data
        else:
            self.current_text.append(data)
            
    def save_current_chunk(self):
        if self.current_text:
            text_content = "\n".join(self.current_text).strip()
            # Filter out boilerplate, short navigation fragments, or footer links
            if text_content and len(text_content) > 30 and not text_content.startswith("Start Screening"):
                self.chunks.append({
                    "title": self.current_title,
                    "header": self.current_header or "General Information",
                    "content": text_content
                })
            self.current_text = []

    def get_all_chunks(self, title):
        self.current_title = title
        self.save_current_chunk()
        return self.chunks

def parse_html_file(filepath):
    print(f"Parsing: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Extract Title using Regex
    title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
    title = title_match.group(1).replace(" | AutiScan", "").replace("AutiScan", "").strip() if title_match else ""
    if not title:
        title = os.path.basename(filepath).replace(".html", "").replace("-", " ").title()
        
    parser = AutismHTMLParser()
    parser.feed(html_content)
    return parser.get_all_chunks(title)

def build_index():
    base_dir = "c:/Users/SHREYA/Desktop/AS_try/autiscan-tool/AutiScan3"
    
    files_to_index = [
        "templates/autism/what-is-autism.html",
        "templates/autism/signs-and-symptoms.html",
        "templates/autism/causes-of-autism.html",
        "templates/autism/autism-screening.html",
        "templates/autism/autism-diagnosis.html",
        "templates/autism/vaccines-and-autism.html",
        "templates/therapies.html",
        "templates/about.html",
        "templates/awareness.html"
    ]
    
    all_chunks = []
    for rel_path in files_to_index:
        full_path = os.path.join(base_dir, rel_path)
        if os.path.exists(full_path):
            file_chunks = parse_html_file(full_path)
            for chunk in file_chunks:
                chunk["source_file"] = rel_path
                all_chunks.append(chunk)
        else:
            print(f"Warning: File not found {full_path}")
            
    print(f"Total chunks extracted: {len(all_chunks)}")
    
    if not all_chunks:
        print("No content chunks extracted. Exiting.")
        return
        
    # Generate embeddings in batches of 50
    batch_size = 50
    embeddings = []
    
    print("Generating embeddings using models/gemini-embedding-2...")
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i+batch_size]
        texts = [f"{c['title']} - {c['header']}\n{c['content']}" for c in batch]
        
        try:
            response = genai.embed_content(
                model="models/gemini-embedding-2",
                content=texts,
                task_type="retrieval_document"
            )
            batch_embeddings = response['embedding']
            embeddings.extend(batch_embeddings)
            print(f"Embedded batch {i//batch_size + 1}/{((len(all_chunks)-1)//batch_size) + 1} ({len(batch)} items)")
        except Exception as e:
            print(f"Error embedding batch: {e}")
            # Try embedding individually as fallback
            print("Attempting individual embeddings fallback for this batch...")
            for item in texts:
                try:
                    response = genai.embed_content(
                        model="models/gemini-embedding-2",
                        content=item,
                        task_type="retrieval_document"
                    )
                    embeddings.append(response['embedding'])
                except Exception as ex:
                    print(f"Failed to embed item: {item[:50]}... | Error: {ex}")
                    # Append zero vector as fallback
                    embeddings.append([0.0] * 3072)
                    
    # Associate embeddings back to chunks
    for chunk, emb in zip(all_chunks, embeddings):
        chunk["embedding"] = emb
        
    # Save index to json
    output_path = os.path.join(base_dir, "rag_index.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
        
    print(f"Success! Saved RAG index with {len(all_chunks)} chunks to {output_path}")

if __name__ == "__main__":
    build_index()
