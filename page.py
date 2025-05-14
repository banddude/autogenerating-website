import sys
import os
import json
from openai import OpenAI
import re

# --- CONFIGURATION LOADING --- START --- 
CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'config.json')


config = CONFIG_FILE_PATH
try:
    with open(CONFIG_FILE_PATH, 'r') as f:
        config = json.load(f)
    # print(f"page.py: Successfully loaded configuration from {CONFIG_FILE_PATH}", file=sys.stderr)
except FileNotFoundError:
    print(f"page.py Warning: {CONFIG_FILE_PATH} not found. Using default configuration.", file=sys.stderr)
except json.JSONDecodeError as e:
    print(f"page.py Error decoding {CONFIG_FILE_PATH}: {e}. Using default configuration.", file=sys.stderr)
except Exception as e:
    print(f"page.py An unexpected error occurred loading {CONFIG_FILE_PATH}: {e}. Using default configuration.", file=sys.stderr)

LLM_MODEL = config.get("llm_model")
WEBSITE_PROFILE = config.get("website_profile")
SYSTEM_PROMPT_TEMPLATE = config.get("system_prompt_template")
# --- CONFIGURATION LOADING --- END --- 

client = OpenAI() # Assumes OPENAI_API_KEY is in environment

def generate_llm_content(current_path_for_content):
    """Generates only the main HTML content snippet for a given path using the LLM."""
    
    llm_path_query = current_path_for_content.strip('/') if current_path_for_content != '/' else 'homepage'
    if not llm_path_query: # Handles cases where path might become empty after stripping, e.g. if original was just '/'
        llm_path_query = 'homepage'

    profile = WEBSITE_PROFILE
    try:
        formatted_system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            company_name=profile.get("company_name", "Our Company"),
            business_type=profile.get("business_type", "Our Business"),
            location=profile.get("location", "Our Location"),
            specialties_list=", ".join(profile.get("specialties", [])),
            values_list=", ".join(profile.get("values", [])),
            target_audience=profile.get("target_audience", "Our Customers"),
            site_tone=profile.get("site_tone", "default"),
            current_page_path_for_llm=llm_path_query
        )
        print(f"page.py DEBUG: Formatted System Prompt for path '{llm_path_query}':\\n---START PROMPT---\\n{formatted_system_prompt}\\n---END PROMPT---", file=sys.stderr) # DEBUG LINE
    except KeyError as e:
        print(f"page.py Error: Missing key in website_profile for system prompt formatting: {e}. Using basic prompt.", file=sys.stderr)
        formatted_system_prompt = f"You are a content writer. Generate minimal HTML main content for a page about '{llm_path_query}'. No images or external links. Only p, h1, h2, h3, ul, ol, li tags."
    
    user_request_llm = f"Provide the main HTML content for the '{llm_path_query}' page, adhering to all instructions in the system prompt."

    main_content_html = ""
    try:
        # print(f"page.py: Sending request to LLM for path: '{llm_path_query}' with prompt: {formatted_system_prompt[:100]}...", file=sys.stderr)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": formatted_system_prompt},
                {"role": "user", "content": user_request_llm}
            ]
        )
        main_content_html = response.choices[0].message.content
        
        # --- Start Content Extraction/Cleanup ---
        # Attempt to remove any outer html/body/main tags to get only the inner content.
        # This makes the LLM output more robust to accidental full-page generation.
        temp_content = main_content_html.strip()
        
        # Try to find content within <main> tags first
        main_match = re.search(r"<main[^>]*>(.*?)</main>", temp_content, re.IGNORECASE | re.DOTALL)
        if main_match:
            temp_content = main_match.group(1).strip()
        else:
            # If no <main>, try to find content within <body> tags
            body_match = re.search(r"<body[^>]*>(.*?)</body>", temp_content, re.IGNORECASE | re.DOTALL)
            if body_match:
                print(f"page.py Warning: LLM returned content with <body> but no <main> for '{llm_path_query}'. Extracted from <body>.", file=sys.stderr)
                temp_content = body_match.group(1).strip()
            elif temp_content.lower().startswith("<!doctype html>") or temp_content.lower().startswith("<html>"):
                print(f"page.py Warning: LLM returned full HTML document for '{llm_path_query}' but couldn't find <main> or <body>. Setting to empty.", file=sys.stderr)
                temp_content = "" # Return empty string
            # If it wasn't a full doc but some other structure we didn't want, it remains temp_content
        
        main_content_html = temp_content
        # --- End Content Extraction/Cleanup ---

        if not main_content_html.strip(): # If after all that, it's empty
            print(f"page.py: Content for '{llm_path_query}' is empty after generation/cleanup. Returning empty string.", file=sys.stderr)
            main_content_html = "" # Return empty string

    except Exception as e:
        print(f"page.py Error calling OpenAI API for path '{current_path_for_content}': {e}. Returning empty string.", file=sys.stderr)
        main_content_html = "" # Return empty string
    
    return main_content_html

if __name__ == "__main__":
    path_arg = "/"
    if len(sys.argv) > 1:
        path_arg = sys.argv[1]
        if path_arg == '' and len(sys.argv) == 2:
            path_arg = '/'
    
    print(f"--- page.py direct execution for path: '{path_arg}' ---", file=sys.stderr)
    generated_content = generate_llm_content(path_arg)
    print(f"--- Generated Content Snippet (length: {len(generated_content)}) ---", file=sys.stderr)
    print(generated_content) # Output the HTML snippet to stdout
    print("--- End of page.py direct execution ---", file=sys.stderr) 