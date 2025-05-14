import sys
import os
import json
from openai import OpenAI
import re

# --- CONFIGURATION LOADING --- START --- 
CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
DEFAULT_CONFIG = {
    "llm_model": "gpt-4.1-nano",
    "website_profile": {
        "company_name": "Shaffer Con Inc. (Default)",
        "business_type": "Electrical Services (Default)",
        "location": "Our Town (Default)",
        "specialties": ["General electrical work"],
        "values": ["Quality", "Reliability"],
        "target_audience": "Everyone (Default)",
        "site_tone": "Professional and friendly (Default)"
    },
    "system_prompt_template": "You are a content writer for {company_name}. Please write concise HTML content for the path '{current_page_path_for_llm}'. No images or external links. Focus on text content using p, h2, h3, ul, ol, li. Provide ONLY the HTML for the main content block."
}

config = DEFAULT_CONFIG
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

LLM_MODEL = config.get("llm_model", DEFAULT_CONFIG["llm_model"])
WEBSITE_PROFILE = config.get("website_profile", DEFAULT_CONFIG["website_profile"])
SYSTEM_PROMPT_TEMPLATE = config.get("system_prompt_template", DEFAULT_CONFIG["system_prompt_template"])
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
        
        # Basic validation/cleanup: ensure it's not trying to be a full document.
        if main_content_html.strip().lower().startswith("<!doctype html>") or "<body" in main_content_html.lower():
            print(f"page.py Warning: LLM returned full document structure for '{llm_path_query}'. Attempting to extract main content or providing error.", file=sys.stderr)
            # This is a simplistic extraction attempt, might need more robust parsing
            body_match = re.search(r"<body[^>]*>(.*?)</body>", main_content_html, re.IGNORECASE | re.DOTALL)
            main_match = re.search(r"<main[^>]*>(.*?)</main>", main_content_html, re.IGNORECASE | re.DOTALL)
            if main_match:
                main_content_html = main_match.group(1)
            elif body_match:
                main_content_html = body_match.group(1) # Fallback to body if main not found
            else: # If cannot extract, fallback to an error message to avoid breaking the page structure.
                main_content_html = "<h1>Content Error</h1><p>The AI tried to generate a full page instead of content. Please try again or check template.</p>"

        if not main_content_html.strip(): # If after all that, it's empty
             main_content_html = f"<h1>{llm_path_query.title()}</h1><p>Content is being generated for this page.</p>"

    except Exception as e:
        print(f"page.py Error calling OpenAI API for path '{current_path_for_content}': {e}. Using fallback content.", file=sys.stderr)
        title = llm_path_query.replace('_',' ').title()
        main_content_html = f"<h2>Error Generating Content for {title}</h2><p>Could not load content due to an API error or unexpected issue. Details: {str(e)}</p>"
    
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