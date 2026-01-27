import calendar
from decimal import Decimal
from django.utils import timezone
from .models import Payslip

def calculate_payslip_breakdown(annual_ctc, worked_days, total_days, pf_enabled=True, location=None):
    """
    Calculates the payslip breakdown based on the user's provided logic.
    Integrates the specific formulas and rounding rules based on location.
    """
    # Convert inputs to float/Decimal
    if isinstance(annual_ctc, str):
        annual_ctc = annual_ctc.replace(",", "")
    annual_ctc = float(annual_ctc)
    worked_days = float(worked_days)
    total_days = int(total_days)

    # Determine location-specific logic
    country_code = "IN"
    currency_symbol = "₹"
    if location:
        if hasattr(location, 'country_code') and location.country_code:
            status_code = str(location.country_code).strip().upper()
            if status_code in ["BD", "BANGLADESH", "DHAKA"]:
                country_code = "BD"
            elif status_code in ["US", "USA", "UNITED STATES"]:
                country_code = "US"
            else:
                country_code = status_code
        elif isinstance(location, str):
            loc_str = location.strip().upper()
            if loc_str in ["BD", "BANGLADESH", "DHAKA"]:
                country_code = "BD"
            elif loc_str in ["US", "USA", "UNITED STATES"]:
                country_code = "US"
            else:
                country_code = loc_str
        
        # Determine currency symbol from location
        if hasattr(location, 'currency'):
            if location.currency == "USD":
                currency_symbol = "$"
            elif location.currency == "BDT":
                currency_symbol = "৳"
            elif location.currency == "INR":
                currency_symbol = "₹"
            else:
                currency_symbol = location.currency + " "

    def get_breakdown_logic(ctc_to_use, is_pf_enabled, country="IN"):
        """Helper to apply the specific calculation logic to a given CTC amount"""
        
        if country == "BD":
            # -------- Bangladesh (Dhaka) Logic --------
            gross_monthly = round(ctc_to_use, 2)
            basic = round(gross_monthly * 0.50, 2)
            hra = round(gross_monthly * 0.25, 2)  # House Rent
            medical = round(gross_monthly * 0.15, 2)
            conveyance = round(gross_monthly * 0.10, 2)
            
            lta = 0.00
            other_allowance = 0.00
            
            if is_pf_enabled:
                employee_pf = round(basic * 0.10, 2) # Typical BD PF is 10%
                employer_pf = employee_pf
            else:
                employee_pf = 0.00
                employer_pf = 0.00
                
            professional_tax = 0.00 # No PT in BD
            net_salary = round(gross_monthly - employee_pf, 2)
            
            return {
                "gross": gross_monthly,
                "basic": basic,
                "hra": hra,
                "medical": medical,
                "conveyance": conveyance,
                "lta": lta,
                "other_allowance": other_allowance,
                "employee_pf": employee_pf,
                "employer_pf": employer_pf,
                "professional_tax": professional_tax,
                "net_salary": net_salary
            }
        elif country == "US":
            # -------- US Logic (Simplified) --------
            # Typical US breakdown might vary, but we'll use a standard percentage
            gross_monthly = round(ctc_to_use, 2)
            basic = round(gross_monthly * 0.70, 2)
            hra = 0.00
            medical = round(gross_monthly * 0.15, 2)
            conveyance = 0.00
            lta = 0.00
            other_allowance = round(gross_monthly * 0.15, 2)
            
            # Simplified US Tax/Social Security (placeholder, usually handles via withholdings)
            # 7.65% for FICA (Social Security + Medicare)
            employee_pf = round(gross_monthly * 0.0765, 2)
            employer_pf = employee_pf
            professional_tax = 0.00
            
            # Total withholdings (Federal/State Tax placeholder - e.g. 20%)
            income_tax = round(gross_monthly * 0.15, 2)
            net_salary = round(gross_monthly - employee_pf - income_tax, 2)
            
            return {
                "gross": gross_monthly,
                "basic": basic,
                "hra": hra,
                "medical": medical,
                "conveyance": conveyance,
                "lta": lta,
                "other_allowance": other_allowance,
                "employee_pf": employee_pf,
                "employer_pf": employer_pf,
                "professional_tax": income_tax, # Mapping Federal/State Tax to Professional Tax field
                "net_salary": net_salary
            }
        else:
            # -------- India Logic (Default) --------
            if is_pf_enabled:
                # Step 1: Compute Gross from Monthly CTC
                gross_case1 = ctc_to_use / 1.065  # When Basic < 15000

                if gross_case1 < 30000:
                    gross_monthly = round(gross_case1, 2)
                    basic = round(gross_monthly * 0.50, 2)
                    employer_pf = round(basic * 0.13, 2)
                else:
                    employer_pf = 1950.00
                    gross_monthly = round(ctc_to_use - employer_pf, 2)
                    basic = round(gross_monthly * 0.50, 2)

                # Employee PF
                if basic < 15000:
                    employee_pf = round(basic * 0.12, 2)
                else:
                    employee_pf = 1800.00
            else:
                # -------- No PF --------
                gross_monthly = round(ctc_to_use, 2)
                basic = round(gross_monthly * 0.50, 2)
                employer_pf = 0.00
                employee_pf = 0.00

            # -------- Allowances --------
            hra = round(gross_monthly * 0.20, 2)
            lta = round(gross_monthly * 0.10, 2)
            other_allowance = round(gross_monthly - (basic + hra + lta), 2)

            # -------- Net Salary --------
            net_before_pt = round(gross_monthly - employee_pf, 2)

            # Professional Tax (Only for India)
            if country == "IN":
                professional_tax = 150 if net_before_pt < 20000 else 200
            else:
                professional_tax = 0.00

            # Net Take Home Salary
            net_salary = round(net_before_pt - professional_tax, 2)
            
            return {
                "gross": gross_monthly,
                "basic": basic,
                "hra": hra,
                "lta": lta,
                "other_allowance": other_allowance,
                "employee_pf": employee_pf,
                "employer_pf": employer_pf,
                "professional_tax": professional_tax,
                "net_salary": net_salary,
                "medical": 0.00,
                "conveyance": 0.00
            }

    # Monthly CTC (Full)
    full_monthly_ctc = round(annual_ctc / 12, 2)
    full_breakdown = get_breakdown_logic(full_monthly_ctc, pf_enabled, country_code)
    
    # Prorated Monthly CTC based on worked days
    if total_days > 0:
        monthly_ctc = round(full_monthly_ctc * (worked_days / total_days), 2)
        prorated_breakdown = get_breakdown_logic(monthly_ctc, pf_enabled, country_code)
    else:
        monthly_ctc = 0.0
        prorated_breakdown = {k: 0.0 for k in full_breakdown}

    return {
        "monthly_ctc": monthly_ctc,
        "full_monthly_ctc": full_monthly_ctc,
        "gross_monthly": prorated_breakdown["gross"],
        "full_monthly_gross": full_breakdown["gross"],
        "basic": prorated_breakdown["basic"],
        "hra": prorated_breakdown["hra"],
        "lta": prorated_breakdown["lta"],
        "medical": prorated_breakdown.get("medical", 0.00),
        "conveyance": prorated_breakdown.get("conveyance", 0.00),
        "other_allowance": prorated_breakdown["other_allowance"],
        "employee_pf": prorated_breakdown["employee_pf"],
        "employer_pf": prorated_breakdown["employer_pf"],
        "professional_tax": float(prorated_breakdown["professional_tax"]),
        "net_salary": prorated_breakdown["net_salary"],
        "worked_days": worked_days,
        "total_days": total_days,
        "pf_enabled": pf_enabled,
        "country_code": country_code,
        "currency_symbol": currency_symbol
    }



def num2words_flexible(number, currency="Rupees"):
    """
    Converts a number to words in Indian/South Asian numbering system
    """
    number = int(round(float(number)))
    if number == 0:
        return f"Zero {currency} only"
    
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    def convert_below_1000(n):
        res = ""
        if n >= 100:
            res += units[n // 100] + " Hundred "
            n %= 100
        if n >= 20:
            res += tens[n // 10] + " "
            n %= 10
        if n >= 10:
            res += teens[n - 10] + " "
            n = 0
        if n > 0:
            res += units[n] + " "
        return res

    res = ""
    temp_num = number
    
    if currency == "Dollars":
        # International System (Millions/Billions)
        # Billions
        if temp_num >= 1000000000:
            res += convert_below_1000(temp_num // 1000000000) + "Billion "
            temp_num %= 1000000000
        # Millions
        if temp_num >= 1000000:
            res += convert_below_1000(temp_num // 1000000) + "Million "
            temp_num %= 1000000
        # Thousands
        if temp_num >= 1000:
            res += convert_below_1000(temp_num // 1000) + "Thousand "
            temp_num %= 1000
        # Remaining
        res += convert_below_1000(temp_num)
    else:
        # Indian System (Lakhs/Crores)
        # Crores
        if temp_num >= 10000000:
            res += convert_below_1000(temp_num // 10000000) + "Crore "
            temp_num %= 10000000
        # Lakhs
        if temp_num >= 100000:
            res += convert_below_1000(temp_num // 100000) + "Lakh "
            temp_num %= 100000
        # Thousands
        if temp_num >= 1000:
            res += convert_below_1000(temp_num // 1000) + "Thousand "
            temp_num %= 1000
        # Remaining
        res += convert_below_1000(temp_num)
    
    return res.strip() + f" {currency} only"

# Mantain alias for backward compatibility if needed, though we will update views
def num2words_indian(number):
    return num2words_flexible(number, "Rupees")
