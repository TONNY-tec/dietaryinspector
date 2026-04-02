import google.generativeai as genai
import json
import re
import base64
import io
from PIL import Image
from django.conf import settings

# INDUSTRY BEST PRACTICE: Define a Master System Instruction 
# Grounding the model in clinical standards (USDA/WHO) to prevent hallucinations.
SYSTEM_BEHAVIOR = """
Role: Senior Clinical Dietitian & Food Safety Expert.
Knowledge Base: USDA FoodData Central, WHO Nutritional Guidelines, and Global Culinary Database.
Strict Protocols:
1. VERIFICATION: Do not hallucinate. Use conservative estimates based on standard food categories if specific data is missing.
2. CULTURAL CONTEXT: Recognize and accurately evaluate regional dishes (e.g., Jollof, Miso, Injera, Fufu, Mediterranean diets).
3. PERSONALIZATION: Prioritize medical-grade constraints (Diabetes, Hypertension, Celiac) and specific diets (Keto, Vegan, Paleo) over general advice.
4. ITERATIVE LOGIC (3-Turn Check): 
   - Step 1: Analyze ingredients/intent. 
   - Step 2: Cross-check against user profile & clinical limits (e.g., Sodium/Sugar). 
   - Step 3: Propose nutrient-dense alternatives if the primary item is high-risk.
"""

def get_ai_analysis(product_name, profile_data):
    """
    Enhanced Analysis: Maps products against USDA standards and identifies hidden additives.
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
     
    prompt = f"""
    {SYSTEM_BEHAVIOR}
    
    ANALYSIS REQUEST:
    Product: "{product_name}"
    User Profile: {profile_data}
    
    TASK:
    - Map this product against USDA nutritional standards.
    - Check for 'Hidden' ingredients (e.g., Maltodextrin, High Fructose Corn Syrup).
    - Rate safety: Green (Safe), Amber (Caution), Red (High Risk).
    
    RETURN ONLY JSON:
    {{
        "rating": "Green/Amber/Red",
        "emoji": "😊/⚠️/🤢",
        "score": 0-100,
        "summary": "Clinical summary (max 2 sentences).",
        "cultural_note": "Context regarding regional variations if applicable."
    }}
    """ 
    try:
        response = model.generate_content(prompt)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"rating": "Amber", "emoji": "⚠️", "score": 50, "summary": "Verification pending."}
    except Exception as e:
        print(f"Analysis Error: {e}")
        return {"rating": "Red", "emoji": "❌", "score": 0, "summary": "Analysis service error."}

def detect_allergens_logic(ingredients_text, profile_data):
    """
    Deep Personalization: Identifies chemical synonyms and cross-contamination risks.
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
 
    prompt = f"""
    {SYSTEM_BEHAVIOR}
    
    INGREDIENTS: "{ingredients_text}"
    USER CONSTRAINTS: {profile_data}
    
    TASK:
    - Identify cross-contamination risks ('May contain traces of...').
    - Identify chemical synonyms (e.g., 'Casein' or 'Whey' for Milk allergies).
    - Identify ingredients conflicting with medical conditions (e.g., High Sodium for Hypertension).
    
    RETURN ONLY JSON:
    {{"general": ["Allergen1"], "critical": ["UserMatch"], "emoji": "🚨/✅"}}
    """
    
    try:
        response = model.generate_content(prompt)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"general": [], "critical": [], "emoji": "❓"}
    except Exception as e:
        return {"general": [], "critical": [], "emoji": "❌"}

def analyze_food_image(base64_str, user_profile):
    """
    Computer Vision Enhancement: Compensates for lighting/angles to improve recognition.
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)

    if "," in base64_str:
        base64_str = base64_str.split(",")[1]

    try:
        img_data = base64.b64decode(base64_str)
        img = Image.open(io.BytesIO(img_data))

        prompt = f"""
        {SYSTEM_BEHAVIOR}
        
        VISUAL INSPECTION:
        Analyze this food label/product. Compensate for lighting, glare, and angles.
        Cross-reference detected ingredients with WHO sodium/sugar limits.
        User Profile: {user_profile}

        RETURN ONLY JSON:
        {{
            "verdict": "SAFE/CAUTION/UNSAFE",
            "emoji": "😊/⚠️/🤢",
            "analysis": "Explanation using clinical standards."
        }}
        """

        response = model.generate_content([prompt, img])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return match.group() if match else response.text
    except Exception as e:
        return json.dumps({"verdict": "ERROR", "emoji": "❌", "analysis": "Label unreadable."})

def get_ai_recommendations(user_query, user_profile):
    """
    Recommendation Engine: Hybrid filtering using content-based and goal-alignment logic.
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
    
    prompt = f"""
    {SYSTEM_BEHAVIOR}
    
    ITERATIVE RECOMMENDATION (3-Turn Protocol):
    1. Intent: Analyze {user_query}.
    2. Nutrient Audit: Verify against {user_profile} (Calories, Macros, Restrictions).
    3. Alternative Logic: Pivot to culturally relevant, low-calorie, or medical-compliant options if needed.
    
    RETURN ONLY JSON LIST:
    [
        {{
            "food_name": "Name",
            "vibe_emoji": "🥗",
            "reason_why": "Benefit (e.g., High Fiber, Low GI).",
            "comparison": "Why this is superior to common alternatives."
        }}
    ]
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean potential markdown formatting
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        match = re.search(r'\[.*\]', clean_text, re.DOTALL)
        return match.group() if match else "[]"
    except Exception as e:
        print(f"Rec Error: {e}")
        return "[]"