from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate, logout
from django.contrib.auth import logout as auth_logout
from .forms import StyledLoginForm, StyledSignupForm, ContactForm, UserUpdateForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .forms import ProfileUpdateForm
from django.core.mail import send_mail
from .utils import get_ai_analysis, detect_allergens_logic, analyze_food_image, get_ai_recommendations, get_guardian_conversation
import json
import random
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .decorators import premium_required
from .models import UserProfile, Scan, Recommendation
from django.shortcuts import render, redirect, get_object_or_404
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse


# Create your views here.
def index(request):
    analysis_result = None
    product_name = ""
    
    if request.method == 'POST':
        product_name = request.POST.get('product_name', '').strip()
        
        if product_name:
            if request.user.is_authenticated:
                profile = request.user.userprofile
                
                # CHECK PREMIUM LIMITS
                if not profile.can_scan():
                    messages.error(request, "Daily limit reached. Upgrade to Premium for unlimited searches!")
                    return redirect('pricing')
                
                # Perform Analysis
                profile_data = {
                    'allergies': profile.allergies,
                    'restrictions': profile.restrictions,
                    'health_goals': profile.health_goals
                }
                analysis_result = get_ai_analysis(product_name, profile_data)

                # INCREMENT COUNT ONLY FOR FREE USERS
                if not profile.is_premium:
                    profile.daily_scan_count += 1
                    profile.save()
            else:
                # Optional: Allow 1 anonymous scan or force login
                profile_data = {'allergies': 'None', 'restrictions': 'None', 'health_goals': 'None'}
                analysis_result = get_ai_analysis(product_name, profile_data)
            
    return render(request, 'index.html', {
        'result': analysis_result, 
        'product_name': product_name
    })

@login_required
def dashboard_view(request):
    profile = request.user.userprofile
    # Get all past scans for this specific user
    user_history = Recommendation.objects.filter(user=request.user)
    
    return render(request, 'dashboard.html', {
        'profile': profile,
        'recommendations': user_history
    })

@staff_member_required
def admin_dashboard(request):
    # Fetch all users and their associated profiles
    profiles = UserProfile.objects.select_related('user').all()
    
    context = {
        'profiles': profiles,
        'total_users': profiles.count(),
        'premium_users': profiles.filter(is_premium=True).count(),
    }
    return render(request, 'admin_dashboard.html', context)
from datetime import timedelta

@staff_member_required
def toggle_premium(request, profile_id):
    profile = get_object_or_404(UserProfile, id=profile_id)
    
    if not profile.is_premium:
        profile.is_premium = True
        profile.subscription_start_date = timezone.now() # Record start
        profile.subscription_end_date = timezone.now() + timedelta(days=30)
        messages.success(request, f"Premium granted to {profile.user.username}")
    else:
        profile.is_premium = False
        profile.subscription_start_date = None
        profile.subscription_end_date = None
        messages.info(request, f"Premium revoked for {profile.user.username}")
    
    profile.save()
    return redirect('admin_dashboard')
    
# inspector/views.py

def signup(request):
    if request.method == 'POST':
        form = StyledSignupForm(request.POST)
        if form.is_valid():
            # 1. Save user without committing to DB yet
            user = form.save(commit=False)
            
            # 2. Explicitly pull the email from the form and assign it to the user
            user.email = form.cleaned_data.get('email')
            user.save() 
            
            # 3. Create the UserProfile immediately (Required for OTP storage)
            # Use get_or_create to prevent errors if the profile already exists
            UserProfile.objects.get_or_create(user=user)
            
            messages.success(request, f"Account created for {user.username}! Please login to verify your email.")
            return redirect('login')
    else:
        form = StyledSignupForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = StyledLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # 1. Generate 6-digit OTP
            otp = str(random.randint(100000, 999999))
            
            # 2. Update/Create UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.otp_code = otp
            profile.otp_created_at = timezone.now()
            profile.is_verified = False
            profile.save()

            # 3. Send Email (Removing try/except temporarily to see the real error)
            subject = 'Dietary Inspector Verification Code'
            message = f'Habari {user.username}, your login verification code is: {otp}. It expires in 1 minute.'
            from_email = 'tonnysafari3@gmail.com' 
            recipient_list = [user.email]
            
            # If this fails, Django will now throw a massive error page—READ IT!
            # It will tell you if the password is wrong or the connection is blocked.
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            
            # 4. Store user ID and redirect
            request.session['pre_verify_user_id'] = user.id
            return redirect('verify_otp')
    else:
        form = StyledLoginForm()
    return render(request, 'login.html', {'form': form})

def verify_otp(request):
    user_id = request.session.get('pre_verify_user_id')
    if not user_id:
        return redirect('login')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp_code')
        try:
            user = User.objects.get(id=user_id)
            profile = user.userprofile

            if profile.otp_code == entered_otp:
                time_diff = timezone.now() - profile.otp_created_at
                if time_diff.total_seconds() < 60: # 1 minutes
                    auth_login(request, user)
                    profile.is_verified = True
                    profile.otp_code = None 
                    profile.save()
                    if 'pre_verify_user_id' in request.session:
                        del request.session['pre_verify_user_id']
                    return redirect('index')
                else:
                    messages.error(request, "Code has expired. Please login again.")
                    return redirect('login')
            else:
                messages.error(request, "Invalid verification code.")
        except User.DoesNotExist:
            return redirect('login')

    return render(request, 'verify_otp.html')

def logout_view(request):
    auth_logout(request)
    return redirect('index')
from .decorators import premium_required 


@login_required
def settings_view(request):
    if request.method == 'POST':
        # Check which form was submitted
        if 'update_profile' in request.POST:
            u_form = UserUpdateForm(request.POST, instance=request.user)
            if u_form.is_valid():
                u_form.save()
                messages.success(request, "Your account details have been updated!")
                return redirect('settings')
        
        elif 'change_password' in request.POST:
            p_form = PasswordChangeForm(request.user, request.POST)
            if p_form.is_valid():
                user = p_form.save()
                update_session_auth_hash(request, user)  # Keeps user logged in
                messages.success(request, "Your password was successfully updated!")
                return redirect('settings')
                
        elif 'delete_account' in request.POST:
            user = request.user
            user.delete()
            messages.warning(request, "Your account has been deleted.")
            return redirect('login')

    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = PasswordChangeForm(request.user)

    return render(request, 'settings.html', {
        'u_form': u_form,
        'p_form': p_form
    })


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
    profile = request.user.userprofile
    return render(request, 'scanner_componet.html')

@csrf_exempt
@login_required
def scan_api(request):
    if request.method == 'POST':
        try:
            profile = request.user.userprofile
            
            # 3. JSON RESPONSE FOR API (Scanner Component)
            if not profile.can_scan():
                return JsonResponse({
                    "verdict": "LIMIT_REACHED", 
                    "analysis": "You've used your 2 free scans for basic mode.",
                    "suggestion": "Upgrade to Premium for unlimited camera scanning.",
                    "upgrade_url": reverse('pricing')
                }, status=403)

            data = json.loads(request.body)
            image_data = data.get('image')
            user_context = f"Allergies: {profile.allergies}, Restrictions: {profile.restrictions}"
            result = analyze_food_image(image_data, user_context)
            
            if not profile.is_premium:
                profile.daily_scan_count += 1
                profile.save()

            return JsonResponse(json.loads(result.replace('```json', '').replace('```', '').strip()))
            
        except Exception as e:
            return JsonResponse({"verdict": "ERROR", "analysis": str(e)}, status=500)

@login_required
def recommendation_page(request):
    # Fetch history to display on the page if needed
    history = Recommendation.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'recommendation.html', {'history': history})

@csrf_exempt
@login_required
def recommend_api(request):
    if request.method == 'POST':
        profile = request.user.userprofile

        if not profile.can_scan():
            return JsonResponse({
                "error": "limit_reached",
                "message": "Daily free limit reached. Please upgrade to Premium."
            }, status=403)

        try:
            data = json.loads(request.body)
            user_query = data.get('query', '')
            user_profile_context = f"Allergies: {profile.allergies}. Restrictions: {profile.restrictions}. Goals: {profile.health_goals}."

            # Call AI
            recommendations_raw = get_ai_recommendations(user_query, user_profile_context)
            clean_json = recommendations_raw.replace('```json', '').replace('```', '').strip()
            
            # --- THE NEW PART: SAVE HISTORY ---
            Recommendation.objects.create(
                user=request.user,
                query_text=user_query,
                recommendation_text=clean_json
            )
            # ----------------------------------

            if not profile.is_premium:
                profile.daily_scan_count += 1
                profile.save()

            return JsonResponse({
                "recommendations": json.loads(clean_json),
                "scans_left": 2 - profile.daily_scan_count if not profile.is_premium else "Unlimited"
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@login_required
def delete_recommendation(request, pk):
    # Only allow the owner to delete
    recommendation = get_object_or_404(Recommendation, pk=pk, user=request.user)
    if request.method == 'POST':
        recommendation.delete()
    return redirect('dashboard') # Or whichever name your dashboard URL uses

@premium_required
def guardian_talk_api(request):
    """Handles the personalized 'Talk-to-Food' voice/text feature."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product = data.get('product', 'Unidentified')
            query = data.get('query', 'Is this safe?')
            
            # Fetch user's profile for the AI
            p = request.user.userprofile
            profile_context = {
                "allergies": p.allergies,
                "health_goals": p.health_goals,
                "restrictions": p.restrictions
            }
            
            # Get AI result
            result = get_guardian_conversation(product, query, profile_context)
            
            # Save to Database so it appears in the Admin History
            Scan.objects.create(
                user=request.user,
                product_name=f"Voice: {product}",
                rating=result.get('rating', 'Amber'),
                analysis_summary=result.get('summary', '')
            )
            
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "POST required"}, status=400)


def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_instance = form.save()
            
            # 1. Email to YOU (The Admin)
            admin_subject = f"New Suggestion: {contact_instance.subject}"
            admin_message = f"From: {contact_instance.name} ({contact_instance.email})\n\nMessage:\n{contact_instance.message}"
            send_mail(admin_subject, admin_message, 'tonnysafari3@gmail.com', ['tonnysafari3@gmail.com'])

            # 2. Confirmation Email to the USER
            user_subject = "We've received your message - DietaryInspector"
            user_message = f"""
                          Hi {contact_instance.name},

                          Thank you for reaching out to the DietaryInspector team. We have received your message and should expect a response from our team shortly.

                          PRIVACY NOTE: Your data has been processed in accordance with the Kenya Data Protection Act (2019).

                          Best Regards,
                          DietaryInspector Team
                          """
            send_mail(user_subject, user_message, 'tonnysafari3@gmail.com', [contact_instance.email])

            messages.success(request, "Your message has been sent successfully!")
            return redirect('contact')
    else:
        form = ContactForm()
    
    return render(request, 'contact.html', {'form': form})

@login_required
def pricing_view(request):
    return render(request, 'pricing.html')

@login_required
def initiate_stk_push(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        phone_number = data.get('phone')
        
        # M-Pesa logic starts here (Simplified for implementation)
        # You would typically call your Daraja API helper here
        # For now, we return a success response to trigger the UI loading state
        
        return JsonResponse({
            'status': 'success',
            'message': 'STK Push initiated successfully'
        })
    return JsonResponse({'status': 'error'}, status=400)

# 3. Callback URL (Where Safaricom sends payment results)
@csrf_exempt
@login_required
def mpesa_callback(request):
    if request.method == 'POST':
        callback_data = json.loads(request.body)
        
        # Logic to parse Safaricom's response
        # If ResultCode is 0 (Success):
        # 1. Identify the user via the checkout request ID
        # 2. Update UserProfile: is_premium = True
        # 3. Set subscription_end_date = timezone.now() + timedelta(days=30)
        
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})