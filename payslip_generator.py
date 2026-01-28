"""
Payslip Generator - Final Version
FIXED: Always show layout with separator, empty deductions when none
FIXED: Increased spacing between note and below
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

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
            
        import base64
        
        # Check if it's a URL
        if logo_path.startswith('http://') or logo_path.startswith('https://'):
            try:
                import requests
                response = requests.get(logo_path, timeout=10)
                if response.status_code == 200:
                    return base64.b64encode(response.content).decode('utf-8')
                else:
                    print(f"Failed to fetch logo from URL: {logo_path}")
                    return None
            except Exception as e:
                print(f"Error fetching logo from URL {logo_path}: {e}")
                return None
        
        # Handle local file
        if not os.path.exists(logo_path):
            return None
        
        with open(logo_path, 'rb') as logo_file:
            return base64.b64encode(logo_file.read()).decode('utf-8')
    
    def generate_payslip(self, employee_data: Dict[str, Any], month: str, year: str) -> str:
        """
        Generate payslip PDF using WeasyPrint with exact template format
        """
        
        # Check if WeasyPrint is available
        if not WEASYPRINT_AVAILABLE:
            raise ImportError("WeasyPrint is not available. Please install it with: pip install weasyprint")
        
        # Get logo (if provided in employee_data)
        logo_base64 = None
        logo_path = employee_data.get('logo_path')
        if logo_path:
            logo_base64 = self._encode_logo(logo_path)
        
        # Render HTML from template
        html_content = self._render_html_template(employee_data, month, year, logo_base64)
        
        # Generate PDF filename
        emp_name = employee_data.get('name', 'Employee').replace(' ', '_')
        pdf_filename = f"{emp_name}-Payslip_{month}-{year}.pdf"
        pdf_path = self.output_dir / pdf_filename
        
        # Use WeasyPrint with optimized settings for exact formatting
        try:
            from weasyprint import CSS
            
            # Create CSS for better PDF rendering - optimized for exact format
            pdf_css = CSS(string="""
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
                .header-section,
                .company-section,
                .employee-name-section,
                .employee-details,
                .salary-header,
                .salary-table,
                .net-salary-section,
                .footer-section {
                    page-break-inside: avoid;
                }
            """)
            
            # Generate PDF with WeasyPrint
            HTML(string=html_content).write_pdf(
                str(pdf_path),
                stylesheets=[pdf_css],
                presentational_hints=True,
                optimize_images=True
            )
            
        except Exception as e:
            print(f"Error with WeasyPrint CSS: {e}")
            # Fallback to basic generation
            try:
                HTML(string=html_content).write_pdf(str(pdf_path))
            except Exception as fallback_error:
                print(f"Fallback PDF generation also failed: {fallback_error}")
                raise fallback_error
        
        print(f"✓ Payslip generated with WeasyPrint: {pdf_path}")
        return str(pdf_path)
    
    def _render_html_template(self, employee_data: Dict[str, Any], month: str, year: str, logo_base64: str = None) -> str:
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
            margin-bottom: 20px;
            padding-bottom: 15px;
        }
        
        .header-content {
            flex: 1;
            text-align: left;
        }
        
        .header-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 8px;
        }
        
        .company-name {
            font-family: 'Arial MT', Arial, sans-serif;
            font-size: 14px;
            font-weight: normal;
            margin-bottom: 5px;
            color: #000;
        }
        
        .company-address {
            font-family: 'Arial MT', Arial, sans-serif;
            font-size: 11px;
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
        
        /* EARNINGS AND DEDUCTIONS LAYOUT */
        .salary-flex {
            display: flex;
            gap: 40px;
            margin-bottom: 15px;
        }
        
        .salary-column {
            flex: 1;
        }
        
        .salary-column-title {
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        
        /* TABLE FOR PROPER SPACING */
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
            width: 90px;
            padding-left: 15px;
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
        
        .separator-line {
            width: 1px;
            background-color: #ccc;
            min-height: 120px;
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
        
        /* NOTE SECTION - INCREASED SPACING */
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
        
        .footer {
            font-size: 9px;
            color: #999;
            margin-top: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header with Company Info on Left, Logo on Right -->
        <div class="header">
            <div class="header-content">
                <div class="header-title">
                    <span style="font-weight: bold; color: #000;">PAYSLIP</span> 
                    <span style="font-weight: normal; color: #666; font-size: 18px;">{{ month_short|upper }} {{ year }}</span>
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
        
        <!-- Thin line below name -->
        <div style="border-bottom: 1px solid #333; margin: 0 0 10px 0;"></div>
        
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
        
        <!-- Grey line after payable units -->
        <div style="border-bottom: 1px solid #ccc; margin-bottom: 15px;"></div>
        
        <!-- EARNINGS, CONTRIBUTIONS, AND TAXES & DEDUCTIONS - EXACT LAYOUT AS IMAGE -->
        {% if has_pf_deductions %}
        <!-- TWO COLUMN LAYOUT: EARNINGS (LEFT) | CONTRIBUTIONS + TAXES & DEDUCTIONS (RIGHT STACKED) -->
        <div style="display: flex; gap: 40px; margin-bottom: 15px;">
            <!-- Left Column: EARNINGS -->
            <div style="flex: 1;">
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
            
            <!-- Right Column: CONTRIBUTIONS (TOP) + TAXES & DEDUCTIONS (BOTTOM) STACKED -->
            <div style="flex: 1;">
                <!-- CONTRIBUTIONS Section (Top) -->
                <div style="margin-bottom: 30px;">
                    <div class="salary-column-title">CONTRIBUTIONS</div>
                    <table class="salary-table">
                        {% for deduction in pf_contributions %}
                        <tr>
                            <td class="salary-label">PF Employee</td>
                            <td class="salary-amount">{{ currency_symbol }}{{ "%.2f"|format(deduction.amount) }}</td>
                        </tr>
                        {% endfor %}
                        <tr class="salary-total-row">
                            <td class="salary-label">Total Contributions (B)</td>
                            <td class="salary-amount">{{ currency_symbol }}{{ "%.2f"|format(total_contributions) }}</td>
                        </tr>
                    </table>
                </div>
                
                <!-- TAXES & DEDUCTIONS Section (Bottom) -->
                {% if tax_deductions and tax_deductions|length > 0 %}
                <div>
                    <div class="salary-column-title">TAXES & DEDUCTIONS</div>
                    <table class="salary-table">
                        {% for deduction in tax_deductions %}
                        <tr>
                            <td class="salary-label">{{ deduction.name }}</td>
                            <td class="salary-amount">{{ currency_symbol }}{{ "%.2f"|format(deduction.amount) }}</td>
                        </tr>
                        {% endfor %}
                        <tr class="salary-total-row">
                            <td class="salary-label">Total Taxes & Deductions (C)</td>
                            <td class="salary-amount">{{ currency_symbol }}{{ "%.2f"|format(total_taxes_deductions) }}</td>
                        </tr>
                    </table>
                </div>
                {% endif %}
            </div>
        </div>
        {% else %}
        <!-- TWO COLUMN LAYOUT: EARNINGS | DEDUCTIONS (NO PF) -->
        <div class="salary-flex">
            <!-- Earnings Column -->
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
            
            <!-- Vertical Separator Line -->
            <div class="separator-line"></div>
            
            <!-- Deductions Column - EMPTY IF NO DEDUCTIONS -->
            <div class="salary-column">
                {% if deductions and deductions|length > 0 %}
                <!-- SHOW TAXES & DEDUCTIONS TITLE AND DATA -->
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
                {% else %}
                <!-- NO DEDUCTIONS - COLUMN IS BLANK/EMPTY -->
                {% endif %}
            </div>
        </div>
        {% endif %}
        
        <!-- Net Salary -->
        <div class="net-salary-section">
            <div class="net-salary-row">
                {% if has_pf_deductions %}
                <span class="net-salary-label">Net Salary Payable ( A - B - C )</span>
                {% else %}
                <span class="net-salary-label">Net Salary Payable ( A {% if deductions %}- B {% endif %})</span>
                {% endif %}
                <span class="net-salary-amount">{{ currency_symbol }}{{ "%.2f"|format(net_salary) }}</span>
            </div>
            <div class="net-salary-row">
                <span class="net-salary-label">Net Salary in words</span>
                <span class="net-salary-amount">{{ salary_in_words }}</span>
            </div>
        </div>
        
        <!-- NOTE - EXACT FORMAT WITH INCREASED SPACING -->
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
        
        # Calculate totals and separate PF contributions from other deductions
        total_earnings = sum(e['amount'] for e in employee_data.get('earnings', []))
        
        # Separate PF contributions from other deductions
        pf_contributions = []
        tax_deductions = []
        
        for deduction in employee_data.get('deductions', []):
            if 'PF' in deduction['name'] or 'Provident' in deduction['name']:
                pf_contributions.append(deduction)
            else:
                tax_deductions.append(deduction)
        
        # Calculate totals for each category
        total_contributions = sum(d['amount'] for d in pf_contributions)
        total_taxes_deductions = sum(d['amount'] for d in tax_deductions)
        total_deductions = total_contributions + total_taxes_deductions
        
        # Determine if we have PF deductions (for layout decision)
        has_pf_deductions = len(pf_contributions) > 0
        
        net_salary = total_earnings - total_deductions
        
        # Get currency information from employee location
        employee_location = employee_data.get('location_obj')  # Location object passed from utils
        currency_info = self._get_currency_info(employee_location)
        salary_in_words = self._number_to_words_with_currency(int(net_salary), currency_info)
        
        # Convert month to 3-letter format
        month_short = month[:3] if len(month) > 3 else month
        
        # Prepare template context - ALL from employee_data
        context = {
            'month': month,
            'month_short': month_short,
            'year': year,
            'company_name': employee_data.get('company_name', ''),
            'company_address': employee_data.get('company_address', ''),
            'company_city': employee_data.get('company_city', ''),
            'company_state': employee_data.get('company_state', ''),
            'company_postal_code': employee_data.get('company_postal_code', ''),
            'employee_name': employee_data.get('name', ''),
            'employee_id': employee_data.get('employee_id', ''),
            'date_joined': employee_data.get('date_joined', 'N/A'),
            'department': employee_data.get('department', ''),
            'designation': employee_data.get('designation', ''),
            'payment_mode': employee_data.get('payment_mode', 'Bank Transfer'),
            'bank_name': employee_data.get('bank_name', ''),
            'bank_ifsc': employee_data.get('bank_ifsc', ''),
            'bank_account': employee_data.get('bank_account', ''),
            'uan': employee_data.get('uan', 'N/A'),
            'pan_number': employee_data.get('pan_number', ''),
            'payable_units': employee_data.get('payable_units', '30 Days'),
            'earnings': employee_data.get('earnings', []),
            'deductions': employee_data.get('deductions', []),
            'pf_contributions': pf_contributions,
            'tax_deductions': tax_deductions,
            'has_pf_deductions': has_pf_deductions,
            'total_earnings': total_earnings,
            'total_contributions': total_contributions,
            'total_taxes_deductions': total_taxes_deductions,
            'total_deductions': total_deductions,
            'net_salary': net_salary,
            'salary_in_words': salary_in_words,
            'logo_base64': logo_base64,
            'currency': employee_data.get('currency', 'INR'),
            'currency_code': currency_info['code'],
            'currency_symbol': currency_info['symbol'],
            'currency_name': currency_info['name'],
        }
        
        # Render template
        template = Template(html_template)
        return template.render(context)
    
    @staticmethod
    def _get_currency_info(location):
        """Get currency information based on employee location"""
        if not location:
            return {'code': 'INR', 'symbol': '₹', 'name': 'Indian Rupees'}
        
        # Currency mapping based on location
        currency_map = {
            'INR': {'code': 'INR', 'symbol': '₹', 'name': 'Indian Rupees'},
            'USD': {'code': 'USD', 'symbol': '$', 'name': 'US Dollars'},
            'BDT': {'code': 'BDT', 'symbol': '৳', 'name': 'Bangladeshi Taka'},
            'EUR': {'code': 'EUR', 'symbol': '€', 'name': 'Euros'},
            'GBP': {'code': 'GBP', 'symbol': '£', 'name': 'British Pounds'},
        }
        
        # Get currency from location or default to INR
        location_currency = getattr(location, 'currency', 'INR').upper()
        
        # Location-based currency detection
        if hasattr(location, 'country_code'):
            country_code = location.country_code.upper()
            if country_code == 'US':
                location_currency = 'USD'
            elif country_code == 'BD':  # Bangladesh
                location_currency = 'BDT'
            elif country_code == 'IN':  # India
                location_currency = 'INR'
        
        # Location name-based detection (fallback)
        location_name = location.name.upper() if hasattr(location, 'name') else ''
        if 'DHAKA' in location_name or 'BANGLADESH' in location_name:
            location_currency = 'BDT'
        elif 'US' in location_name or 'AMERICA' in location_name or 'USA' in location_name:
            location_currency = 'USD'
        elif 'INDIA' in location_name or 'INDIAN' in location_name:
            location_currency = 'INR'
        
        return currency_map.get(location_currency, currency_map['INR'])

    @staticmethod
    def _number_to_words_with_currency(num: int, currency_info: dict) -> str:
        """Convert number to words with appropriate currency"""
        ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
        teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 
                'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
        tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
        
        def convert_below_thousand(n):
            if n == 0:
                return ''
            elif n < 10:
                return ones[n]
            elif n < 20:
                return teens[n - 10]
            elif n < 100:
                return tens[n // 10] + (' ' + ones[n % 10] if n % 10 != 0 else '')
            else:
                return ones[n // 100] + ' Hundred' + (' ' + convert_below_thousand(n % 100) if n % 100 != 0 else '')
        
        if num == 0:
            return 'Zero'
        
        currency_code = currency_info['code']
        
        # Different number systems based on currency
        if currency_code == 'INR':
            # Indian numbering system (Crore, Lakh)
            crore = num // 10000000
            num %= 10000000
            lakh = num // 100000
            num %= 100000
            thousand = num // 1000
            num %= 1000
            remainder = num
            
            result = []
            if crore > 0:
                result.append(convert_below_thousand(crore) + ' Crore')
            if lakh > 0:
                result.append(convert_below_thousand(lakh) + ' Lakh')
            if thousand > 0:
                result.append(convert_below_thousand(thousand) + ' Thousand')
            if remainder > 0:
                result.append(convert_below_thousand(remainder))
            
            return ' '.join(result) + ' Rupees only'
            
        elif currency_code == 'BDT':
            # Bangladeshi Taka (similar to Indian system)
            crore = num // 10000000
            num %= 10000000
            lakh = num // 100000
            num %= 100000
            thousand = num // 1000
            num %= 1000
            remainder = num
            
            result = []
            if crore > 0:
                result.append(convert_below_thousand(crore) + ' Crore')
            if lakh > 0:
                result.append(convert_below_thousand(lakh) + ' Lakh')
            if thousand > 0:
                result.append(convert_below_thousand(thousand) + ' Thousand')
            if remainder > 0:
                result.append(convert_below_thousand(remainder))
            
            return ' '.join(result) + ' Taka only'
            
        else:
            # Western numbering system (Million, Billion) for USD, EUR, GBP
            billion = num // 1000000000
            num %= 1000000000
            million = num // 1000000
            num %= 1000000
            thousand = num // 1000
            num %= 1000
            remainder = num
            
            result = []
            if billion > 0:
                result.append(convert_below_thousand(billion) + ' Billion')
            if million > 0:
                result.append(convert_below_thousand(million) + ' Million')
            if thousand > 0:
                result.append(convert_below_thousand(thousand) + ' Thousand')
            if remainder > 0:
                result.append(convert_below_thousand(remainder))
            
            currency_name = currency_info['name']
            return ' '.join(result) + f' {currency_name} only'
