
# -------------------------------------------------------------------------
# Forgot Password / OTP Flow
# -------------------------------------------------------------------------

def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            
            # Generate 6-digit OTP
            otp = str(random.randint(100000, 999999))
            
            # Save OTP
            PasswordResetOTP.objects.create(user=user, otp=otp)
            
            # Send Email (Mock)
            print(f"--------------------------------------------------")
            print(f"MOCK EMAIL SENT TO: {email}")
            print(f"OTP: {otp}")
            print(f"--------------------------------------------------")
            
            request.session['reset_email'] = email
            messages.success(request, f"OTP sent to {email}. Please check your console (dev) or inbox.")
            return redirect('verify_otp')
    else:
        form = ForgotPasswordForm()
    
    return render(request, 'core/forgot_password.html', {'form': form})

def verify_otp_view(request):
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, "Session expired. Please try again.")
        return redirect('forgot_password')
    
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp_input = form.cleaned_data['otp']
            user = User.objects.get(email=email)
            
            # Verify OTP (check latest for user)
            otp_record = PasswordResetOTP.objects.filter(user=user).last()
            
            if otp_record and otp_record.otp == otp_input:
                otp_record.is_verified = True
                otp_record.save()
                
                request.session['otp_verified'] = True
                messages.success(request, "OTP Verified Successfully.")
                return redirect('reset_password')
            else:
                messages.error(request, "Invalid OTP.")
    else:
        form = OTPVerificationForm()
    
    return render(request, 'core/verify_otp.html', {'form': form, 'email': email})

def reset_password_view(request):
    email = request.session.get('reset_email')
    is_verified = request.session.get('otp_verified')
    
    if not email or not is_verified:
        messages.error(request, "Unauthorized access. Please verify OTP first.")
        return redirect('forgot_password')
    
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user = User.objects.get(email=email)
            
            user.set_password(new_password)
            user.save()
            
            # Clear session
            del request.session['reset_email']
            del request.session['otp_verified']
            
            messages.success(request, "Password reset successfully. You can now login.")
            return redirect('login') # Assuming 'login' is the name of your login url
    else:
        form = ResetPasswordForm()
    
    return render(request, 'core/reset_password.html', {'form': form})
