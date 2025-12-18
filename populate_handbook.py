import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from employees.models import HandbookSection

def populate_handbook():
    # Clear existing sections
    print("Clearing existing handbook sections...")
    HandbookSection.objects.all().delete()
    
    sections_data = [
        {
            "title": "Company Overview",
            "order": 1,
            "content": """
                <h4>1.1 Welcome Message</h4>
                <p>Welcome to the organization. We are glad to have you with us. This handbook explains company policies, expectations, and employee responsibilities.</p>
                
                <h4>1.2 Company Vision & Values</h4>
                <p><strong>Vision:</strong> To deliver quality services with integrity and innovation</p>
                <p><strong>Values:</strong> Respect, accountability, teamwork, and professionalism</p>

                <h4>1.3 Employment Terms</h4>
                <ul>
                    <li>Employment types: Full-time, Part-time, Intern, Contract</li>
                    <li>Probation period: 3–6 months</li>
                    <li>Employment confirmation is performance-based</li>
                </ul>

                <h4>1.4 Equal Opportunity</h4>
                <p>The company provides equal opportunity to all employees and does not allow discrimination of any kind.</p>
            """
        },
        {
            "title": "Workplace Rules",
            "order": 2,
            "content": """
                <h4>2.1 Working Hours & Attendance</h4>
                <ul>
                    <li>Standard working days: Monday to Friday</li>
                    <li>Working hours: As defined by the company</li>
                    <li>Attendance must be marked through HRMS</li>
                </ul>

                <h4>2.2 Code of Conduct</h4>
                <p>Employees must:</p>
                <ul>
                    <li>Behave professionally</li>
                    <li>Respect colleagues and clients</li>
                    <li>Follow company ethics and policies</li>
                </ul>

                <h4>2.3 POSH (Anti-Harassment Policy)</h4>
                <p>Sexual harassment is strictly prohibited. Complaints can be raised confidentially to the Internal Complaints Committee (ICC).</p>
            """
        },
        {
            "title": "Leave & Payroll",
            "order": 3,
            "content": """
                <h4>3.1 Leave Policy</h4>
                <ul>
                    <li>Casual Leave</li>
                    <li>Sick Leave</li>
                    <li>Earned Leave</li>
                    <li>Statutory leaves as per law</li>
                </ul>
                <p>Leave approval through HRMS is mandatory.</p>

                <h4>3.2 Holidays</h4>
                <p>The company follows national and festival holidays as announced yearly.</p>

                <h4>3.3 Salary & Payroll</h4>
                <ul>
                    <li>Salary is paid monthly</li>
                    <li>Payslips available on HRMS</li>
                    <li>Statutory deductions apply (PF, ESI, PT, TDS)</li>
                </ul>
            """
        },
        {
            "title": "Performance & IT",
            "order": 4,
            "content": """
                <h4>4.1 Performance Management</h4>
                <ul>
                    <li>Performance reviews conducted periodically</li>
                    <li>Appraisals based on performance and contribution</li>
                </ul>

                <h4>4.2 IT Usage Policy</h4>
                <ul>
                    <li>Company systems are for official use only</li>
                    <li>Sharing passwords or data is prohibited</li>
                </ul>

                <h4>4.3 Confidentiality</h4>
                <p>All company and client data must be kept confidential during and after employment.</p>
            """
        },
        {
            "title": "Grievance & Exit",
            "order": 5,
            "content": """
                <h4>5.1 Grievance Redressal</h4>
                <p>Employees may raise concerns without fear of retaliation. All grievances will be handled confidentially.</p>

                <h4>5.2 Disciplinary Action</h4>
                <p>Violation of policies may lead to warnings, suspension, or termination.</p>

                <h4>5.3 Exit & Separation</h4>
                <ul>
                    <li>Notice period as per appointment letter</li>
                    <li>Asset return mandatory</li>
                    <li>Full & final settlement processed as per policy</li>
                </ul>

                <h4>5.4 Acknowledgement</h4>
                <p>Employees must accept the handbook digitally on HRMS.</p>
            """
        }
    ]

    for section in sections_data:
        HandbookSection.objects.create(
            title=section["title"],
            order=section["order"],
            content=section["content"],
            is_active=True
        )
        print(f"Created section: {section['title']}")

    print("Handbook populated successfully!")

if __name__ == '__main__':
    populate_handbook()
