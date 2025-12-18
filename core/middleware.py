import threading

_thread_locals = threading.local()

def get_current_company():
    return getattr(_thread_locals, 'company', None)

def get_current_user():
    return getattr(_thread_locals, 'user', None)

class CompanyIsolationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, 'user', None)
        if request.user and request.user.is_authenticated:
            # 1. Company Isolation
            request.company = request.user.company
            _thread_locals.company = request.user.company
            
            # 2. Force Password Change on First Login
            # Check if current path is NOT logout or change-password to avoid loops
            from django.shortcuts import redirect
            
            path = request.path_info
            # Check for force password change flag
            # We must allow access to logout, change-password, and statics
            if request.user.must_change_password and \
               not path.startswith('/accounts/logout/') and \
               not path.startswith('/accounts/change-password/') and \
               not path.startswith('/static/'):
                   return redirect('change_password')

        else:
            request.company = None
            if hasattr(_thread_locals, 'company'):
                del _thread_locals.company

        response = self.get_response(request)
        return response
