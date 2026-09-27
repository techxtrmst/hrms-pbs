def calculate_payslip_breakdown(
    annual_ctc,
    worked_days,
    total_days,
    pf_enabled=True,
    location=None,
    company=None,
    month=None,
    year=None,
    travel_allowance=0.0,
    tds_deduction=0.0,
    arrears=0.0,
):
    """
    Calculates the payslip breakdown based on the user's provided logic.
    Integrates the specific formulas and rounding rules based on location.

    Payroll cycle rule (India):
      Cycle runs from 27th of previous month → 28th of current month.
      - total_days for calculation  = days in the PREVIOUS month
        (e.g. April payroll → March has 31 days → total_days = 31)
      - display_days (shown in PDF) = days in the CURRENT month (April = 30)
      - absent_days  = display_days - entered_worked_days
      - actual_worked_days = total_days - absent_days
      So entering 29 for April (display=30, cycle=31) gives:
        absent=1, actual_worked=30, gross = round(monthly × 30/31)
    """
    travel_allowance = float(travel_allowance or 0.0)
    tds_deduction = float(tds_deduction or 0.0)
    arrears = float(arrears or 0.0)
    import calendar as _calendar

    # Convert inputs to float/Decimal
    if isinstance(annual_ctc, str):
        annual_ctc = annual_ctc.replace(",", "")
    annual_ctc = float(annual_ctc)
    worked_days = float(worked_days)
    total_days = int(total_days)

    # ----------------------------------------------------------------
    # Payroll-cycle adjustment (only when month+year are provided)
    # ----------------------------------------------------------------
    display_days = total_days  # days in current month (for PDF label)
    cycle_total_days = total_days  # days used for proration denominator

    if month is not None and year is not None:
        month = int(month)
        year = int(year)
        # Previous month
        if month == 1:
            prev_month, prev_year = 12, year - 1
        else:
            prev_month, prev_year = month - 1, year
        cycle_total_days = _calendar.monthrange(prev_year, prev_month)[1]
        display_days = _calendar.monthrange(year, month)[1]

    # Convert entered worked_days (out of display_days) to actual worked days
    # (out of cycle_total_days) by preserving the number of absent days.
    absent_days = display_days - worked_days
    actual_worked_days = cycle_total_days - absent_days

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
            lta = conveyance
            other_allowance = 0.00
            special_allowance = 0.00

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
                "conveyance_allowance": conveyance,
                "lta": lta,
                "special_allowance": special_allowance,
                "other_allowance": other_allowance,
                "employee_pf": employee_pf,
                "employer_pf": employer_pf,
                "professional_tax": professional_tax,
                "net_salary": net_salary,
            }
        else:
            # -------- Standard / India / US / Global Logic --------
            # Rates: Basic 50%, HRA 20%, Conveyance Allowance 20%, Special Allowance remainder (10%)
            b_pct = float(config.basic_percentage) / 100 if config and config.basic_percentage else 0.50
            h_pct = float(config.hra_percentage) / 100 if config and config.hra_percentage else 0.20
            conv_pct = 0.20
            if (
                config
                and hasattr(config, "lta_percentage")
                and config.lta_percentage
                and float(config.lta_percentage) not in [10.0, 0.0]
            ):
                conv_pct = float(config.lta_percentage) / 100

            pf_er_rate = float(config.pf_employer_rate) / 100 if config and config.pf_employer_rate else 0.13
            pf_ee_rate = float(config.pf_employee_rate) / 100 if config and config.pf_employee_rate else 0.12
            pf_ceil = float(config.pf_ceiling) if config and config.pf_ceiling else 15000.0

            pt_thresh = float(config.pt_threshold) if config and config.pt_threshold else 20000.0
            pt_low = float(config.pt_amount_below) if config and config.pt_amount_below else 150.0
            pt_high = float(config.pt_amount_above) if config and config.pt_amount_above else 200.0

            gross_monthly = float(round(ctc_to_use))

            # -------- Earnings Breakdown --------
            basic = float(round(gross_monthly * b_pct))
            hra = float(round(gross_monthly * h_pct))
            conveyance = float(round(gross_monthly * conv_pct))
            # Special allowance is the exact remainder so earnings add up perfectly to gross_monthly
            special_allowance = float(round(gross_monthly - (basic + hra + conveyance)))
            lta = conveyance
            other_allowance = special_allowance

            # -------- Provident Fund --------
            if is_pf_enabled:
                if basic >= pf_ceil:
                    # PF is capped at standard rates (Employer: 13% of 15000 = 1950, Employee: 12% of 15000 = 1800, Total = 3750)
                    employer_pf = float(round(pf_ceil * pf_er_rate))
                    employee_pf = float(round(pf_ceil * pf_ee_rate))
                else:
                    employer_pf = float(round(basic * pf_er_rate))
                    employee_pf = float(round(basic * pf_ee_rate))
            else:
                employer_pf = 0.00
                employee_pf = 0.00

            # -------- Professional Tax --------
            pt_config = None
            if location and hasattr(location, "professional_tax_config"):
                try:
                    pt_config = location.professional_tax_config
                except Exception:
                    pt_config = None

            if pt_config and pt_config.is_active:
                pt_thresh_val = float(pt_config.pt_threshold) if float(pt_config.pt_threshold) > 0 else 20000.0
                pt_low_val = float(pt_config.pt_amount_below)
                pt_high_val = float(pt_config.pt_amount_above)
                should_apply_pt = True
            else:
                pt_thresh_val = pt_thresh if pt_thresh > 0 else 20000.0
                pt_low_val = pt_low if pt_low > 0 else 150.0
                pt_high_val = pt_high if pt_high > 0 else 200.0
                should_apply_pt = True

            professional_tax = (
                (pt_low_val if gross_monthly < pt_thresh_val else pt_high_val)
                if should_apply_pt and gross_monthly > 0
                else 0.0
            )

            # -------- Net Salary --------
            net_salary = float(round(gross_monthly - employee_pf - employer_pf - professional_tax))

            return {
                "gross": gross_monthly,
                "basic": basic,
                "hra": hra,
                "conveyance": conveyance,
                "conveyance_allowance": conveyance,
                "lta": lta,
                "special_allowance": special_allowance,
                "other_allowance": other_allowance,
                "employee_pf": employee_pf,
                "employer_pf": employer_pf,
                "professional_tax": professional_tax,
                "net_salary": net_salary,
                "medical": 0.00,
            }

    # Monthly CTC (Full)
    full_monthly_ctc = float(round(annual_ctc / 12))
    full_breakdown = get_breakdown_logic(full_monthly_ctc, pf_enabled, country_code)

    # Prorated Monthly CTC based on actual worked days within the payroll cycle
    if cycle_total_days > 0:
        monthly_ctc = float(round(full_monthly_ctc * (actual_worked_days / cycle_total_days)))
        prorated_breakdown = get_breakdown_logic(monthly_ctc, pf_enabled, country_code)
    else:
        monthly_ctc = 0.0
        prorated_breakdown = dict.fromkeys(full_breakdown, 0.0)

    positive_arrears = arrears if arrears > 0 else 0.0

    return {
        "monthly_ctc": monthly_ctc,
        "full_monthly_ctc": full_monthly_ctc,
        "gross_monthly": prorated_breakdown["gross"] + travel_allowance + positive_arrears,
        "full_monthly_gross": full_breakdown["gross"] + travel_allowance + positive_arrears,
        "basic": prorated_breakdown["basic"],
        "hra": prorated_breakdown["hra"],
        "conveyance": prorated_breakdown.get("conveyance", 0.00),
        "conveyance_allowance": prorated_breakdown.get(
            "conveyance_allowance", prorated_breakdown.get("conveyance", 0.00)
        ),
        "lta": prorated_breakdown.get("lta", 0.00),
        "special_allowance": prorated_breakdown.get(
            "special_allowance", prorated_breakdown.get("other_allowance", 0.00)
        ),
        "other_allowance": prorated_breakdown.get("other_allowance", 0.00),
        "medical": prorated_breakdown.get("medical", 0.00),
        "employee_pf": prorated_breakdown["employee_pf"],
        "employer_pf": prorated_breakdown["employer_pf"],
        "professional_tax": float(prorated_breakdown["professional_tax"]),
        "net_salary": prorated_breakdown["net_salary"] + travel_allowance + arrears - tds_deduction,
        "worked_days": worked_days,
        "actual_worked_days": actual_worked_days,
        "total_days": total_days,
        "cycle_total_days": cycle_total_days,
        "display_days": display_days,
        "pf_enabled": pf_enabled,
        "country_code": country_code,
        "currency_symbol": currency_symbol,
        "travel_allowance": travel_allowance,
        "tds_deduction": tds_deduction,
        "arrears": arrears,
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
