import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import PolicySection

def populate_policy():
    # Clear existing sections
    print("Clearing existing policy sections...")
    PolicySection.objects.all().delete()
    
    sections_data = [
        {
            "title": "Employment & Workplace",
            "order": 1,
            "content": """
                <h4>Purpose</h4>
                <p>To define employment terms and ensure a fair and professional workplace.</p>
                
                <h4>Policy</h4>
                <ul>
                    <li>Employment may be full-time, part-time, intern, or contract-based</li>
                    <li>All employees will undergo a probation period of 3–6 months</li>
                    <li>Equal opportunity is provided to all employees</li>
                    <li>Discrimination or unfair treatment is not allowed</li>
                </ul>

                <h4>Applicability</h4>
                <p>All employees of the organization.</p>
            """
        },
        {
            "title": "Attendance & Leave",
            "order": 2,
            "content": """
                <h4>Purpose</h4>
                <p>To maintain discipline and work continuity.</p>

                <h4>Policy</h4>
                <ul>
                    <li>Working days: Monday to Friday</li>
                    <li>Attendance must be marked through HRMS or approved system</li>
                    <li>Leave must be applied and approved in advance</li>
                    <li>Types of leave include Casual, Sick, Earned, and statutory leaves</li>
                    <li>Unauthorized absence may lead to disciplinary action</li>
                </ul>
            """
        },
        {
            "title": "Compensation & Payroll",
            "order": 3,
            "content": """
                <h4>Purpose</h4>
                <p>To ensure transparent and timely salary processing.</p>

                <h4>Policy</h4>
                <ul>
                    <li>Salaries are paid monthly</li>
                    <li>Payslips are available through HRMS</li>
                    <li>Statutory deductions such as PF, ESI, PT, and TDS will apply</li>
                    <li>Incentives and bonuses, if any, are performance-based</li>
                </ul>
            """
        },
        {
            "title": "Conduct & POSH",
            "order": 4,
            "content": """
                <h4>Purpose</h4>
                <p>To promote respectful and ethical behavior.</p>

                <h4>Policy</h4>
                <ul>
                    <li>Employees must behave professionally at all times</li>
                    <li>Harassment, discrimination, or misconduct is strictly prohibited</li>
                    <li>The company follows the POSH Act for prevention of sexual harassment</li>
                    <li>Complaints can be raised confidentially to the ICC</li>
                </ul>
            """
        },
        {
            "title": "IT & Data Security",
            "order": 5,
            "content": """
                <h4>Purpose</h4>
                <p>To protect company and client information.</p>

                <h4>Policy</h4>
                <ul>
                    <li>Company IT systems are for official use only</li>
                    <li>Sharing passwords, data, or confidential information is prohibited</li>
                    <li>Client and company data must not be disclosed during or after employment</li>
                    <li>Misuse of systems may result in disciplinary or legal action</li>
                </ul>
            """
        },
        {
            "title": "Performance & Discipline",
            "order": 6,
            "content": """
                <h4>Purpose</h4>
                <p>To improve employee performance and maintain discipline.</p>

                <h4>Policy</h4>
                <ul>
                    <li>Performance is reviewed periodically</li>
                    <li>Feedback and improvement plans may be provided</li>
                    <li>Policy violations may lead to warnings, suspension, or termination</li>
                </ul>
            """
        },
        {
            "title": "Grievance & Exit",
            "order": 7,
            "content": """
                <h4>Purpose</h4>
                <p>To handle employee concerns and separation professionally.</p>

                <h4>Policy</h4>
                <ul>
                    <li>Employees can raise grievances without fear of retaliation</li>
                    <li>Notice period applies as per appointment letter</li>
                    <li>Company assets must be returned during exit</li>
                    <li>Full and final settlement will be processed as per policy</li>
                </ul>
            """
        }
    ]

    for section in sections_data:
        PolicySection.objects.create(
            title=section["title"],
            order=section["order"],
            content=section["content"],
            is_active=True
        )
        print(f"Created section: {section['title']}")

    print("Policy populated successfully!")

if __name__ == '__main__':
    populate_policy()
