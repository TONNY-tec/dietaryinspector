import google.generativeai as genai
import json
import re
from django.conf import settings
from PIL import Image
import base64
import io

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

def analyze_food_label(image_base64, user_profile_text):
    """
    Analyzes food labels using the google-generativeai library.
    """
    # 1. Setup the API Key
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    # 2. Initialize the Model
    model = genai.GenerativeModel('gemini-pro-vision')

    # 3. Clean the base64 string
    if "base64," in image_base64:
        image_base64 = image_base64.split("base64,")[1]
    
    image_bytes = base64.b64decode(image_base64)
    img = Image.open(io.BytesIO(image_bytes))

    # 4. Create the specialized prompt
    prompt = f"""
    User Health Profile: {user_profile_text}
    
    Instructions:
    1. Read the ingredients from this image.
    2. Determine if the product is SAFE, UNSAFE, or CAUTION based on the profile.
    3. Return ONLY a JSON object with keys "verdict" and "analysis".
    """

    # 5. Generate content (Older library uses a list for multimodal)
    response = model.generate_content([prompt, img])

    return response.text




# def analyze_food_label(image_base64, user_profile_text):
#     """
#     Decodes a base64 image and sends it to Gemini for dietary analysis.
#     """
#     # 1. Initialize the Gemini Client
#     client = genai.Client(api_key=settings.GEMINI_API_KEY)

#     # 2. Decode the Base64 string into bytes
#     # Remove the 'data:image/jpeg;base64,' prefix if it exists
#     if "base64," in image_base64:
#         image_base64 = image_base64.split("base64,")[1]
    
#     image_bytes = base64.b64decode(image_base64)
#     img = Image.open(io.BytesIO(image_bytes))

#     # 3. Create the prompt based on User Profile
#     prompt = f"""
#     You are an expert Kenyan Dietary Assistant. 
#     Analyze the provided image of a food ingredient label.
#     User Profile: {user_profile_text}
    
#     Tasks:
#     1. Identify any ingredients that are dangerous for this user.
#     2. Provide a 'verdict' (SAFE, UNSAFE, or CAUTION).
#     3. Provide a brief 1-sentence analysis.
    
#     Return ONLY a JSON object like this:
#     {{"verdict": "UNSAFE", "analysis": "Contains wheat which triggers your Celiac disease."}}
#     """

#     # 4. Call Gemini 1.5 Flash (Optimized for speed/images)
#     response = client.models.generate_content(
#         model="gemini-1.5-flash",
#         contents=[prompt, img]
#     )

#     return response.text