import google.generativeai as genai
import json
import re
import base64
import io
from PIL import Image
from django.conf import settings

def get_ai_analysis(product_name, profile_data):
    # Use the key from settings
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
    # model = genai.GenerativeModel('gemini-2.5-flash')
    
    # # Try flash first, fallback to pro if the 404 error persists
    # try:
    #     model = genai.GenerativeModel('gemini-pro')
    # except:
    #     model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Return ONLY a raw JSON object for the product "{product_name}".
    User Profile: Allergies({profile_data.get('allergies')}), Restrictions({profile_data.get('restrictions')}), Goals({profile_data.get('health_goals')}).

    JSON Structure:
    {{
        "rating": "Green" or "Amber" or "Red",
        "score": 0-100,
        "summary": "Explain safety vs allergies in 2 sentences."
    }}
    """
    
    response = model.generate_content(prompt)
    
    try:
        # Use RegEx to find the JSON block even if AI adds extra text
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"rating": "Amber", "score": 50, "summary": "Analysis format error."}
    except Exception as e:
        print(f"Parsing error: {e}")
        return {"rating": "Red", "score": 0, "summary": "Could not analyze this product."}

def detect_allergens_logic(ingredients_text, profile_data):
    """
    Personalized AI scan comparing ingredients against the user's specific profile.
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
    
    # We include user profile context in the prompt
    prompt = f"""
    You are a food safety expert. Scan the following ingredient list:
    "{ingredients_text}"

    USER PROFILE:
    - Allergies: {profile_data.get('allergies')}
    - Restrictions: {profile_data.get('restrictions')}

    INSTRUCTIONS:
    1. Identify general allergens (Milk, Eggs, Peanuts, Wheat, etc.).
    2. Identify specific ingredients that conflict with the USER PROFILE.
    3. Return a JSON object with two lists:
       - "general": Common allergens found.
       - "critical": Allergens specifically matching the user's profile.
    
    Format: {{"general": ["item1"], "critical": ["item2"]}}
    If none, return empty lists.
    """
    
    try:
        response = model.generate_content(prompt)
        # Extract JSON using RegEx to handle any extra AI text
        import re, json
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"general": [], "critical": []}
    except Exception as e:
        print(f"Error: {e}")
        return {"general": [], "critical": []}

def analyze_food_image(base64_str, user_profile):
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Remove header
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]

    img_data = base64.b64decode(base64_str)
    img = Image.open(io.BytesIO(img_data))

    prompt = f"""
    Analyze this food label. User profile: {user_profile}.
    Return JSON ONLY: {{"verdict": "SAFE/UNSAFE", "analysis": "Reason"}}
    """

    response = model.generate_content([prompt, img])
    return response.text