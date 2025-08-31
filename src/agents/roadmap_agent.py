import instructor
import google.generativeai as genai
import json
from typing import List, Dict
from models.roadmap import GeneratedRoadmap
from core.settings import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
client = instructor.from_gemini(genai.GenerativeModel(model_name="gemini-1.5-flash"))


def generate_roadmap(
    jobs_data: List[Dict[str, str]], graduation_year: int
) -> GeneratedRoadmap:
    """Generates a personalized and styled learning roadmap for a student."""
    from datetime import datetime

    current_year = datetime.now().year
    current_month = datetime.now().month
    years_left = max(1, graduation_year - current_year)
    months_left = years_left * 12 - (current_month - 1)
    timeline_desc = f"{years_left} year(s) ({months_left} months) until graduation in {graduation_year}."

    job_titles = [job.get("title", "") for job in jobs_data]
    companies = [job.get("company", "") for job in jobs_data]
    technologies = []
    for job in jobs_data:
        tech_list = job.get("technologies", [])
        if isinstance(tech_list, list):
            technologies.extend(tech_list)

    unique_tech = list(set(technologies))
    tech_frequency = {tech: technologies.count(tech) for tech in unique_tech}

    sorted_tech = sorted(tech_frequency.items(), key=lambda x: x[1], reverse=True)

    jobs_json_string = json.dumps(
        jobs_data, indent=2
    )  # Use ALL job data, not just first 30

    prompt = f"""
    You are an elite career strategist, learning designer, and technical mentor with 20+ years of experience 
    helping students transition into successful tech careers. Your mission is to create an extraordinary, 
    comprehensive, and actionable learning roadmap that will transform this student into the ideal candidate 
    for their target roles.

    ================================================================================
    CRITICAL ANALYSIS INSTRUCTIONS - DEEP JOB DATA MINING
    ================================================================================
    
    You MUST perform an EXHAUSTIVE analysis of EVERY single job description provided. This is critical for 
    creating a truly personalized roadmap. Analyze each job posting for:

    1. **COMPLETE TECHNICAL SKILLS EXTRACTION**:
       - Extract EVERY programming language mentioned across ALL job descriptions
       - Identify ALL frameworks, libraries, tools, and technologies
       - Note specific versions, years of experience, and proficiency levels required
       - Map skill frequency across all jobs to prioritize learning order
       - Identify skill combinations that appear together frequently
       - Extract cloud platforms, databases, DevOps tools, testing frameworks
       - Note architecture patterns, design paradigms, and methodologies
       - Capture any emerging or cutting-edge technologies mentioned

    2. **COMPREHENSIVE QUALIFICATIONS ANALYSIS**:
       - Extract ALL education requirements (degrees, certifications, bootcamps)
       - Analyze experience level requirements (entry, mid, senior)
       - Identify preferred backgrounds and career paths
       - Note any specific project experience requirements
       - Extract portfolio, GitHub, or open-source contribution expectations
       - Analyze salary ranges and compensation details if mentioned

    3. **DETAILED RESPONSIBILITY BREAKDOWN**:
       - Extract EVERY responsibility mentioned across all job descriptions
       - Categorize daily tasks and long-term projects
       - Identify collaboration patterns and team structures
       - Note client interaction and communication requirements
       - Extract project types and business domains
       - Analyze problem-solving scenarios described

    4. **COMPANY CULTURE & ENVIRONMENT ANALYSIS**:
       - Extract company values, mission statements, and culture indicators
       - Identify work environment preferences (remote, hybrid, on-site)
       - Note team sizes, company stages (startup, enterprise, etc.)
       - Analyze growth opportunities and career progression paths
       - Extract benefits, perks, and work-life balance indicators
       - Identify industry sectors and business domains

    5. **SOFT SKILLS & COMPETENCIES DEEP DIVE**:
       - Extract ALL soft skills mentioned across job descriptions
       - Identify communication requirements (written, verbal, presentation)
       - Note leadership, mentorship, and teaching expectations
       - Extract collaboration, teamwork, and cross-functional work requirements
       - Identify problem-solving approaches and analytical thinking patterns
       - Note time management, prioritization, and organizational skills
       - Extract adaptability, learning, and growth mindset requirements

    6. **HIDDEN PATTERNS & INSIGHTS**:
       - Identify unstated requirements that appear between the lines
       - Spot industry trends emerging from multiple job descriptions
       - Recognize common career progression patterns
       - Identify skill gaps in the current market
       - Note any unique or specialized requirements
       - Extract performance metrics and success criteria mentioned

    7. **GEOGRAPHIC & MARKET ANALYSIS**:
       - Analyze job locations and market concentrations
       - Identify salary variations by location
       - Note remote work policies and flexibility
       - Extract market demand indicators
       - Identify regional technology preferences

    8. **JOB POSTING LANGUAGE ANALYSIS**:
       - Identify commonly used keywords and phrases
       - Extract specific terminology and jargon
       - Note required vs. preferred qualifications patterns
       - Analyze urgency indicators and hiring timeline clues
       - Extract company growth indicators from job descriptions

    ================================================================================
    STUDENT CONTEXT & TIMELINE
    ================================================================================
    
    Current Date: {datetime.now().strftime('%B %Y')}
    Graduation Timeline: {timeline_desc}
    Available Learning Time: {months_left} months to become job-ready
    
    ================================================================================
    COMPLETE JOB MARKET DATA FOR ANALYSIS
    ================================================================================
    
    Target Job Titles: {', '.join(job_titles)}
    Target Companies: {', '.join(companies)}
    Most In-Demand Technologies: {', '.join([tech[0] for tech in sorted_tech[:10]])}
    
    COMPLETE JOB DESCRIPTIONS TO ANALYZE:
    {jobs_json_string}
    
    ================================================================================
    ROADMAP CREATION REQUIREMENTS - BASED ON JOB DATA ANALYSIS
    ================================================================================
    
    Using your deep analysis of the job data above, create a WORLD-CLASS learning roadmap that directly 
    addresses every pattern, requirement, and insight you've discovered. The roadmap must:

    **STRUCTURE REQUIREMENTS:**
    
    1. **Data-Driven Timeline Granularity**:
       - Create quarters based on skill complexity found in job descriptions
       - Prioritize skills by their frequency across ALL job postings
       - Sequence learning based on prerequisite patterns found in job requirements
       - Include monthly milestones that directly match job description expectations
       - Add weekly focus areas for the most critical skills identified

    2. **Job-Data-Informed Skill Categories**:
       
       A. **FOUNDATIONAL SKILLS** (Directly from job requirements analysis):
          - Focus on the most fundamental technologies found across ALL job descriptions
          - Prioritize based on how frequently they appear as "required" vs "preferred"
          - Include specific versions and proficiency levels mentioned in job postings
          - Build learning path that matches the prerequisite patterns found
       
       B. **CORE TECHNICAL SKILLS** (Based on job responsibility analysis):
          - Deep dive into the most frequently mentioned technical requirements
          - Include specific frameworks, tools, and technologies from job descriptions
          - Match learning depth to the experience levels required in job postings
          - Include specific project types and scenarios mentioned in job descriptions
       
       C. **ADVANCED & SPECIALIZED SKILLS** (From senior-level requirements):
          - Focus on skills mentioned in higher-level positions
          - Include cutting-edge technologies found in job descriptions
          - Address specialized requirements unique to target companies
          - Include specific architecture and design patterns mentioned
       
       D. **COMPANY-SPECIFIC PREPARATION** (From company culture analysis):
          - Include skills and approaches specific to target companies
          - Address industry-specific requirements found in job descriptions
          - Prepare for specific work environments and team structures identified
          - Include domain knowledge relevant to target business sectors

    3. **Job-Description-Driven Learning Resources**:
       For EACH skill identified in job descriptions, provide:
       - Resources that match the specific proficiency levels required
       - Learning paths that address the exact use cases mentioned in job postings
       - Projects that mirror the responsibilities described in job descriptions
       - Validation methods that match how skills are tested in interviews
       - Time investments that align with experience requirements

    4. **Job-Posting-Inspired Project Requirements**:
       - Create projects that directly simulate work described in job postings
       - Include technology stacks exactly as mentioned in job descriptions
       - Design project complexity to match experience levels required
       - Include collaboration elements that mirror team structures described
       - Address specific business problems mentioned in job descriptions

    5. **Company-Aligned Milestone Checkpoints**:
       - Create assessments that match evaluation criteria mentioned in job postings
       - Include portfolio requirements that address specific company needs
       - Design mock interviews based on actual interview processes described
       - Include networking goals that target the specific companies identified

    6. **Job-Data-Informed Networking & Community**:
       - Target meetups and communities relevant to companies and roles identified
       - Include networking strategies specific to target industries
       - Address professional development mentioned in job descriptions
       - Include thought leadership activities that match company cultures

    ================================================================================
    HTML/CSS DESIGN SPECIFICATIONS
    ================================================================================
    
    **CRITICAL**: Output MUST be a single, self-contained HTML string with ALL styling inline.
    
    **HTML Structure**:
    ```
    <style>
      /* All CSS here - no external stylesheets */
    </style>
    <div class="roadmap-container">
      <!-- All content here -->
    </div>
    ```
    
    **Design Requirements**:
    
    1. **Color Scheme**:
       - Primary: #2563eb (Modern blue)
       - Secondary: #10b981 (Success green)
       - Accent: #8b5cf6 (Purple for highlights)
       - Warning: #f59e0b (For important notes)
       - Background: #f8fafc (Light gray-blue)
       - Card Background: #ffffff
       - Text Primary: #1e293b
       - Text Secondary: #64748b

    2. **Typography**:
       - Font Stack: 'Inter', 'SF Pro Display', 'Segoe UI', system-ui, sans-serif
       - Main Title: 48px, bold, with gradient effect
       - Section Headers: 32px, semi-bold
       - Card Headers: 20px, medium
       - Body Text: 16px, regular
       - Small Text: 14px

    3. **Layout Components**:
       
       A. **Hero Section**:
          - Display insights derived from job data analysis
          - Show personalized statistics based on actual job requirements
          - Include timeline overview with job-market-aligned milestones
          - Highlight top skills identified from job description analysis
       
       B. **Job Market Insights Section**:
          - Display analysis results from job descriptions
          - Show skill frequency charts based on actual data
          - Include company-specific insights and requirements
          - Highlight market trends discovered in job postings
       
       C. **Data-Driven Timeline Sections**:
          - Visual timeline based on skill complexity from job data
          - Quarter sections prioritized by job requirement frequency
          - Monthly breakdown aligned with experience level progressions
          - Skill progression directly mapped to job requirements
       
       D. **Job-Aligned Skill Cards**:
          - Skills prioritized exactly as they appear in job descriptions
          - Experience levels matching job posting requirements
          - Learning resources targeting specific job description needs
          - Time investments aligned with experience requirements
       
       E. **Job-Simulation Project Cards**:
          - Projects that replicate work described in job postings
          - Technology combinations exactly as mentioned in job descriptions
          - Complexity levels matching experience requirements
          - Business contexts from actual job responsibilities

    4. **Interactive Elements** (CSS only):
       - Hover effects showing job-specific insights
       - Progress tracking aligned with job requirement milestones
       - Skill completion checkboxes that match job prerequisites
       - Company-specific badges and indicators

    5. **Responsive Considerations**:
       - Design that works across all devices mentioned in job descriptions
       - Layouts that reflect modern development practices required by companies
       - Performance optimizations that match technical standards mentioned

    ================================================================================
    CONTENT QUALITY REQUIREMENTS - HEAVY JOB DATA USAGE
    ================================================================================
    
    1. **Direct Job Description Integration**:
       - Quote specific requirements from actual job postings
       - Reference exact technologies, versions, and experience levels mentioned
       - Include specific company names and their unique requirements
       - Address exact responsibilities and daily tasks described
       - Match language and terminology used in job descriptions

    2. **Market-Driven Actionability**:
       - Every recommendation must trace back to specific job postings
       - Include exact skill combinations found in job descriptions
       - Provide learning paths that match career progressions described
       - Address specific interview processes and requirements mentioned

    3. **Company-Specific Motivation**:
       - Include actual company values and culture elements found in job postings
       - Reference specific growth opportunities mentioned in job descriptions
       - Include real salary ranges and compensation data from postings
       - Address specific challenges and opportunities described by companies

    4. **Job-Data-Driven Adaptability**:
       - Create different paths for different company types identified
       - Include options for various experience levels found in job postings
       - Address geographic variations discovered in job data
       - Provide alternatives for different industry focuses found

    5. **Real-World Industry Insights**:
       - Extract and include actual industry trends from job descriptions
       - Reference specific tools, processes, and methodologies mentioned
       - Include actual team structures and collaboration patterns described
       - Address real business problems and contexts from job postings

    ================================================================================
    SPECIAL SECTIONS BASED ON JOB DATA ANALYSIS
    ================================================================================
    
    1. **"Target Company Deep Dive"** Section:
       - Detailed analysis of each company found in job descriptions
       - Specific requirements, culture, and expectations per company
       - Tailored preparation strategies for each target organization
       - Industry context and business domain analysis

    2. **"Job Description Decoder"** Section:
       - Translation of common job posting language and requirements
       - Hidden meanings behind frequently used phrases
       - Red flags and green flags in job postings identified
       - How to read between the lines of job requirements

    3. **"Market Reality Check"** Section:
       - Honest assessment of competition based on job requirements
       - Skill gaps identified in the current market
       - Opportunities for differentiation discovered in job data
       - Realistic timeline expectations based on requirement complexity

    4. **"Company-Specific Interview Prep"**:
       - Interview preparation tailored to each company's requirements
       - Technical challenges based on actual job responsibilities
       - Cultural fit preparation based on company values found in postings
       - Specific portfolio requirements per company

    5. **"Salary & Negotiation Intelligence"**:
       - Compensation analysis based on job posting data
       - Skill-to-salary correlation from job descriptions
       - Geographic pay variations discovered
       - Negotiation strategies based on market demand patterns

    ================================================================================
    FINAL OUTPUT REQUIREMENTS
    ================================================================================
    
    The HTML output must:
    1. Heavily reference and utilize EVERY piece of job description data provided
    2. Include specific quotes and requirements from actual job postings
    3. Show clear connections between learning recommendations and job requirements
    4. Address EVERY company and role type found in the job data
    5. Include analysis insights that could only come from the provided job descriptions
    6. Reference specific technologies, tools, and requirements by their exact names
    7. Include company-specific preparation sections
    8. Show skill prioritization based on actual job posting frequency
    9. Include market insights derived from the collective job data analysis
    10. Demonstrate deep understanding of the provided job market landscape

    Remember: This roadmap must prove that you've thoroughly analyzed every single job description 
    provided. Every recommendation, timeline, and resource must be traceable back to insights 
    derived from the job data. Make it obvious that this roadmap could only have been created 
    by someone who deeply understands the specific job market represented in the data.
    
    Now, perform your exhaustive analysis of the job descriptions and create this data-driven, 
    comprehensive, and transformative learning roadmap!
    """
    try:
        roadmap = client.create(
            response_model=GeneratedRoadmap,
            messages=[{"role": "user", "content": prompt}],
        )
        return roadmap
    except Exception as e:
        print(f"Error generating roadmap: {e}")
        # Enhanced error fallback
        return GeneratedRoadmap(
            roadmap_html="""
            <style>
                .error-container {
                    font-family: 'Segoe UI', sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 30px;
                    background: #fff;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .error-title {
                    color: #e74c3c;
                    font-size: 24px;
                    margin-bottom: 15px;
                }
                .error-message {
                    color: #555;
                    line-height: 1.6;
                }
                .retry-button {
                    margin-top: 20px;
                    padding: 10px 20px;
                    background: #3498db;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                }
            </style>
            <div class="error-container">
                <h2 class="error-title">⚠️ Roadmap Generation Error</h2>
                <p class="error-message">
                    We encountered an issue while generating your personalized roadmap. 
                    This might be due to high demand or a temporary service interruption.
                    Please try again in a few moments.
                </p>
                <button class="retry-button" onclick="location.reload()">Retry Generation</button>
            </div>
            """
        )
