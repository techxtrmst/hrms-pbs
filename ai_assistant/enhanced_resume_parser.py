"""
Enhanced Resume Parser with comprehensive data extraction
Extracts: Basic Info, Education, Experience, Projects, Certifications, Skills
"""

import re
import hashlib
from datetime import datetime
from dateutil import parser as date_parser


class EnhancedResumeParser:
    """
    Comprehensive resume parser for ATS/HRMS
    """

    # Comprehensive skill database
    TECHNICAL_SKILLS = [
        # Programming Languages
        "Python",
        "Java",
        "JavaScript",
        "TypeScript",
        "C++",
        "C#",
        "PHP",
        "Ruby",
        "Go",
        "Rust",
        "Swift",
        "Kotlin",
        "Scala",
        "R",
        "MATLAB",
        "Perl",
        "Shell",
        "Bash",
        "PowerShell",
        # Web Technologies
        "React",
        "Angular",
        "Vue.js",
        "Next.js",
        "Nuxt.js",
        "Svelte",
        "jQuery",
        "Bootstrap",
        "Tailwind CSS",
        "Material UI",
        "HTML",
        "HTML5",
        "CSS",
        "CSS3",
        "SASS",
        "LESS",
        "Webpack",
        "Vite",
        "Babel",
        # Backend Frameworks
        "Django",
        "Flask",
        "FastAPI",
        "Node.js",
        "Express.js",
        "Spring Boot",
        "ASP.NET",
        "Laravel",
        "Ruby on Rails",
        "Gin",
        "Echo",
        # Databases
        "MySQL",
        "PostgreSQL",
        "MongoDB",
        "Redis",
        "Cassandra",
        "Oracle",
        "SQL Server",
        "SQLite",
        "DynamoDB",
        "Elasticsearch",
        "Neo4j",
        "MariaDB",
        # Cloud & DevOps
        "AWS",
        "Azure",
        "Google Cloud",
        "GCP",
        "Docker",
        "Kubernetes",
        "Jenkins",
        "GitLab CI",
        "GitHub Actions",
        "Terraform",
        "Ansible",
        "Chef",
        "Puppet",
        "CircleCI",
        "Travis CI",
        # Data Science & ML
        "Machine Learning",
        "Deep Learning",
        "TensorFlow",
        "PyTorch",
        "Keras",
        "Scikit-learn",
        "Pandas",
        "NumPy",
        "Matplotlib",
        "Seaborn",
        "NLP",
        "Computer Vision",
        "OpenCV",
        # Tools & Others
        "Git",
        "GitHub",
        "GitLab",
        "Bitbucket",
        "JIRA",
        "Confluence",
        "Slack",
        "Trello",
        "Postman",
        "Swagger",
        "REST API",
        "GraphQL",
        "Microservices",
        "Agile",
        "Scrum",
        "Linux",
        "Unix",
        "Windows Server",
        "Nginx",
        "Apache",
    ]

    TOOLS = [
        "Power BI",
        "Tableau",
        "Excel",
        "Google Analytics",
        "Figma",
        "Adobe XD",
        "Sketch",
        "Photoshop",
        "Illustrator",
        "InDesign",
        "VS Code",
        "IntelliJ",
        "PyCharm",
        "Eclipse",
        "Visual Studio",
        "Sublime Text",
        "Atom",
    ]

    SOFT_SKILLS = [
        "Leadership",
        "Communication",
        "Team Management",
        "Problem Solving",
        "Critical Thinking",
        "Time Management",
        "Collaboration",
        "Adaptability",
        "Creativity",
        "Analytical",
        "Presentation",
        "Negotiation",
        "Decision Making",
        "Conflict Resolution",
    ]

    @staticmethod
    def parse_resume(file_path):
        """
        Main parsing function - extracts all information from resume
        """
        try:
            # Extract text from PDF/DOCX
            text = EnhancedResumeParser._extract_text(file_path)

            if not text:
                return {"error": "Could not extract text from file"}

            # Extract all information
            parsed_data = {
                # Basic Details
                "name": EnhancedResumeParser._extract_name(text),
                "email": EnhancedResumeParser._extract_email(text),
                "phone": EnhancedResumeParser._extract_phone(text),
                "location": EnhancedResumeParser._extract_location(text),
                "linkedin": EnhancedResumeParser._extract_linkedin(text),
                "github": EnhancedResumeParser._extract_github(text),
                "portfolio": EnhancedResumeParser._extract_portfolio(text),
                # Skills (categorized)
                "skills": EnhancedResumeParser._extract_skills_legacy(
                    text
                ),  # Comma-separated for backward compatibility
                "skills_json": EnhancedResumeParser._extract_skills_categorized(text),
                # Education
                "education": EnhancedResumeParser._extract_education(text),
                # Experience
                "experience": EnhancedResumeParser._extract_experience(text),
                "total_experience_years": EnhancedResumeParser._calculate_total_experience(
                    text
                ),
                # Projects
                "projects": EnhancedResumeParser._extract_projects(text),
                # Certifications
                "certifications": EnhancedResumeParser._extract_certifications(text),
                # Categorization
                "candidate_type": EnhancedResumeParser._categorize_candidate_type(text),
                "role_fit": EnhancedResumeParser._determine_role_fit(text),
                "domain": EnhancedResumeParser._determine_domain(text),
                # Duplicate Detection
                "duplicate_check_hash": EnhancedResumeParser._generate_hash(text),
            }

            return parsed_data

        except Exception as e:
            return {
                "error": str(e),
                "name": None,
                "email": None,
                "phone": None,
                "skills": None,
            }

    @staticmethod
    def _extract_text(file_path):
        """Extract text from PDF or DOCX"""
        try:
            if file_path.lower().endswith(".pdf"):
                return EnhancedResumeParser._extract_text_from_pdf(file_path)
            elif file_path.lower().endswith((".docx", ".doc")):
                return EnhancedResumeParser._extract_text_from_docx(file_path)
            else:
                return ""
        except:
            return ""

    @staticmethod
    def _extract_text_from_pdf(file_path):
        """Extract text from PDF with improved layout preservation and fallback"""
        text = ""
        try:
            import PyPDF2

            with open(file_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        # Fix common PDF extraction issues: merged words
                        # Add space before capital letters if they follow lowercase immediately (e.g. nameEmail -> name Email)
                        page_text = re.sub(r"([a-z])([A-Z])", r"\1 \2", page_text)

                        # Add space after email if stuck to next word (e.g. .comName -> .com Name)
                        page_text = re.sub(
                            r"(\.com|\.in|\.org|\.net)([A-Za-z])", r"\1 \2", page_text
                        )

                        text += page_text + "\n"

            # Global cleanup
            text = text.replace("\x00", "")

            # If text is very short/empty, PyPDF2 fail.
            if len(text) < 50:
                return ""

            return text
        except:
            return ""

    # ==================== BASIC DETAILS ====================

    @staticmethod
    def _extract_name(text):
        """Extract candidate name - The Ultimate Fallback Strategy"""
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # Banned words - Expanded to kill "Uber Data Analytics"
        banned = [
            "resume",
            "cv",
            "curriculum",
            "vitae",
            "bio",
            "profile",
            "summary",
            "about",
            "contact",
            "work",
            "experience",
            "education",
            "skills",
            "projects",
            "certifications",
            "languages",
            "hobbies",
            "declaration",
            "developer",
            "engineer",
            "analyst",
            "manager",
            "consultant",
            "intern",
            "student",
            "hyderabad",
            "bangalore",
            "mumbai",
            "delhi",
            "pune",
            "chennai",
            "india",
            "usa",
            "uk",
            "dubai",
            "portfolio",
            "website",
            "personal",
            "link",
            "github",
            "linkedin",
            "gmail",
            "email",
            "phone",
            "address",
            "uber",
            "data",
            "analytics",
            "analysis",
        ]  # Explicitly ban "Uber Data Analytics" components

        # Strategy: Scan only the first 20 lines. The name IS there.
        # Don't look at the bottom of the resume where projects are.

        for line in lines[:20]:
            clean_line = re.sub(r"[^a-zA-Z\s\.]", "", line).strip()
            if not clean_line:
                continue

            line_lower = clean_line.lower()

            # Skip banned
            if any(b in line_lower for b in banned):
                continue

            words = clean_line.split()

            # Name typical format: 2 or 3 words (First Last)
            if 2 <= len(words) <= 3:
                # Must be Title Case or UPPER
                if clean_line.istitle() or clean_line.isupper():
                    # Must be alphabet only
                    if clean_line.replace(" ", "").replace(".", "").isalpha():
                        return clean_line  # Return the FIRST valid match at the top.

        return "Unknown Candidate"

    @staticmethod
    def _extract_location(text):
        """Extract location with STRICT Known-City Requirement"""

        # Known cities/countries - The match MUST contain one of these.
        known_places = [
            "india",
            "usa",
            "uk",
            "canada",
            "australia",
            "germany",
            "france",
            "singapore",
            "dubai",
            "uae",
            "hyderabad",
            "bangalore",
            "bengaluru",
            "mumbai",
            "delhi",
            "new delhi",
            "pune",
            "chennai",
            "kolkata",
            "gurgaon",
            "noida",
            "bhubaneswar",
            "odisha",
            "cuttack",
            "berhampur",
            "karnataka",
            "maharashtra",
            "telangana",
            "tamil nadu",
            "andhra pradesh",
        ]

        # Ban List
        ban_list = ["git", "hub", "github", "python", "java", "react", "node"]

        matches = re.findall(
            r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)*,\s*[A-Z][a-z]+(?: [A-Z][a-z]+)*)\b", text
        )

        for match in matches:
            match_lower = match.lower()

            # 1. Check Bans
            if any(b in match_lower for b in ban_list):
                continue

            # 2. STRICT REQUIRED: Must contain a known place
            # "Git, Git Hub" -> Fails (No 'India' or 'Hyderabad')
            # "Hyderabad, India" -> Passes
            has_known = False
            for place in known_places:
                if place in match_lower:
                    has_known = True
                    break

            if has_known:
                if len(match) < 60:
                    return match

        # Fallback for single line cities "Hyderabad"
        for line in text.split("\n"):
            line_clean = line.strip()
            line_lower = line_clean.lower()
            if line_lower in known_places:
                return line_clean + ", India"

        return None

    @staticmethod
    def _extract_email(text):
        """Extract email address with flexible regex for merged text"""
        # Regex that can handle merged text by looking for the @ symbol buffer
        # e.g. "NameEmail@domain.comPhone" -> extracts "Email@domain.com"

        # 1. Standard search
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,5}\b"
        match = re.search(email_pattern, text)
        if match:
            return match.group(0)

        # 2. Aggressive search (if strict boundaries \b failed due to merging)
        # Look for X@Y.Z inside a string
        aggressive_pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,5}"
        match = re.search(aggressive_pattern, text)
        if match:
            return match.group(0)

        return None

    @staticmethod
    def _extract_phone(text):
        """Extract phone number"""
        phone_patterns = [
            r"\+91[-\s]?\d{10}",
            r"\+91[-\s]?\d{5}[-\s]?\d{5}",
            r"\d{10}",
            r"\(\d{3}\)[-\s]?\d{3}[-\s]?\d{4}",
            r"\+\d{1,3}[-\s]?\d{10}",
        ]

        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None

    @staticmethod
    def _extract_location(text):
        """Extract location/address avoiding technical keywords"""

        # Keywords to BAN from location (Tech stack often looks like "Location: Python")
        ban_list = [
            "python",
            "java",
            "script",
            "react",
            "node",
            "aws",
            "cloud",
            "sql",
            "data",
            "pandas",
            "analysis",
            "html",
            "css",
            "developed",
            "managed",
            "using",
            "tools",
        ]

        lines = text.split("\n")

        # 1. Look for explicit "Location: City"
        for line in lines[:20]:
            match = re.search(
                r"(?:Location|Address|City)\s*[:|-]\s*([A-Za-z\s,]+)",
                line,
                re.IGNORECASE,
            )
            if match:
                loc = match.group(1).strip()
                # Validate it's not a banned word
                if not any(b in loc.lower() for b in ban_list) and len(loc) < 40:
                    return loc

        # 2. Pattern Search (City, State)
        loc_pattern = (
            r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)*,\s*[A-Z][a-z]+(?: [A-Z][a-z]+)*)\b"
        )
        matches = re.findall(loc_pattern, text)

        for match in matches:
            # Check bans
            if any(b in match.lower() for b in ban_list):
                continue
            if "University" in match or "College" in match:
                continue

            # Simple length heuristic
            if 5 < len(match) < 40:
                return match

        return None

    @staticmethod
    def _extract_linkedin(text):
        """Extract LinkedIn URL"""
        linkedin_pattern = r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+"
        match = re.search(linkedin_pattern, text, re.IGNORECASE)
        return match.group(0) if match else None

    @staticmethod
    def _extract_github(text):
        """Extract GitHub URL"""
        github_pattern = r"(?:https?://)?(?:www\.)?github\.com/[\w-]+"
        match = re.search(github_pattern, text, re.IGNORECASE)
        return match.group(0) if match else None

    @staticmethod
    def _extract_portfolio(text):
        """Extract portfolio/personal website URL"""
        # Exclude LinkedIn, GitHub, email domains
        url_pattern = r"(?:https?://)?(?:www\.)?[\w-]+\.[\w]{2,}(?:/[\w-]*)*"
        matches = re.findall(url_pattern, text)

        # Common technical terms that look like URLs but aren't
        false_positives = [
            "node.js",
            "react.js",
            "vue.js",
            "next.js",
            "nuxt.js",
            "express.js",
            "three.js",
            "d3.js",
            "chart.js",
            "moment.js",
            "angular.js",
            "backbone.js",
            "jquery.js",
            "ember.js",
            "polymer.js",
            "meteor.js",
            "gatsby.js",
            "intro.js",
            "reveal.js",
            "socket.io",
            "asp.net",
            "vb.net",
        ]

        for url in matches:
            url_lower = url.lower()

            # Skip if it's a known email provider or social platform
            if any(
                x in url_lower
                for x in [
                    "linkedin",
                    "github",
                    "gmail",
                    "yahoo",
                    "outlook",
                    "hotmail",
                    "@",
                ]
            ):
                continue

            # Skip common technical terms (false positives)
            if url_lower in false_positives:
                continue

            # Skip if it is purely numeric or looks like a version number/IP/GPA (e.g., 7.94, 1.0.0, 192.168.1.1)
            # Must contain at least one actual letter to be a domain
            if not any(c.isalpha() for c in url_lower):
                continue

            # Skip short numeric-like strings (e.g. "7.94.2") that matched regex but aren't URLs
            if re.match(r"^[\d\.]+$", url_lower):
                continue

            # Strict TLD Check: Must end with a valid-looking TLD
            # e.g., anything that ends in .00 or .94 is NOT a website
            if not re.search(r"\.[a-z]{2,}(/|$)", url_lower):
                continue

            # Skip if it's just a file extension mention without protocol/www
            if url_lower.endswith(".js") and not url_lower.startswith(("http", "www")):
                continue

            return url

        return None

    # ==================== SKILLS ====================

    @staticmethod
    def _extract_skills_legacy(text):
        """Extract skills as comma-separated string (backward compatibility)"""
        skills_json = EnhancedResumeParser._extract_skills_categorized(text)
        all_skills = []

        if skills_json:
            all_skills.extend(skills_json.get("technical", []))
            all_skills.extend(skills_json.get("tools", []))
            all_skills.extend(skills_json.get("soft", []))

        return ", ".join(all_skills) if all_skills else None

    @staticmethod
    def _extract_skills_categorized(text):
        """Extract and categorize skills"""
        text_lower = text.lower()

        found_technical = []
        found_tools = []
        found_soft = []

        for skill in EnhancedResumeParser.TECHNICAL_SKILLS:
            if skill.lower() in text_lower:
                found_technical.append(skill)

        for tool in EnhancedResumeParser.TOOLS:
            if tool.lower() in text_lower:
                found_tools.append(tool)

        for soft_skill in EnhancedResumeParser.SOFT_SKILLS:
            if soft_skill.lower() in text_lower:
                found_soft.append(soft_skill)

        return {"technical": found_technical, "tools": found_tools, "soft": found_soft}

    # ==================== EDUCATION ====================

    @staticmethod
    def _extract_education(text):
        """Extract education details with strict filtering"""
        education_list = []

        # 1. Compile regex patterns separately for control over case-sensitivity

        # Case-insensitive patterns (Safe 3+ letters or containing dots)
        safe_patterns = [
            r"\bB\.?Tech\b",
            r"\bBachelor of Technology\b",
            r"\bB\.?E\.\b",
            r"\bBachelor of Engineering\b",  # B.E. with dot is safe
            r"\bM\.?Tech\b",
            r"\bMaster of Technology\b",
            r"\bM\.?E\.\b",
            r"\bMaster of Engineering\b",  # M.E. with dot is safe
            r"\bMBA\b",
            r"\bMaster of Business Administration\b",
            r"\bMCA\b",
            r"\bMaster of Computer Applications\b",
            r"\bMaster in Computer Applications\b",
            r"\bBCA\b",
            r"\bBachelor of Computer Applications\b",
            r"\bB\.?Sc\b",
            r"\bBachelor of Science\b",
            r"\bM\.?Sc\b",
            r"\bMaster of Science\b",
            r"\bB\.?Com\b",
            r"\bBachelor of Commerce\b",
            r"\bM\.?Com\b",
            r"\bMaster of Commerce\b",
            r"\bPh\.?D\b",
            r"\bDoctorate\b",
            r"\bDiploma\b",
            r"\bMatriculation\b",
            r"\bSSC\b",
            r"\bHSC\b",
            r"\b10th\b",
            r"\b12th\b",
            r"\bIntermediate\b",
        ]

        # Strict patterns (Case-SENSITIVE 2-letter degrees to avoid 'be', 'me', 'ma')
        # We will match these manually in the loop
        strict_acronyms = {"BE", "ME", "BA", "MA", "BS", "MS"}

        lines = text.split("\n")

        for i, line in enumerate(lines):
            line_str = line.strip()
            if not line_str or len(line_str) < 4:
                continue

            degree_found = None

            # Check safe patterns (Ignore Case)
            for pat in safe_patterns:
                match = re.search(pat, line_str, re.IGNORECASE)
                if match:
                    degree_found = match.group(0)
                    # Normalize common variations
                    lower_deg = degree_found.lower()
                    if "b.tech" in lower_deg:
                        degree_found = "B.Tech"
                    elif "m.tech" in lower_deg:
                        degree_found = "M.Tech"
                    elif "mca" in lower_deg:
                        degree_found = "MCA"
                    elif "mba" in lower_deg:
                        degree_found = "MBA"
                    break

            # Check strict acronyms (Case Sensitive) if no safe pattern found
            if not degree_found:
                # Tokenize line to find exact words
                words = re.split(r"[^a-zA-Z]", line_str)
                for word in words:
                    if word in strict_acronyms:
                        # Extra check: Must be UpperCase AND (followed by space/pipe or end of line)
                        # And usually followed by "in" or "Computer" or something relevant
                        # Or just strictly uppercase 2-letter acronym
                        degree_found = word
                        break

            if degree_found:
                # ------------------- EXTRACT DETAILS -------------------
                degree = degree_found
                university = None
                year = None
                gpa = None
                specialization = None

                # Context: Current line + next 2 lines (reduced window to avoid merging sections)
                context_lines = [line_str]
                if i + 1 < len(lines):
                    context_lines.append(lines[i + 1].strip())
                if i + 2 < len(lines):
                    context_lines.append(lines[i + 2].strip())

                full_context = " | ".join(
                    [l for l in context_lines if l]
                )  # Use separator

                # A. Extract Year (4 digits, 1990-2030)
                years = re.findall(r"\b(199\d|20[0-2]\d|2030)\b", full_context)
                if years:
                    year = int(max(years))  # Grad year is usually the latest

                # B. Extract GPA/Score
                gpa_pattern = r"\b(\d{1,2}\.?\d{0,2})\s*(?:CGPA|GPA|%|/10|/100)\b"
                gpa_match = re.search(gpa_pattern, full_context, re.IGNORECASE)
                if gpa_match:
                    try:
                        gpa = float(gpa_match.group(1))
                    except:
                        pass
                else:
                    # Fallback: finding float at end of line (e.g. "... | 7.94")
                    fallback = re.search(
                        r"(?:\||\-)\s*(\d{1,2}\.\d{2})\b", full_context
                    )
                    if fallback:
                        try:
                            gpa = float(fallback.group(1))
                        except:
                            pass

                # C. Extract University / College
                # Strategy: Look for specific keywords or assume non-degree parts are Uni
                uni_keywords = [
                    "University",
                    "College",
                    "Institute",
                    "School",
                    "Academy",
                    "Campus",
                    "Vidyalaya",
                ]

                # 1. Check for keyword match in context
                for ctx_line in context_lines:
                    if any(kw in ctx_line for kw in uni_keywords):
                        # Avoid extracting the degree line if it contains the uni " Institute of Tech... "
                        # If the line starts with Degree, the rest might be uni
                        clean_line = ctx_line
                        if degree in clean_line:
                            clean_line = clean_line.replace(degree, "").strip(" ,|-")

                        # If meaningful text remains
                        if len(clean_line) > 10 and not re.search(r"^\d", clean_line):
                            university = clean_line
                            break

                # 2. Pipe strategy (e.g. Degree | Uni | Year)
                if not university and "|" in line_str:
                    parts = line_str.split("|")
                    for part in parts:
                        p = part.strip()
                        if degree not in p and not re.search(r"\d", p) and len(p) > 5:
                            # Avoid "Computer Science" as uni
                            if "Science" not in p and "Engineering" not in p:
                                university = p
                                break

                # D. Extract Specialization
                specs = [
                    "Computer Science",
                    "Information Technology",
                    "Civil",
                    "Mechanical",
                    "Electrical",
                    "Electronics",
                    "HR",
                    "Finance",
                    "Marketing",
                    "AI",
                    "Data Science",
                ]
                for sp in specs:
                    if sp.lower() in full_context.lower():
                        specialization = sp
                        break

                # ------------------- VALIDATION -------------------
                # Filter out obvious false positives
                # If university ("Not Detected") and Year (None) and GPA (None) -> Likely false positive degree matching (e.g. "me" in text)
                if not year and not university and not gpa:
                    # Be very strict: remove entry if it's just a raw degree with no other info
                    continue

                education_list.append(
                    {
                        "degree": degree,
                        "university": university
                        if university
                        else "University Not Detected",
                        "specialization": specialization,
                        "year": year,
                        "gpa": gpa,
                    }
                )

        # Deduplicate
        seen = set()
        final_list = []
        for edu in education_list:
            key = f"{edu['degree']}-{edu['year']}"
            if key not in seen:
                final_list.append(edu)
                seen.add(key)

        return final_list if final_list else None

    # ==================== EXPERIENCE ====================

    @staticmethod
    def _extract_experience(text):
        """Extract work experience"""
        experience_list = []

        # Look for experience section
        lines = text.split("\n")
        in_experience_section = False

        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            # Detect experience section start
            if any(
                keyword in line_lower
                for keyword in ["experience", "work history", "employment"]
            ):
                in_experience_section = True
                continue

            # Detect section end
            if in_experience_section and any(
                keyword in line_lower
                for keyword in ["education", "skills", "projects", "certifications"]
            ):
                break

            # Look for company/job title patterns
            if in_experience_section:
                # Look for date ranges (e.g., "Jan 2020 - Dec 2022")
                date_pattern = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)[\s,]+(\d{4})\s*[-–]\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December|Present|Current)[\s,]*(\d{4})?"

                if re.search(date_pattern, line, re.IGNORECASE):
                    # Found a date range, likely an experience entry
                    match = re.search(date_pattern, line, re.IGNORECASE)
                    start_date = f"{match.group(1)} {match.group(2)}"
                    end_date = (
                        f"{match.group(3)} {match.group(4) if match.group(4) else ''}"
                    )

                    # Company and title are usually in nearby lines
                    company = None
                    title = None
                    description = []

                    # Look backwards for company/title
                    for j in range(max(0, i - 3), i):
                        prev_line = lines[j].strip()
                        if prev_line and len(prev_line) > 3:
                            if not company:
                                company = prev_line
                            elif not title:
                                title = prev_line

                    # Look forward for description
                    # Capture up to 15 lines or until next job/section
                    for j in range(i + 1, min(i + 20, len(lines))):
                        desc_line = lines[j].strip()

                        # Stop if we hit a date pattern (likely next job)
                        if re.search(date_pattern, desc_line, re.IGNORECASE):
                            break

                        # Stop if complex empty line sequence (end of section)
                        if (
                            not desc_line
                            and j + 1 < len(lines)
                            and not lines[j + 1].strip()
                        ):
                            continue

                        if desc_line:
                            # Preserve bullet points
                            if desc_line.startswith(("•", "-", "*", "➢", "·")):
                                description.append(desc_line)
                            else:
                                description.append(desc_line)

                    # Format description with newlines for better display
                    formatted_desc = "\n".join(description) if description else None

                    experience_list.append(
                        {
                            "company": company,
                            "title": title,
                            "start_date": start_date,
                            "end_date": end_date,
                            "description": formatted_desc,
                        }
                    )

        return experience_list if experience_list else None

    @staticmethod
    def _calculate_total_experience(text):
        """Calculate total years of experience"""
        # Look for explicit mentions
        exp_patterns = [
            r"(\d+)[\+]?\s*(?:years?|yrs?)\s*(?:of)?\s*experience",
            r"experience[:\s]+(\d+)[\+]?\s*(?:years?|yrs?)",
        ]

        for pattern in exp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))

        # Calculate from experience dates
        experience = EnhancedResumeParser._extract_experience(text)
        if experience:
            total_months = 0
            for exp in experience:
                try:
                    start = date_parser.parse(exp["start_date"], fuzzy=True)
                    if (
                        "present" in exp["end_date"].lower()
                        or "current" in exp["end_date"].lower()
                    ):
                        end = datetime.now()
                    else:
                        end = date_parser.parse(exp["end_date"], fuzzy=True)

                    months = (end.year - start.year) * 12 + (end.month - start.month)
                    total_months += months
                except:
                    pass

            if total_months > 0:
                return round(total_months / 12, 1)

        return None

    # ==================== PROJECTS ====================

    @staticmethod
    def _extract_projects(text):
        """Extract project details"""
        projects_list = []

        lines = text.split("\n")
        in_projects_section = False

        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            if any(
                keyword in line_lower
                for keyword in ["projects", "project work", "academic projects"]
            ):
                in_projects_section = True
                continue

            if in_projects_section and any(
                keyword in line_lower
                for keyword in ["experience", "education", "certifications", "skills"]
            ):
                break

            if in_projects_section and line.strip() and len(line.strip()) > 5:
                # Potential project title
                title = line.strip()
                technologies = []
                description = []

                # Look for technologies and description in next few lines
                for j in range(i + 1, min(i + 15, len(lines))):
                    next_line = lines[j].strip()

                    if next_line:
                        # Stop if we hit a new potential project title (short line, capitalized) or section
                        if (
                            len(next_line) < 40
                            and j > i + 2
                            and not any(
                                kw in next_line.lower()
                                for kw in EnhancedResumeParser.TECHNICAL_SKILLS
                            )
                            and next_line[0].isupper()
                        ):
                            # Only break if it really looks like a header (no bullet)
                            if not next_line.startswith(("•", "-", "*", "➢")):
                                break

                        # Check for technology keywords
                        for tech in EnhancedResumeParser.TECHNICAL_SKILLS:
                            if tech.lower() in next_line.lower():
                                technologies.append(tech)

                        description.append(next_line)

                if title:
                    projects_list.append(
                        {
                            "title": title[:100],
                            "technologies": list(set(technologies))[
                                :15
                            ],  # Unique, max 15
                            "description": "\n".join(description)
                            if description
                            else None,
                            "domain": EnhancedResumeParser._determine_project_domain(
                                title + " ".join(description)
                            ),
                        }
                    )

                if len(projects_list) >= 5:  # Limit to 5 projects
                    break

        return projects_list if projects_list else None

    @staticmethod
    def _determine_project_domain(text):
        """Determine project domain"""
        text_lower = text.lower()

        if any(
            kw in text_lower
            for kw in ["web", "website", "e-commerce", "portal", "dashboard"]
        ):
            return "Web"
        elif any(kw in text_lower for kw in ["mobile", "android", "ios", "app"]):
            return "Mobile"
        elif any(
            kw in text_lower
            for kw in ["ai", "ml", "machine learning", "deep learning", "neural"]
        ):
            return "AI/ML"
        elif any(
            kw in text_lower for kw in ["data", "analytics", "visualization", "bi"]
        ):
            return "Data"
        elif any(kw in text_lower for kw in ["cloud", "aws", "azure", "devops"]):
            return "Cloud"
        else:
            return "Other"

    # ==================== CERTIFICATIONS ====================

    @staticmethod
    def _extract_certifications(text):
        """Extract certifications"""
        certifications_list = []

        lines = text.split("\n")
        in_cert_section = False

        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            if any(
                keyword in line_lower
                for keyword in ["certification", "certificate", "courses", "training"]
            ):
                in_cert_section = True
                continue

            if in_cert_section and any(
                keyword in line_lower
                for keyword in ["experience", "education", "projects", "skills"]
            ):
                break

            if in_cert_section and line.strip() and len(line.strip()) > 5:
                cert_name = line.strip()
                issuer = None
                year = None

                # Look for issuer and year in next line
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()

                    # Extract year
                    year_match = re.search(r"(19|20)\d{2}", next_line)
                    if year_match:
                        year = int(year_match.group(0))

                    # Issuer is the rest of the line
                    if next_line:
                        issuer = re.sub(r"\d{4}", "", next_line).strip()[:100]

                certifications_list.append(
                    {"name": cert_name[:150], "issuer": issuer, "year": year}
                )

                if len(certifications_list) >= 10:  # Limit to 10
                    break

        return certifications_list if certifications_list else None

    # ==================== CATEGORIZATION ====================

    @staticmethod
    def _categorize_candidate_type(text):
        """Determine if candidate is Fresher or Experienced"""
        total_exp = EnhancedResumeParser._calculate_total_experience(text)

        if total_exp is None or total_exp < 1:
            return "FRESHER"
        else:
            return "EXPERIENCED"

    @staticmethod
    def _determine_role_fit(text):
        """Determine best role fit based on skills"""
        text_lower = text.lower()

        role_keywords = {
            "Frontend Developer": [
                "react",
                "angular",
                "vue",
                "html",
                "css",
                "javascript",
                "typescript",
                "frontend",
            ],
            "Backend Developer": [
                "django",
                "flask",
                "node.js",
                "express",
                "spring boot",
                "backend",
                "api",
            ],
            "Full Stack Developer": [
                "full stack",
                "fullstack",
                "mern",
                "mean",
                "django",
                "react",
            ],
            "Data Analyst": [
                "data analysis",
                "excel",
                "power bi",
                "tableau",
                "sql",
                "analytics",
            ],
            "Data Scientist": [
                "machine learning",
                "data science",
                "python",
                "tensorflow",
                "pytorch",
            ],
            "DevOps Engineer": [
                "devops",
                "docker",
                "kubernetes",
                "jenkins",
                "aws",
                "azure",
                "ci/cd",
            ],
            "Mobile Developer": [
                "android",
                "ios",
                "react native",
                "flutter",
                "swift",
                "kotlin",
            ],
            "UI/UX Designer": ["figma", "adobe xd", "sketch", "ui", "ux", "design"],
            "QA Engineer": [
                "testing",
                "selenium",
                "automation",
                "qa",
                "quality assurance",
            ],
            "HR Professional": [
                "hr",
                "human resource",
                "recruitment",
                "talent acquisition",
            ],
        }

        role_scores = {}
        for role, keywords in role_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                role_scores[role] = score

        if role_scores:
            return max(role_scores, key=role_scores.get)

        return "General"

    @staticmethod
    def _determine_domain(text):
        """Determine industry domain"""
        text_lower = text.lower()

        if any(
            kw in text_lower
            for kw in ["software", "developer", "programming", "coding", "tech"]
        ):
            return "IT"
        elif any(
            kw in text_lower
            for kw in ["finance", "banking", "accounting", "investment"]
        ):
            return "Finance"
        elif any(
            kw in text_lower for kw in ["healthcare", "medical", "hospital", "pharma"]
        ):
            return "Healthcare"
        elif any(
            kw in text_lower for kw in ["marketing", "sales", "business development"]
        ):
            return "Marketing"
        elif any(kw in text_lower for kw in ["hr", "human resource", "recruitment"]):
            return "HR"
        else:
            return "General"

    # ==================== DUPLICATE DETECTION ====================

    @staticmethod
    def _generate_hash(text):
        """Generate hash for duplicate detection"""
        # Normalize text: lowercase, remove extra spaces
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()
