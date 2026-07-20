import google.generativeai as genai

def configure_genai(api_key: str) -> None:
    """Configures the google-generativeai package.
    
    If the key starts with 'AQ.', it is wrapped in an OAuth2 Credentials object
    to ensure it is passed via the 'Authorization: Bearer' header, preventing
    invalid credential errors at Google's API gateway.
    """
    if not api_key:
        return
    clean_key = api_key.strip()
    if clean_key.startswith("AQ."):
        from google.oauth2.credentials import Credentials
        creds = Credentials(token=clean_key)
        genai.configure(credentials=creds)
    else:
        genai.configure(api_key=clean_key)
