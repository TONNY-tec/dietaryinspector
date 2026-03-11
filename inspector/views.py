import json
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate, logout
from django.contrib.auth import logout as auth_logout
from .forms import StyledLoginForm, StyledSignupForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .forms import ProfileUpdateForm
from django.http import JsonResponse
from .utils import get_ai_analysis, detect_allergens_logic, analyze_food_label


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


def scanner_page(request):
    """Renders the HTML page with the camera UI"""
    return render(request, 'scanner.html')

@csrf_exempt # Use this for testing, but ideally use CSRF tokens in production
def scan_api(request):
    if request.method == 'POST':
        try:
            # Check if the body is empty
            if not request.body:
                return JsonResponse({"verdict": "ERROR", "analysis": "No data received"}, status=400)

            data = json.loads(request.body)
            image_data = data.get('image')

            if not image_data:
                return JsonResponse({"verdict": "ERROR", "analysis": "No image found in request"}, status=400)

            # Define user_info so the code doesn't crash if Profile is missing
            user_info = "User has general health interests. Check for common allergens like nuts, dairy, and gluten."

            # Optional: Try to get real user profile if it exists
            if request.user.is_authenticated:
                try:
                    user_info = f"Allergies: {request.user.userprofile.allergies}. Restrictions: {request.user.userprofile.restrictions}. Health Goals: {request.user.userprofile.health_goals}"
                except AttributeError:
                    pass # Fallback to default user_info if userprofile doesn't exist for some reason

            # Call the AI logic from utils.py
            ai_response_raw = analyze_food_label(image_data, user_info)

            # Clean and parse the AI response
            clean_json = ai_response_raw.replace('```json', '').replace('```', '').strip()
            result = json.loads(clean_json)

            return JsonResponse(result)

        except Exception as e:
            # This prints the error to your Cloud Shell terminal so you can see it!
            print(f"--- SCANNER ERROR: {str(e)} ---")
            return JsonResponse({"verdict": "ERROR", "analysis": f"Backend Error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only POST requests allowed"}, status=405)