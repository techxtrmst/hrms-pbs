"""
Payslip Generator - Final Version with Enhanced Features
- PF Contributions and Taxes & Deductions separation
- Multi-currency support
- Improved header format
"""

import os
from pathlib import Path
from typing import Any

# Conditional import for weasyprint to handle CI/CD environments
try:
    from weasyprint import HTML

    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    HTML = None

from jinja2 import Template


class PayslipGenerator:
    """Generate fully customizable payslips - all content from employee_data"""

    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

    def _encode_logo(self, logo_path: str) -> str:
        """Encode logo image to base64 - supports both local files and URLs"""
        if not logo_path:
            return None

        try:
            if logo_path.startswith(("http://", "https://")):
                # Handle URL - download and encode with proper headers
                import base64

                import requests

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }

                response = requests.get(logo_path, headers=headers, timeout=10)
                response.raise_for_status()
                return base64.b64encode(response.content).decode("utf-8")
            else:
                # Handle local file
                if not os.path.exists(logo_path):
                    return None
                import base64

                with open(logo_path, "rb") as logo_file:
                    return base64.b64encode(logo_file.read()).decode("utf-8")
        except Exception as e:
            print(f"Warning: Could not load logo from {logo_path}: {e}")
            return None

    def generate_payslip(self, employee_data: dict[str, Any], month: str, year: str) -> str:
        """Generate payslip PDF using WeasyPrint"""

        if not WEASYPRINT_AVAILABLE:
            raise ImportError("WeasyPrint is not available. Please install it with: pip install weasyprint")

        # Get logo
        logo_base64 = None
        logo_source = employee_data.get("logo_url") or employee_data.get("logo_path")
        if logo_source:
            logo_base64 = self._encode_logo(logo_source)

        # Render HTML from template
        html_content = self._render_html_template(employee_data, month, year, logo_base64)

        # Generate PDF filename
        emp_name = employee_data.get("name", "Employee").replace(" ", "_")
        pdf_filename = f"{emp_name}-Payslip_{month}-{year}.pdf"
        pdf_path = self.output_dir / pdf_filename

        # Use WeasyPrint with optimized settings
        try:
            from weasyprint import CSS

            pdf_css = CSS(
                string="""
                @page {
                    size: A4;
                    margin: 15mm;
                }
                body {
                    -webkit-print-color-adjust: exact;
                    color-adjust: exact;
                    print-color-adjust: exact;
                }
                table {
                    page-break-inside: avoid;
                }
            """
            )

            HTML(string=html_content).write_pdf(
                str(pdf_path), stylesheets=[pdf_css], presentational_hints=True, optimize_images=True
            )

        except Exception as e:
            print(f"Error with WeasyPrint CSS: {e}")
            try:
                HTML(string=html_content).write_pdf(str(pdf_path))
            except Exception as fallback_error:
                print(f"Fallback PDF generation also failed: {fallback_error}")
                raise fallback_error

        print(f"✓ Payslip generated with WeasyPrint: {pdf_path}")
        return str(pdf_path)

    def _render_html_template(
        self, employee_data: dict[str, Any], month: str, year: str, logo_base64: str = None
    ) -> str:
        """Render HTML template - EXACT format matching original payslip"""

        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: Arial, sans-serif;
            font-size: 11px;
            line-height: 1.4;
            color: #333;
            padding: 20px;
        }

        .container {
            max-width: 800px;
            margin: 0;
        }

        .header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 15px;
            padding-bottom: 10px;
        }

        .header-content {
            flex: 1;
            text-align: left;
        }

        .header-title {
            font-family: 'Arial MT', Arial, sans-serif;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 8px;
        }

        .company-name {
            font-family: 'Arial MT', Arial, sans-serif;
            font-size: 12px;
            font-weight: normal;
            margin-bottom: 5px;
            color: #000;
        }

        .company-address {
            font-family: 'Arial MT', Arial, sans-serif;
            font-size: 10px;
            line-height: 1.3;
            margin-bottom: 3px;
        }

        .logo-section {
            flex: 0 0 auto;
            margin-left: 20px;
            display: flex;
            align-items: flex-start;
        }

        .logo-section img {
            height: 50px;
            width: auto;
        }

        .employee-name {
            font-size: 14px;
            font-weight: bold;
            margin-top: 5px;
            margin-bottom: 0px;
            text-align: left;
            text-transform: uppercase;
        }

        .divider-line {
            border-bottom: 1px solid #333;
            margin: 0 0 10px 0;
        }

        .info-section {
            margin-bottom: 20px;
        }

        .info-grid {
            display: table;
            width: 100%;
            border-collapse: collapse;
        }

        .info-row {
            display: table-row;
        }

        .info-cell {
            display: table-cell;
            padding: 8px 10px;
            width: 25%;
            font-size: 11px;
            border-bottom: 1px solid #ddd;
        }

        .info-label {
            font-weight: bold;
            color: #666;
        }

        .info-value {
            color: #333;
        }

        .section-title {
            font-size: 12px;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 10px;
            text-transform: uppercase;
            border-bottom: 2px solid #333;
            padding-bottom: 5px;
        }

        .salary-flex {
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
        }

        .salary-column {
            flex: 1;
            min-width: 0;
        }

        .salary-column-title {
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 8px;
            text-transform: uppercase;
        }

        .separator-line {
            width: 1px;
            background-color: #ccc;
            min-height: 200px;
            margin: 0 15px;
            flex-shrink: 0;
        }

        .salary-table {
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }

        .salary-table tr {
            display: table-row;
        }

        .salary-table td {
            padding: 4px 0;
            font-size: 11px;
            border-bottom: none;
        }

        .salary-label {
            text-align: left;
            padding-right: 15px;
            width: auto;
            word-break: break-word;
        }

        .salary-amount {
            text-align: right;
            width: 80px;
            padding-left: 10px;
            font-weight: normal;
        }

        .salary-total-row {
            padding-top: 0;
        }

        .salary-total-row td {
            font-weight: bold;
            padding: 6px 0;
            border-top: none;
        }

        .net-salary-section {
            margin-top: 20px;
            padding: 10px;
            background-color: #f5f5f5;
            border-left: 3px solid #333;
        }

        .net-salary-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 11px;
        }

        .net-salary-label {
            font-weight: bold;
        }

        .net-salary-amount {
            font-weight: bold;
            margin-left: 20px;
        }

        .note-section {
            font-size: 9.5px;
            font-family: Arial, sans-serif;
            font-style: italic;
            margin-top: 30px;
            margin-bottom: 40px;
            color: #333;
            line-height: 1.5;
        }

        .note-line {
            margin-bottom: 8px;
        }

        .note-line:first-child {
            font-size: 9.5px;
        }

        .note-line:last-child {
            font-size: 7.5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="header-content">
                <div class="header-title">
                    <span style="font-family: 'Arial MT', Arial, sans-serif; font-weight: bold; color: #000; font-size: 18px;">PAYSLIP</span>
                    <span style="font-family: 'Arial MT', Arial, sans-serif; font-weight: normal; color: #666; font-size: 18px;">{{ month_short|upper }} {{ year }}</span>
                </div>
                <div class="company-name">{{ company_name }}</div>
                <div class="company-address">
                    {{ company_address }}<br>
                    {{ company_city }}<br>
                    {{ company_state }}
                </div>
            </div>
            {% if logo_base64 %}
            <div class="logo-section">
                <img src="data:image/png;base64,{{ logo_base64 }}" alt="Company Logo">
            </div>
            {% endif %}
        </div>

        <!-- Employee Name -->
        <div class="employee-name">{{ employee_name|upper }}</div>
        <div class="divider-line"></div>

        <!-- Employee Details -->
        <div class="info-section">
            <div class="info-grid">
                <div class="info-row">
                    <div class="info-cell">
                        <span class="info-label">Employee Number</span><br>
                        <span class="info-value">{{ employee_id }}</span>
                    </div>
                    <div class="info-cell">
                        <span class="info-label">Date Joined</span><br>
                        <span class="info-value">{{ date_joined }}</span>
                    </div>
                    <div class="info-cell">
                        <span class="info-label">Department</span><br>
                        <span class="info-value">{{ department }}</span>
                    </div>
                    <div class="info-cell">
                        <span class="info-label">Designation</span><br>
                        <span class="info-value">{{ designation }}</span>
                    </div>
                </div>
                <div class="info-row">
                    <div class="info-cell">
                        <span class="info-label">Payment Mode</span><br>
                        <span class="info-value">{{ payment_mode }}</span>
                    </div>
                    <div class="info-cell">
                        <span class="info-label">Bank</span><br>
                        <span class="info-value">{{ bank_name }}</span>
                    </div>
                    <div class="info-cell">
                        <span class="info-label">Bank IFSC</span><br>
                        <span class="info-value">{{ bank_ifsc }}</span>
                    </div>
                    <div class="info-cell">
                        <span class="info-label">Bank Account</span><br>
                        <span class="info-value">{{ bank_account }}</span>
                    </div>
                </div>
                <div class="info-row">
                    <div class="info-cell">
                        <span class="info-label">UAN</span><br>
                        <span class="info-value">{{ uan }}</span>
                    </div>
                    <div class="info-cell">
                        <span class="info-label">PAN Number</span><br>
                        <span class="info-value">{{ pan_number }}</span>
                    </div>
                    <div class="info-cell"></div>
                    <div class="info-cell"></div>
                </div>
            </div>
        </div>

        <!-- Salary Details Section -->
        <div class="section-title">SALARY DETAILS</div>

        <!-- Payable Units -->
        <div style="margin-bottom: 15px; font-size: 11px;">
            <span style="font-weight: bold;">PAYABLE UNITS</span><br>
            <span>{{ payable_units }}</span>
        </div>

        <!-- Grey line -->
        <div style="border-bottom: 1px solid #ccc; margin-bottom: 15px;"></div>

        <!-- EARNINGS, CONTRIBUTIONS AND DEDUCTIONS - VERTICAL LAYOUT -->

        <!-- EARNINGS AND DEDUCTIONS - SIDE BY SIDE LAYOUT -->
        <div class="salary-flex">
            <!-- Left Column: EARNINGS -->
            <div class="salary-column">
                <div class="salary-column-title">EARNINGS</div>
                <table class="salary-table">
                    {% for earning in earnings %}
                    <tr>
                        <td class="salary-label">{{ earning.name }}</td>
                        <td class="salary-amount">{{ currency_symbol }}{{ "%.2f"|format(earning.amount) }}</td>
                    </tr>
                    {% endfor %}
                    <tr class="salary-total-row">
                        <td class="salary-label">Total Earnings (A)</td>
                        <td class="salary-amount">{{ currency_symbol }}{{ "%.2f"|format(total_earnings) }}</td>
                    </tr>
                </table>
            </div>

            <!-- Separator Line -->
            <div class="separator-line"></div>

            <!-- Right Column: CONTRIBUTIONS & DEDUCTIONS -->
            <div class="salary-column">
                {% if (contributions and contributions|length > 0) or (deductions and deductions|length > 0) %}

                {% if contributions and contributions|length > 0 %}
                <!-- Show CONTRIBUTIONS section when PF exists -->
                <div class="salary-column-title">CONTRIBUTIONS</div>
                <table class="salary-table">
                    {% for contribution in contributions %}
                    <tr>
                        <td class="salary-label">{{ contribution.name }}</td>
                        <td class="salary-amount">{{ currency_symbol }}{{ "%.2f"|format(contribution.amount) }}</td>
                    </tr>
                    {% endfor %}
                    <tr class="salary-total-row">
                        <td class="salary-label">Total Contributions (B)</td>
                        <td class="salary-amount">{{ currency_symbol }}{{ "%.2f"|format(total_contributions) }}</td>
                    </tr>
                </table>

                    {% if deductions and deductions|length > 0 %}
                    <!-- When PF exists, deductions are labeled as C -->
                    <div class="salary-column-title" style="margin-top: 15px;">TAXES & DEDUCTIONS</div>
                    <table class="salary-table">
                        {% for deduction in deductions %}
                        <tr>
                            <td class="salary-label">{{ deduction.name }}</td>
                            <td class="salary-amount">{{ currency_symbol }}{{ "%.2f"|format(deduction.amount) }}</td>
                        </tr>
                        {% endfor %}
                        <tr class="salary-total-row">
                            <td class="salary-label">Total Taxes & Deductions (C)</td>
                            <td class="salary-amount">{{ currency_symbol }}{{ "%.2f"|format(total_deductions) }}</td>
                        </tr>
                    </table>
                    {% endif %}

                {% else %}
                    {% if deductions and deductions|length > 0 %}
                    <!-- When NO PF exists, deductions are labeled as B -->
                    <div class="salary-column-title">TAXES & DEDUCTIONS</div>
                    <table class="salary-table">
                        {% for deduction in deductions %}
                        <tr>
                            <td class="salary-label">{{ deduction.name }}</td>
                            <td class="salary-amount">{{ currency_symbol }}{{ "%.2f"|format(deduction.amount) }}</td>
                        </tr>
                        {% endfor %}
                        <tr class="salary-total-row">
                            <td class="salary-label">Total Taxes & Deductions (B)</td>
                            <td class="salary-amount">{{ currency_symbol }}{{ "%.2f"|format(total_deductions) }}</td>
                        </tr>
                    </table>
                    {% endif %}
                {% endif %}

                {% endif %}
            </div>
        </div>

        <!-- Net Salary -->
        <div class="net-salary-section">
            <div class="net-salary-row">
                {% if contributions and contributions|length > 0 %}
                    <!-- When PF exists: A - B - C -->
                    <span class="net-salary-label">Net Salary Payable ( A {% if contributions %}- B {% endif %}{% if deductions %}- C {% endif %})</span>
                {% else %}
                    <!-- When NO PF exists: A - B (deductions become B) -->
                    <span class="net-salary-label">Net Salary Payable ( A {% if deductions %}- B {% endif %})</span>
                {% endif %}
                <span class="net-salary-amount">{{ currency_symbol }}{{ "%.2f"|format(net_salary) }}</span>
            </div>
            <div class="net-salary-row">
                <span class="net-salary-label">Net Salary in words</span>
                <span class="net-salary-amount">{{ salary_in_words }}</span>
            </div>
        </div>

        <!-- NOTE -->
        <div class="note-section">
            <div class="note-line">
                <span style="font-style: italic;"><strong>**Note :</strong> All amounts displayed in this payslip are in <strong>{{ currency }}</strong></span>
            </div>
            <div class="note-line">
                <span style="font-style: italic;">* This is computer generated statement, does not require signature.</span>
            </div>
        </div>
    </div>
</body>
</html>
        """

        # Calculate totals
        total_earnings = sum(e["amount"] for e in employee_data.get("earnings", []))
        total_contributions = (
            sum(c["amount"] for c in employee_data.get("contributions", []))
            if employee_data.get("contributions")
            else 0
        )
        total_deductions = (
            sum(d["amount"] for d in employee_data.get("deductions", [])) if employee_data.get("deductions") else 0
        )
        net_salary = total_earnings - total_contributions - total_deductions

        # Currency
        currency = employee_data.get("currency", "INR")
        currency_symbols = {"INR": "₹", "USD": "$", "BDT": "৳", "EUR": "€", "GBP": "£"}
        currency_symbol = currency_symbols.get(currency, "₹")

        # Number to words
        salary_in_words = self._number_to_words(int(net_salary), currency)

        # Month short format
        month_short = month[:3] if len(month) > 3 else month

        # Context
        context = {
            "month": month,
            "month_short": month_short,
            "year": year,
            "company_name": employee_data.get("company_name", ""),
            "company_address": employee_data.get("company_address", ""),
            "company_city": employee_data.get("company_city", ""),
            "company_state": employee_data.get("company_state", ""),
            "company_postal_code": employee_data.get("company_postal_code", ""),
            "employee_name": employee_data.get("name", ""),
            "employee_id": employee_data.get("employee_id", ""),
            "date_joined": employee_data.get("date_joined", "N/A"),
            "department": employee_data.get("department", ""),
            "designation": employee_data.get("designation", ""),
            "payment_mode": employee_data.get("payment_mode", "Bank Transfer"),
            "bank_name": employee_data.get("bank_name", ""),
            "bank_ifsc": employee_data.get("bank_ifsc", ""),
            "bank_account": employee_data.get("bank_account", ""),
            "uan": employee_data.get("uan", "N/A"),
            "pan_number": employee_data.get("pan_number", ""),
            "payable_units": employee_data.get("payable_units", "30 Days"),
            "earnings": employee_data.get("earnings", []),
            "contributions": employee_data.get("contributions", []),
            "deductions": employee_data.get("deductions", []),
            "total_earnings": total_earnings,
            "total_contributions": total_contributions,
            "total_deductions": total_deductions,
            "net_salary": net_salary,
            "salary_in_words": salary_in_words,
            "logo_base64": logo_base64,
            "currency": currency,
            "currency_symbol": currency_symbol,
        }

        # Render
        template = Template(html_template)
        return template.render(context)

    @staticmethod
    def _number_to_words(num: int, currency: str = "INR") -> str:
        """Convert number to words"""
        ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
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

        def convert_below_thousand(n):
            if n == 0:
                return ""
            elif n < 10:
                return ones[n]
            elif n < 20:
                return teens[n - 10]
            elif n < 100:
                return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
            else:
                return ones[n // 100] + " Hundred" + (" " + convert_below_thousand(n % 100) if n % 100 != 0 else "")

        if num == 0:
            return "Zero"

        if currency == "INR":
            crore = num // 10000000
            num %= 10000000
            lakh = num // 100000
            num %= 100000
            thousand = num // 1000
            num %= 1000
            remainder = num

            result = []
            if crore > 0:
                result.append(convert_below_thousand(crore) + " Crore")
            if lakh > 0:
                result.append(convert_below_thousand(lakh) + " Lakh")
            if thousand > 0:
                result.append(convert_below_thousand(thousand) + " Thousand")
            if remainder > 0:
                result.append(convert_below_thousand(remainder))

            return " ".join(result) + " Rupees only"
        else:
            return str(num) + " " + currency + " only"
