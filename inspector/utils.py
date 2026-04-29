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
Role: Senior Clinical Dietitian & Food Safety Expert (Localized reasoning specialist).
Knowledge Base: USDA FoodData Central, WHO Nutritional Guidelines, Kenya Bureau of Standards (KEBS) Food Safety protocols, and Regional African Culinary Databases.

Strict Operational Protocols:
1. GEOGRAPHICAL SPECIFICITY: Prioritize regional food availability. When suggesting alternatives, suggest items accessible in the user's specific region (e.g., if in East Africa, suggest Managu or Sukuma Wiki over Kale; suggest Cassava or Arrowroots over imported oats). 

2. CLINICAL VERIFICATION: Do not hallucinate safety ratings. If a product’s specific chemical composition is unknown, use conservative "Amber" ratings and state the reason based on standard category risks.

3. CULTURAL & LINGUISTIC MAPPING: Correctly interpret regional names for dishes and ingredients (e.g., Matoke, Ugali, Githeri, Nyama Choma). Recognize that nutritional density varies based on local preparation methods.

4. MULTI-LAYERED REASONING (3-Step Audit): 
   - Step 1 (Extraction): Identify raw ingredients and E-number additives from the input.
   - Step 2 (Clinical Check): Cross-reference ingredients against the User's Profile (Allergies: {allergies}, Goals: {goals}, Conditions: {conditions}). 
   - Step 3 (Localized Verdict): Assign a Safety Rating (Red/Amber/Green) and propose a nutrient-dense alternative that is EASILY AVAILABLE in the user's current geography.

5. OUTPUT FORMAT: Always return structured JSON with: rating, summary (plain language), emoji, and localized_alternative.
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
    Analyze the attached image of a food label. 
    Even if the image is slightly blurry or has glare, please attempt to extract 
    the ingredients. If parts are missing, provide a warning but do not just 
    return 'Unreadable'.
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

# def analyze_food_image(base64_str, user_profile):
#     genai.configure(api_key=settings.GEMINI_API_KEY)
#     # Ensure you are using a vision-capable model like 'gemini-1.5-flash'
#     model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)

#     if "," in base64_str:
#         base64_str = base64_str.split(",")[1]

#     try:
#         # 1. Prepare image correctly for Gemini
#         img_data = base64.b64decode(base64_str)
#         image_parts = [
#             {
#                 "mime_type": "image/jpeg",
#                 "data": img_data
#             }
#         ]

#         # 2. Stronger Prompt with explicit JSON formatting instructions
#         prompt = f"""
#         Act as a clinical dietitian. Analyze this food label image.
#         User Health Context: {user_profile}

#         Instructions:
#         1. Extract all visible ingredients.
#         2. Identify allergens or high-risk additives based on the user profile.
#         3. Even if blurry, give your best professional estimate.

#         Return ONLY a valid JSON object in this exact format:
#         {{
#             "verdict": "SAFE", 
#             "emoji": "😊",
#             "analysis": "Provide a detailed clinical explanation here."
#         }}
#         """

        # 3. Generate content using the proper image part format
    #     response = model.generate_content([prompt, image_parts[0]])
        
    #     # 4. Clean the response text (remove markdown code blocks if present)
    #     clean_text = response.text.replace('```json', '').replace('```', '').strip()
        
    #     # 5. Attempt to find JSON if there is extra text
    #     match = re.search(r'\{.*\}', clean_text, re.DOTALL)
    #     if match:
    #         return match.group()
        
    #     return clean_text

    # except Exception as e:
    #     # DEBUG: This will print the ACTUAL error to your terminal/console
    #     print(f"REAL ERROR: {str(e)}") 
    #     return json.dumps({
    #         "verdict": "ERROR", 
    #         "emoji": "❌", 
    #         "analysis": f"AI Processing Error: {str(e)}"
    #     })

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

def get_guardian_conversation(product_name, user_query, profile_data):
    """
    New Feature: Handles natural language 'Talk-to-Food' questions.
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
     
    prompt = f"""
    {SYSTEM_BEHAVIOR}
    
    USER PROFILE: {profile_data}
    PRODUCT: "{product_name}"
    USER ASKED: "{user_query}"
    
    TASK:
    - Analyze the query against the product and user profile.
    - Rate safety: Green (Safe), Amber (Caution), Red (High Risk).
    
    RETURN ONLY JSON:
    {{
        "rating": "Green/Amber/Red",
        "emoji": "🛡️",
        "score": 0-100,
        "summary": "Direct conversational answer (max 2 sentences).",
        "alternative": "A safer specific product suggestion.",
        "warning_label": "Short label (e.g., 'High Sugar' or 'Allergen Match')"
    }}
    """ 
    try:
        response = model.generate_content(prompt)
        # Cleaning logic to handle potential markdown
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"rating": "Amber", "emoji": "⚠️", "summary": "I'm having trouble analyzing that. Please try again."}
    except Exception as e:
        return {"rating": "Red", "emoji": "❌", "summary": f"Guardian service error: {str(e)}"}