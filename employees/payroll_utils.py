def calculate_payslip_breakdown(annual_ctc, worked_days, total_days, pf_enabled=True, location=None, company=None):
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
        if hasattr(location, "country_code") and location.country_code:
            status_code = str(location.country_code).strip().upper()
            if status_code in ["BD", "BANGLADESH", "DHAKA"]:
                country_code = "BD"
            elif status_code in ["US", "USA", "UNITED STATES"]:
                country_code = "US"
            elif status_code in ["IN", "INDIA", "INDIAN", "IND"]:
                country_code = "IN"
            else:
                country_code = status_code
        elif isinstance(location, str):
            loc_str = location.strip().upper()
            if loc_str in ["BD", "BANGLADESH", "DHAKA"]:
                country_code = "BD"
            elif loc_str in ["US", "USA", "UNITED STATES"]:
                country_code = "US"
            elif loc_str in ["IN", "INDIA", "INDIAN", "IND"]:
                country_code = "IN"
            else:
                country_code = loc_str
    # Determine currency symbol from location
    if hasattr(location, "currency"):
        if location.currency == "USD":
            currency_symbol = "$"
        elif location.currency == "BDT":
            currency_symbol = "৳"
        elif location.currency == "INR":
            currency_symbol = "₹"
        else:
            currency_symbol = location.currency + " "

    # Fetch company configuration
    from companies.models import PayrollConfiguration

    config = None
    target_company = company
    if not target_company and location and hasattr(location, "company"):
        target_company = location.company

    if target_company:
        config = PayrollConfiguration.objects.filter(company=target_company).first()

    def get_breakdown_logic(ctc_to_use, is_pf_enabled, country="IN"):
        """Helper to apply the specific calculation logic to a given CTC amount"""

        if country == "BD":
            # -------- Bangladesh (Dhaka) Logic --------
            basic_rate = float(config.bd_basic_percentage) / 100 if config else 0.50
            hra_rate = float(config.bd_hra_percentage) / 100 if config else 0.25
            med_rate = float(config.bd_medical_percentage) / 100 if config else 0.15
            conv_rate = float(config.bd_conveyance_percentage) / 100 if config else 0.10

            gross_monthly = float(round(ctc_to_use))
            basic = float(round(gross_monthly * basic_rate))
            hra = float(round(gross_monthly * hra_rate))  # House Rent
            medical = float(round(gross_monthly * med_rate))
            conveyance = float(round(gross_monthly * conv_rate))
            lta = 0.00
            other_allowance = 0.00

            if is_pf_enabled:
                employee_pf = float(round(basic * 0.10))  # Typical BD PF is 10%
                employer_pf = employee_pf
            else:
                employee_pf = 0.00
                employer_pf = 0.00

            professional_tax = 0.00  # No PT in BD
            net_salary = float(round(gross_monthly - employee_pf))

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
                "net_salary": net_salary,
            }
        elif country == "US":
            # -------- US Logic (Simplified) --------
            basic_rate = float(config.us_basic_percentage) / 100 if config else 0.70
            tax_rate = float(config.us_tax_percentage) / 100 if config else 0.15

            gross_monthly = float(round(ctc_to_use))
            basic = float(round(gross_monthly * basic_rate))
            hra = 0.00
            medical = float(round(gross_monthly * 0.15))
            conveyance = 0.00
            lta = 0.00
            other_allowance = float(round(gross_monthly - (basic + medical)))
            # Simplified US Tax/Social Security (placeholder, usually handles via withholdings)
            # 7.65% for FICA (Social Security + Medicare)
            employee_pf = float(round(gross_monthly * 0.0765))
            employer_pf = employee_pf
            professional_tax = 0.00
            # Total withholdings (Federal/State Tax placeholder)
            income_tax = float(round(gross_monthly * tax_rate))
            net_salary = float(round(gross_monthly - employee_pf - income_tax))

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
                "professional_tax": income_tax,  # Mapping Federal/State Tax to Professional Tax field
                "net_salary": net_salary,
            }
        else:
            # -------- India Logic (Default) --------
            # Rates from config
            b_pct = float(config.basic_percentage) / 100 if config else 0.50
            h_pct = float(config.hra_percentage) / 100 if config else 0.20
            l_pct = float(config.lta_percentage) / 100 if config else 0.10

            pf_er_rate = float(config.pf_employer_rate) / 100 if config else 0.13
            pf_ee_rate = float(config.pf_employee_rate) / 100 if config else 0.12
            pf_ceil = float(config.pf_ceiling) if config else 15000.0

            pt_thresh = float(config.pt_threshold) if config else 20000.0
            pt_low = float(config.pt_amount_below) if config else 150.0
            pt_high = float(config.pt_amount_above) if config else 200.0

            if is_pf_enabled:
                # Step 1: Compute Gross from Monthly CTC
                # Factor accounts for Employer PF being part of CTC
                pf_factor = 1 + (pf_er_rate * b_pct)
                gross_case1 = ctc_to_use / pf_factor

                if (gross_case1 * b_pct) < pf_ceil:
                    # Calculate basic from the fractional gross to maintain precision
                    basic = float(round(gross_case1 * b_pct))
                    employer_pf = float(round(basic * pf_er_rate))
                    # Derive gross_monthly from CTC to ensure they always add up perfectly
                    gross_monthly = float(ctc_to_use - employer_pf)
                else:
                    employer_pf = float(round(pf_ceil * pf_er_rate))
                    gross_monthly = float(round(ctc_to_use - employer_pf))
                    basic = float(round(gross_monthly * b_pct))

                # Employee PF
                employee_pf = (
                    float(round(basic * pf_ee_rate)) if basic < pf_ceil else float(round(pf_ceil * pf_ee_rate))
                )
            else:
                # -------- No PF --------
                gross_monthly = float(round(ctc_to_use))
                basic = float(round(gross_monthly * b_pct))
                employer_pf = 0.00
                employee_pf = 0.00

            # -------- Allowances --------
            hra = float(round(gross_monthly * h_pct))
            lta = float(round(gross_monthly * l_pct))
            other_allowance = float(round(gross_monthly - (basic + hra + lta)))

            # -------- Net Salary --------
            net_before_pt = float(round(gross_monthly - employee_pf))

            # Professional Tax (Only for India or Bluebix/SoftStandard entities)
            # Based on Gross Monthly Salary: 200 if >= 20000, 150 if < 20000
            is_special_entity = False
            if target_company:
                cname = str(target_company.name).upper()
                if "BLUEBIX" in cname or "SOFTSTANDARD" in cname:
                    is_special_entity = True

            should_apply_pt = country == "IN" or is_special_entity

            # Ensure we have valid rates even if config is partially set
            pt_thresh_val = pt_thresh if pt_thresh > 0 else 20000.0
            pt_low_val = pt_low if pt_low > 0 else 150.0
            pt_high_val = pt_high if pt_high > 0 else 200.0

            professional_tax = (
                (pt_low_val if gross_monthly < pt_thresh_val else pt_high_val) if should_apply_pt else 0.0
            )

            # Net Take Home Salary
            net_salary = float(round(net_before_pt - professional_tax))

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
                "conveyance": 0.00,
            }

    # Monthly CTC (Full)
    full_monthly_ctc = float(round(annual_ctc / 12))
    full_breakdown = get_breakdown_logic(full_monthly_ctc, pf_enabled, country_code)

    # Prorated Monthly CTC based on worked days
    if total_days > 0:
        monthly_ctc = float(round(full_monthly_ctc * (worked_days / total_days)))
        prorated_breakdown = get_breakdown_logic(monthly_ctc, pf_enabled, country_code)
    else:
        monthly_ctc = 0.0
        prorated_breakdown = dict.fromkeys(full_breakdown, 0.0)

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
        "currency_symbol": currency_symbol,
    }


def num2words_flexible(number, currency="Rupees"):
    """
    Converts a number to words in Indian/South Asian numbering system
    """
    number = int(round(float(number)))
    if number == 0:
        return f"Zero {currency} only"

    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = [
        "Ten",
        "Eleven",
        "Twelve",
        "Thirteen",
        "Fourteen",
        "Fifteen",
        "Sixteen",
        "Seventeen",
        "Eighteen",
        "Nineteen",
    ]
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
