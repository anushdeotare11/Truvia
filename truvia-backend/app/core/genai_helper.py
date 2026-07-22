import google.generativeai as genai

def configure_genai(api_key: str) -> None:
    """Configures the google-generativeai package with the API key."""
    if not api_key:
        return
    clean_key = api_key.strip()
    genai.configure(api_key=clean_key)

