from flask import Flask, request, jsonify, send_from_directory
import subprocess
import os
import sys
import re
import json # Required if page.py direct call output needs parsing, though not for current plan

# Import the function directly from page.py
from page import generate_llm_content 

app = Flask(__name__, static_folder='static')

# Cache directory for LLM-generated content snippets
CONTENT_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
if not os.path.exists(CONTENT_CACHE_DIR):
    os.makedirs(CONTENT_CACHE_DIR)
    print(f"Created content cache directory: {CONTENT_CACHE_DIR}", file=sys.stderr)

# Determine the correct python interpreter path for the venv
# This assumes app.py is in the project root alongside the venv directory
VENV_PYTHON = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'python')
if not os.path.exists(VENV_PYTHON):
    # Fallback for environments where venv might not be directly in bin (e.g. Windows)
    # or if the script is run from a different working directory structure.
    # This is a basic fallback; a more robust solution might be needed for complex setups.
    VENV_PYTHON = 'python' # Fallback to just 'python', hoping it's the venv one or PATH is set
    print(f"Warning: venv python interpreter not found at default location. Falling back to '{VENV_PYTHON}'. Ensure it's the correct one.", file=sys.stderr)

def sanitize_path_to_filename(path):
    """Converts a URL path to a safe filename."""
    if not path or path == '/':
        path = 'index'
    # Remove leading/trailing slashes and replace others with underscores
    filename = path.strip('/').replace('/', '_')
    # Remove characters not safe for filenames
    filename = re.sub(r'[^a-zA-Z0-9_\-. ]', '', filename)
    return f"{filename}.html"

def sanitize_path_to_cache_filename(path_str):
    """Converts a URL path to a safe filename for content snippets."""
    if not path_str or path_str == '/':
        filename_base = 'index'
    else:
        filename_base = path_str.strip('/').replace('/', '_')
    filename_base = re.sub(r'[^a-zA-Z0-9_\-]', '', filename_base)
    return f"{filename_base}_content.html"

def path_to_display_name(path_str):
    """Converts a path to a human-readable name for the menu."""
    if not path_str or path_str == '/':
        return "Home"
    return path_str.strip('/').replace('_', ' ').replace('-',' ').title()

def get_menu_items_from_cache(current_path):
    """Scans the content cache directory and builds a list of menu items."""
    menu = []
    # Ensure current path is represented, even if not cached yet (will be after LLM call)
    # This makes it appear in the menu on first load.
    current_path_normalized = ('/' + current_path.strip('/')) if current_path and current_path != '/' else '/'
    
    # Temporary set to track paths to avoid duplicates from different sanitization stages
    processed_paths_for_menu = {current_path_normalized}
    menu.append({
        "name": path_to_display_name(current_path_normalized),
        "path": current_path_normalized,
        "is_current": True
    })

    for filename in os.listdir(CONTENT_CACHE_DIR):
        if filename.endswith("_content.html"):
            # Infer original path from filename
            original_path_base = filename[:-len("_content.html")]
            if original_path_base == 'index':
                original_path = '/'
            else:
                original_path = '/' + original_path_base.replace('_', '/')
            
            if original_path not in processed_paths_for_menu:
                menu.append({
                    "name": path_to_display_name(original_path),
                    "path": original_path,
                    "is_current": False
                })
                processed_paths_for_menu.add(original_path)
    
    menu.sort(key=lambda x: (x['path'] != '/', x['name']))
    return menu

@app.route('/get_page_data')
def get_page_data_endpoint():
    path_param = request.args.get('path', '/')
    # Normalize path for consistency (e.g. ensure leading slash, handle empty as root)
    normalized_path = ('/' + path_param.strip('/')) if path_param and path_param != '/' else '/'

    cache_content_filename = sanitize_path_to_cache_filename(normalized_path)
    cache_content_filepath = os.path.join(CONTENT_CACHE_DIR, cache_content_filename)

    main_html_content = ""
    menu_items = []

    if os.path.exists(cache_content_filepath):
        try:
            with open(cache_content_filepath, 'r', encoding='utf-8') as f:
                main_html_content = f.read()
            print(f"app.py: Served content for '{normalized_path}' from cache: {cache_content_filepath}", file=sys.stderr)
        except Exception as e:
            print(f"app.py Error reading content cache for '{normalized_path}': {e}. Will try to regenerate.", file=sys.stderr)
            main_html_content = "" # Force regeneration

    if not main_html_content:
        print(f"app.py: Content cache miss for '{normalized_path}'. Calling page.generate_llm_content.", file=sys.stderr)
        try:
            # page.py is now a module, call its function directly
            main_html_content = generate_llm_content(normalized_path) 
            if main_html_content:
                try:
                    with open(cache_content_filepath, 'w', encoding='utf-8') as f:
                        f.write(main_html_content)
                    print(f"app.py: Saved generated content for '{normalized_path}' to cache: {cache_content_filepath}", file=sys.stderr)
                except Exception as e:
                    print(f"app.py Error writing content to cache for '{normalized_path}': {e}", file=sys.stderr)
            else:
                 main_html_content = "<h1>Error</h1><p>Failed to generate content for this page.</p>"
        except Exception as e:
            print(f"app.py Exception calling generate_llm_content for '{normalized_path}': {e}", file=sys.stderr)
            main_html_content = f'<h1>Server Error</h1><p>Error during content generation: {str(e)}</p>'
    
    # Always generate menu items fresh after content handling, so it reflects the current cache state
    menu_items = get_menu_items_from_cache(normalized_path)

    return jsonify({
        "main_content_html": main_html_content,
        "menu_items": menu_items
    })

# Catch-all route to serve index.html for client-side routing
@app.route('/')
@app.route('/<path:text>')
def serve_index(text=None):
    # This ensures that index.html is served for any path, allowing client-side routing to take over.
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3006, debug=True) 