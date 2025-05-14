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
    normalized_path = ('/' + path_param.strip('/')) if path_param and path_param != '/' else '/'

    cache_content_filename = sanitize_path_to_cache_filename(normalized_path)
    cache_content_filepath = os.path.join(CONTENT_CACHE_DIR, cache_content_filename)

    main_html_content = ""

    if os.path.exists(cache_content_filepath):
        try:
            with open(cache_content_filepath, 'r', encoding='utf-8') as f:
                main_html_content = f.read()
            # print(f"app.py (API): Served content for '{normalized_path}' from cache.", file=sys.stderr)
        except Exception as e:
            print(f"app.py (API) Error reading content cache for '{normalized_path}': {e}. Will try to regenerate.", file=sys.stderr)
            main_html_content = ""

    if not main_html_content.strip(): # If cache miss or cache read failed and main_html_content is empty
        # print(f"app.py (API): Content cache miss or empty for '{normalized_path}'. Calling page.generate_llm_content.", file=sys.stderr)
        try:
            main_html_content = generate_llm_content(normalized_path)
            if main_html_content.strip():
                try:
                    with open(cache_content_filepath, 'w', encoding='utf-8') as f:
                        f.write(main_html_content)
                    # print(f"app.py (API): Saved generated content for '{normalized_path}' to cache.", file=sys.stderr)
                except Exception as e:
                    print(f"app.py (API) Error writing content to cache for '{normalized_path}': {e}", file=sys.stderr)
            else:
                main_html_content = "" # Ensure empty if LLM provides no content
        except Exception as e:
            print(f"app.py (API) Exception calling generate_llm_content for '{normalized_path}': {e}", file=sys.stderr)
            main_html_content = "" # Ensure empty on error
    
    menu_items = get_menu_items_from_cache(normalized_path)

    return jsonify({
        "main_content_html": main_html_content.strip(),
        "menu_items": menu_items
    })

# Catch-all route to serve index.html for client-side routing
@app.route('/')
@app.route('/<path:text>')
def serve_index(text=None):
    path_param = text if text else '/'
    normalized_path = ('/' + path_param.strip('/')) if path_param and path_param != '/' else '/'

    main_html_content = "" # Default to empty string
    cache_content_filename = sanitize_path_to_cache_filename(normalized_path)
    cache_content_filepath = os.path.join(CONTENT_CACHE_DIR, cache_content_filename)

    if os.path.exists(cache_content_filepath):
        try:
            with open(cache_content_filepath, 'r', encoding='utf-8') as f:
                main_html_content = f.read()
            # print(f"app.py (SSR): Served content for '{normalized_path}' from cache: {cache_content_filepath}", file=sys.stderr)
        except Exception as e:
            print(f"app.py (SSR) Error reading content cache for '{normalized_path}': {e}. Will try to regenerate.", file=sys.stderr)
            main_html_content = "" # Ensure it is empty before regeneration attempt
            try:
                main_html_content = generate_llm_content(normalized_path)
                if main_html_content.strip(): # Check if content is not just whitespace
                    with open(cache_content_filepath, 'w', encoding='utf-8') as f:
                        f.write(main_html_content)
                else:
                    main_html_content = "" # Explicitly set to empty if LLM returns nothing
            except Exception as gen_e:
                print(f"app.py (SSR) Error during content regeneration: {gen_e}", file=sys.stderr)
                main_html_content = "" # Empty on error
    else:
        # print(f"app.py (SSR): Content cache miss for '{normalized_path}'. Calling page.generate_llm_content.", file=sys.stderr)
        try:
            main_html_content = generate_llm_content(normalized_path) 
            if main_html_content.strip(): # Check if content is not just whitespace
                try:
                    with open(cache_content_filepath, 'w', encoding='utf-8') as f:
                        f.write(main_html_content)
                    # print(f"app.py (SSR): Saved generated content for '{normalized_path}' to cache: {cache_content_filepath}", file=sys.stderr)
                except Exception as e:
                    print(f"app.py (SSR) Error writing content to cache for '{normalized_path}': {e}", file=sys.stderr)
            else:
                 main_html_content = "" # Explicitly set to empty if LLM returns nothing
        except Exception as e:
            print(f"app.py (SSR) Exception calling generate_llm_content for '{normalized_path}': {e}", file=sys.stderr)
            main_html_content = "" # Empty on error

    # The menu item generation should remain in get_page_data_endpoint, not here in serve_index for SSR.
    # For SSR, we only care about the main_html_content.

    try:
        index_html_path = os.path.join(os.path.dirname(__file__), 'index.html')
        with open(index_html_path, 'r', encoding='utf-8') as f:
            index_html_template = f.read()
        
        placeholder_with_fallback = "<!-- MAIN_CONTENT_SSR -->\n            <p>Loading page content...</p> <!-- This will be overwritten by SSR or client-side JS -->"
        final_html = index_html_template.replace(placeholder_with_fallback, main_html_content.strip())
        
        return final_html
    except Exception as e:
        print(f"app.py (SSR) Error reading or processing index.html template: {e}", file=sys.stderr)
        # Return the original template or a very basic error page if template processing fails, to avoid breaking site entirely
        try:
            return send_from_directory('.', 'index.html') # Fallback to serving raw index
        except Exception:
            return "<h1>Major Server Error</h1><p>Site template unrenderable.</p>", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3006, debug=True) 