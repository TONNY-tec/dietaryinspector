import google.generativeai as genai
import json
import re
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

def detect_allergens_logic(ingredients_text):
    """
    Expert AI scan of raw ingredient text to find hidden allergens.
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
    
    prompt = f"""
    You are a food safety expert. Scan the following ingredient list for potential allergens:
    "{ingredients_text}"

    Instructions:
    1. Identify common allergens (Milk, Eggs, Peanuts, Tree Nuts, Fish, Shellfish, Soy, Wheat, etc.).
    2. Identify hidden derivatives (e.g., Whey = Milk, Lecithin = Soy).
    3. Return ONLY a comma-separated list of the allergen names found.
    4. If none are found, return the word "None".
    """
    
    response = model.generate_content(prompt)
    result = response.text.strip()
    
    # Handle empty or "None" responses from AI
    if result.lower() == "none" or not result:
        return []
        
    # Clean and split the comma-separated string into a Python list
    return [item.strip() for item in result.split(',')]