import threading
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from companies.models import Company

_thread_locals = threading.local()

def get_current_company():
    """Get the current company from thread local storage"""
    return getattr(_thread_locals, 'company', None)

def get_current_user():
    """Get the current user from thread local storage"""
    return getattr(_thread_locals, 'user', None)

class CompanyIsolationMiddleware:
    """
    Multi-tenant middleware that:
    1. Identifies company by domain (e.g., petabytz.com, bluebix.com)
    2. Ensures complete data isolation between companies
    3. Validates user belongs to the correct company
    4. Enforces password change on first login
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def get_company_from_domain(self, request):
        """
        Identify company from the request domain
        Supports both primary domain and allowed domains
        """
        host = request.get_host().split(':')[0]  # Remove port if present
        
        # Try to find company by primary domain
        try:
            company = Company.objects.filter(primary_domain__iexact=host, is_active=True).first()
            if company:
                return company
        except Company.DoesNotExist:
            pass
        
        # Try to find by allowed domains
        for company in Company.objects.filter(is_active=True):
            if company.is_domain_allowed(host):
                return company
        
        # For development: if localhost or 127.0.0.1, try to get from user's email domain
        if host in ['localhost', '127.0.0.1']:
            return None  # Will be determined by user's company
        
        return None

    def __call__(self, request):
        # Store user in thread locals
        _thread_locals.user = getattr(request, 'user', None)
        
        # Get company from domain
        domain_company = self.get_company_from_domain(request)
        
        if request.user and request.user.is_authenticated:
            # Import User model to check role
            from accounts.models import User
            
            # Get current path
            path = request.path_info
            
            # Skip company validation for:
            # 1. Django admin panel (for superusers)
            # 2. Static/media files
            # 3. SuperAdmin custom portal
            # 4. Account management pages
            if (path.startswith('/admin/') or 
                path.startswith('/static/') or 
                path.startswith('/media/') or 
                path.startswith('/superadmin/') or
                path.startswith('/accounts/logout/') or
                path.startswith('/accounts/change-password/')):
                
                # Still store company info if available
                request.company = request.user.company or domain_company
                _thread_locals.company = request.company
                
                # Check password change requirement
                if request.user.must_change_password and \
                   not path.startswith('/accounts/logout/') and \
                   not path.startswith('/accounts/change-password/') and \
                   not path.startswith('/static/') and \
                   not path.startswith('/media/'):
                    return redirect('change_password')
                
                response = self.get_response(request)
                return response
            
            # Skip company validation for SUPERADMIN users (for non-admin paths)
            is_superadmin = hasattr(request.user, 'role') and request.user.role == User.Role.SUPERADMIN
            
            user_company = request.user.company
            
            # Validate user belongs to the correct company (if domain company is identified)
            if not is_superadmin and domain_company and user_company and domain_company.id != user_company.id:
                # User is trying to access wrong company's domain
                return HttpResponseForbidden(
                    f"Access Denied: You are not authorized to access {domain_company.name}. "
                    f"Please use your company's domain: {user_company.primary_domain}"
                )
            
            # Set company (prefer user's company for localhost development)
            request.company = user_company or domain_company
            _thread_locals.company = request.company
            
            # Validate user has a company assigned (skip for SUPERADMIN)
            if not is_superadmin and not request.company:
                return HttpResponseForbidden(
                    "Access Denied: Your account is not associated with any company. "
                    "Please contact your administrator."
                )
            
            # Force Password Change on First Login
            if request.user.must_change_password and \
               not path.startswith('/accounts/logout/') and \
               not path.startswith('/accounts/change-password/') and \
               not path.startswith('/static/') and \
               not path.startswith('/media/'):
                return redirect('change_password')
        
        else:
            # For unauthenticated users, store domain company for login page customization
            request.company = domain_company
            _thread_locals.company = domain_company
        
        response = self.get_response(request)
        return response
