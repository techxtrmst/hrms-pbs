from accounts.models import LinkedAccount, User


def linked_accounts_context(request):
    """
    Context processor to provide linked accounts for the account switcher.
    Supports seamless 1-click switching between accounts across different entities.
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {
            "linked_accounts": [],
            "other_linked_accounts": [],
            "has_other_accounts": False,
        }

    current_user = request.user
    session_accounts = request.session.get("linked_accounts", [])

    # Color palette matching the UI design
    COLOR_PALETTES = [
        {"bg": "#e0f2fe", "text": "#0284c7", "badge_bg": "#f0f9ff"},  # Blue (Petabytz)
        {"bg": "#dcfce7", "text": "#16a34a", "badge_bg": "#f0fdf4"},  # Green (Bluebix)
        {"bg": "#ffedd5", "text": "#d97706", "badge_bg": "#fff7ed"},  # Amber (Attest)
        {"bg": "#ede9fe", "text": "#7c3aed", "badge_bg": "#f5f3ff"},  # Purple (Softstandard)
        {"bg": "#ffe4e6", "text": "#e11d48", "badge_bg": "#fff1f2"},  # Rose
        {"bg": "#ccfbf1", "text": "#0d9488", "badge_bg": "#f0fdfa"},  # Teal
    ]

    def get_color_scheme(name, idx=0):
        name_lower = (name or "").lower()
        if "softstandard" in name_lower:
            return {"bg": "#ede9fe", "text": "#7c3aed", "badge_bg": "#f5f3ff"}
        elif "petabytz" in name_lower:
            return {"bg": "#e0f2fe", "text": "#0284c7", "badge_bg": "#f0f9ff"}
        elif "bluebix" in name_lower:
            return {"bg": "#dcfce7", "text": "#16a34a", "badge_bg": "#f0fdf4"}
        elif "attest" in name_lower:
            return {"bg": "#ffedd5", "text": "#d97706", "badge_bg": "#fff7ed"}
        return COLOR_PALETTES[idx % len(COLOR_PALETTES)]

    # Helper to extract user profile details
    def get_user_data(u, is_current=False, idx=0):
        avatar_url = ""
        designation = ""
        if hasattr(u, "employee_profile") and u.employee_profile:
            designation = u.employee_profile.designation or ""
            if u.employee_profile.profile_picture:
                try:
                    avatar_url = u.employee_profile.profile_picture.url
                except Exception:
                    avatar_url = ""

        company_name = u.company.name if u.company else "HRMS Portal"
        role_display = u.get_role_display() if hasattr(u, "get_role_display") else u.role
        colors = get_color_scheme(company_name, idx)

        return {
            "user_id": u.id,
            "email": u.email,
            "full_name": u.get_full_name() or u.username,
            "company_name": company_name,
            "company_slug": u.company.slug if u.company else "",
            "role": u.role,
            "role_display": role_display,
            "designation": designation,
            "avatar_url": avatar_url,
            "is_current": is_current,
            "theme_bg": colors["bg"],
            "theme_text": colors["text"],
            "theme_badge_bg": colors["badge_bg"],
        }

    # Fetch database-backed linked account user IDs
    db_linked_user_ids = list(
        LinkedAccount.objects.filter(primary_user=current_user, linked_user__is_active=True)
        .order_by("created_at")
        .values_list("linked_user_id", flat=True)
    )

    # Also include any user IDs currently in session
    session_user_ids = [acc.get("user_id") for acc in session_accounts if isinstance(acc, dict) and "user_id" in acc]

    # Combine unique user IDs with current_user first, then DB-linked, then session-linked
    combined_user_ids = []
    seen = set()
    for uid in [current_user.id] + db_linked_user_ids + session_user_ids:
        if uid and uid not in seen:
            seen.add(uid)
            combined_user_ids.append(uid)

    # Validate all user IDs against active DB users
    active_users = {
        u.id: u
        for u in User.objects.filter(id__in=combined_user_ids, is_active=True).select_related(
            "company", "employee_profile"
        )
    }

    valid_linked_accounts = []
    other_linked_accounts = []
    session_data = []

    for i, uid in enumerate(combined_user_ids):
        if uid in active_users:
            u = active_users[uid]
            is_curr = u.id == current_user.id
            acc_data = get_user_data(u, is_current=is_curr, idx=i)
            valid_linked_accounts.append(acc_data)
            session_data.append(acc_data)
            if not is_curr:
                other_linked_accounts.append(acc_data)

    # Sync back to session so request.session has the fresh list
    request.session["linked_accounts"] = session_data

    # Compute current user data with theme
    current_account_data = get_user_data(current_user, is_current=True, idx=0)

    return {
        "current_account_data": current_account_data,
        "linked_accounts": valid_linked_accounts,
        "other_linked_accounts": other_linked_accounts,
        "has_other_accounts": len(other_linked_accounts) > 0,
    }
