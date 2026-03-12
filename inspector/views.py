from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate, logout
from django.contrib.auth import logout as auth_logout
from .forms import StyledLoginForm, StyledSignupForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import ProfileUpdateForm

from .utils import get_ai_analysis, detect_allergens_logic, analyze_food_image
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

@csrf_exempt
def scan_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_data = data.get('image')

            # Get response from AI
            result = analyze_food_image(image_data, "User has nut allergies")
            
            # This links to your Gemini AI logic
            clean_json = result.replace('```json', '').replace('```', '').strip()
            
            # 3. Parse and return
            return JsonResponse(json.loads(clean_json))
            
        except Exception as e:
            # This print will show the REAL error in your Cloud Shell terminal
            print(f"Server-side Error: {str(e)}")
            return JsonResponse({"verdict": "ERROR", "analysis": str(e)}, status=500)