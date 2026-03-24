from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate, logout
from django.contrib.auth import logout as auth_logout
from .forms import StyledLoginForm, StyledSignupForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import ProfileUpdateForm

from .utils import get_ai_analysis, detect_allergens_logic, analyze_food_image, get_ai_recommendations
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt



# Create your views here.
def index(request):
    analysis_result = None
    product_name = ""
    
    if request.method == 'POST':
        # Ensure the 'name' attribute in your HTML is exactly 'product_name'
        product_name = request.POST.get('product_name', '').strip()
        
        if product_name:
            # Fetch profile for the logged-in user
            if request.user.is_authenticated:
                p = request.user.userprofile
                profile_data = {
                    'allergies': p.allergies,
                    'restrictions': p.restrictions,
                    'health_goals': p.health_goals
                }
            else:
                profile_data = {'allergies': 'None', 'restrictions': 'None', 'health_goals': 'None'}
            
            # Call the updated utility function
            analysis_result = get_ai_analysis(product_name, profile_data)
            
    return render(request, 'index.html', {
        'result': analysis_result, 
        'product_name': product_name
    })

def signup(request):
    if request.method == 'POST':
        form = StyledSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('login')
    else:
        form = StyledSignupForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = StyledLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('index')
    else:
        form = StyledLoginForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    auth_logout(request)
    return redirect('index')


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been successfully updated!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user.userprofile)
    
    return render(request, 'profile.html', {'form': form})


@login_required
def allergen_detector_view(request):
    results = {"general": [], "critical": []}
    ingredients = ""
    has_searched = False

    if request.method == 'POST':
        ingredients = request.POST.get('ingredients', '').strip()
        if ingredients:
            # 1. Fetch the user's profile for personalization
            profile = request.user.userprofile
            profile_data = {
                'allergies': profile.allergies,
                'restrictions': profile.restrictions
            }
            
            # 2. Pass profile data to the logic function
            results = detect_allergens_logic(ingredients, profile_data)
            has_searched = True

    return render(request, 'allergen.html', {
        'results': results, # Now contains both general and critical
        'ingredients': ingredients,
        'has_searched': has_searched
    })

def scanner_componet(request):
    return render(request, 'scanner_componet.html')

def scan_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_data = data.get('image')

            # Get the real profile if logged in
            if request.user.is_authenticated:
                user_profile = f"Allergies: {request.user.userprofile.allergies}, Restrictions: {request.user.userprofile.restrictions}"
            else:
                user_profile = "User has general health goals."

            # Call Gemini logic
            result = analyze_food_image(image_data, user_profile)
            
            clean_json = result.replace('```json', '').replace('```', '').strip()
            return JsonResponse(json.loads(clean_json))
            
        except Exception as e:
            print(f"CRITICAL ERROR: {str(e)}") # This prints to your terminal
            return JsonResponse({"verdict": "ERROR", "analysis": "AI processing failed. Check terminal."}, status=500)

# @csrf_exempt
# def scan_api(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             image_data = data.get('image')

#             # Get response from AI
#             result = analyze_food_image(image_data, "User has nut allergies")
            
#             # This links to your Gemini AI logic
#             clean_json = result.replace('```json', '').replace('```', '').strip()
            
#             # 3. Parse and return
#             return JsonResponse(json.loads(clean_json))
            
#         except Exception as e:
#             # This print will show the REAL error in your Cloud Shell terminal
#             print(f"Server-side Error: {str(e)}")
#             return JsonResponse({"verdict": "ERROR", "analysis": str(e)}, status=500)
@login_required
def recommendation_page(request):
    return render(request, 'recommendation.html')

@csrf_exempt # Ensure this is present to allow POST requests from the browser
def recommend_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_query = data.get('query', '') 
            
            # Static profile for testing as per your code
            user_profile = "User has a severe nut allergy and is lactose intolerant." 
            
            # Call the AI logic
            recommendations_raw = get_ai_recommendations(user_query, user_profile)
            
            # CLEANING LOGIC: 
            # 1. Remove Markdown formatting if the AI includes it
            clean_json = recommendations_raw.replace('```json', '').replace('```', '').strip()
            
            # 2. Parse the cleaned string into a Python object
            response_data = json.loads(clean_json)
            
            # 3. Return as JsonResponse. Using safe=False if the AI returns a List []
            return JsonResponse(response_data, safe=False)
            
        except json.JSONDecodeError as json_err:
            # This captures if the AI output is still not valid JSON
            print(f"JSON Error: {str(json_err)}")
            return JsonResponse({"error": "The AI provided an unreadable response format."}, status=500)
        except Exception as e:
            # General catch-all for other errors (like API connectivity)
            print(f"Server Error: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({"error": "Invalid request method"}, status=400)