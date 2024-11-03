import streamlit as st
import google.generativeai as genai
import PyPDF2 as pdf
from dotenv import load_dotenv
import os
import plotly.graph_objects as go
import pandas as pd

load_dotenv()

# Configure Gemini AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Career levels and their descriptions
CAREER_LEVELS = {
    "Entry-level": "Students & recent graduates. Less than 2 years of work experience.",
    "Mid-level": "You have between 2 and 10 years of relevant work experience.",
    "Senior-level": "You have more than 10 years of relevant work experience."
}

# Predefined job roles and their descriptions
JOB_ROLES = {
    "Software Engineer": """Looking for a Software Engineer with strong programming skills in Python, Java, or C++.
    Experience with web development frameworks, databases, and cloud platforms. Strong problem-solving abilities and
    experience with agile methodologies required.""",

    "Data Scientist": """Seeking a Data Scientist with expertise in machine learning, statistical analysis, and data
    visualization. Proficiency in Python, R, SQL, and experience with deep learning frameworks. Knowledge of big data
    technologies and cloud platforms preferred.""",

    "Data Analyst": """Looking for a Data Analyst with strong SQL skills and experience with data visualization tools
    like Tableau or Power BI. Proficiency in Python or R for data analysis, experience with Excel, and strong
    analytical thinking required.""",

    "Big Data Engineer": """Seeking a Big Data Engineer with expertise in Hadoop ecosystem, Spark, and cloud platforms.
    Strong programming skills in Python or Java, experience with data warehousing, and knowledge of distributed
    computing required."""
}


def get_gemini_response(resume_text, job_description, career_level):
    prompt = f"""You are an advanced ATS (Applicant Tracking System) with expertise in tech recruitment.
    Analyze the provided resume for a {career_level} position with the job description below. Consider the career level
    when analyzing the resume and providing suggestions.

    Resume: {resume_text}
    Job Description: {job_description}
    Career Level: {career_level}

    Please provide your analysis in the following format:

    ATS SCORE: [Provide a percentage match]

    GLOBAL PERCENTILE: [Provide where this resume stands compared to global resumes, as a percentile]

    KEY SKILLS FOUND:
    - [List the matching skills found in the resume]

    MISSING SKILLS:
    - [List important skills from the job description that are missing in the resume]

    EXPERIENCE ANALYSIS:
    - [Analyze if the experience level matches the career level selected]

    PROFILE SUMMARY:
    [Provide a brief evaluation of the candidate's profile]

    IMPROVEMENT SUGGESTIONS:
    - [Provide specific suggestions for improving the resume based on best practices]

    ATS OPTIMIZATION TIPS:
    - [Provide specific tips to increase the ATS score]

    Please ensure each section is clearly labeled with the exact headers shown above.
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating response: {str(e)}")
        return None


def create_gauge_chart(score, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 75], 'color': "gray"},
                {'range': [75, 100], 'color': "lightblue"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 80
            }
        }
    ))

    fig.update_layout(height=300)
    return fig


def parse_gemini_response(response_text):
    """Parse the response text into sections with improved score handling"""
    sections = {
        'ats_score': '0',  # Changed default to string without %
        'global_percentile': '0',
        'key_skills': [],
        'missing_skills': [],
        'experience_analysis': [],
        'profile_summary': '',
        'improvement_suggestions': [],
        'ats_optimization_tips': []
    }

    if response_text:
        current_section = None
        for line in response_text.split('\n'):
            line = line.strip()
            if not line:
                continue

            if "ATS SCORE:" in line.upper():
                current_section = 'ats_score'
                # Improved score parsing
                score_text = line.split(':')[1].strip()
                # Remove any non-digit characters except decimal point
                score = ''.join(
                    c for c in score_text if c.isdigit() or c == '.')
                try:
                    # Convert to float first to handle decimal numbers
                    score_value = float(score)
                    # Round to nearest integer
                    sections['ats_score'] = str(round(score_value))
                except ValueError:
                    sections['ats_score'] = '0'
                continue

            if "GLOBAL PERCENTILE:" in line.upper():
                current_section = 'global_percentile'
                percentile_text = line.split(':')[1].strip()
                # Remove any non-digit characters except decimal point
                percentile = ''.join(
                    c for c in percentile_text if c.isdigit() or c == '.')
                try:
                    # Convert to float first to handle decimal numbers
                    percentile_value = float(percentile)
                    # Round to nearest integer
                    sections['global_percentile'] = str(
                        round(percentile_value))
                except ValueError:
                    sections['global_percentile'] = '0'
                continue

            if "KEY SKILLS FOUND:" in line.upper():
                current_section = 'key_skills'
                continue

            if "MISSING SKILLS:" in line.upper():
                current_section = 'missing_skills'
                continue

            if "EXPERIENCE ANALYSIS:" in line.upper():
                current_section = 'experience_analysis'
                continue

            if "PROFILE SUMMARY:" in line.upper():
                current_section = 'profile_summary'
                continue

            if "IMPROVEMENT SUGGESTIONS:" in line.upper():
                current_section = 'improvement_suggestions'
                continue

            if "ATS OPTIMIZATION TIPS:" in line.upper():
                current_section = 'ats_optimization_tips'
                continue

            if current_section:
                if current_section in ['ats_score', 'global_percentile']:
                    continue
                elif current_section == 'profile_summary':
                    sections[current_section] += line + ' '
                elif current_section in ['key_skills', 'missing_skills', 'experience_analysis',
                                         'improvement_suggestions', 'ats_optimization_tips']:
                    if line.startswith('- '):
                        sections[current_section].append(line[2:])
                    elif line not in ['KEY SKILLS FOUND:', 'MISSING SKILLS:', 'EXPERIENCE ANALYSIS:',
                                      'IMPROVEMENT SUGGESTIONS:', 'ATS OPTIMIZATION TIPS:']:
                        sections[current_section].append(line)

    return sections


def extract_text_from_pdf(uploaded_file):
    try:
        reader = pdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += str(page.extract_text())
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None


# Set page config
st.set_page_config(page_title="Smart ATS", layout="wide",
                   initial_sidebar_state="expanded")

# Custom CSS
st.markdown("""
    <style>
    .stProgress > div > div > div > div {
        background-color: #00ff00;
    }
    .big-font {
        font-size:24px !important;
        font-weight: bold;
    }
    .medium-font {
        font-size:18px !important;
    }
    .highlight {
        background-color:#7d5f8a;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .skills-item {
        background-color: #4f634e;
        padding: 5px 10px;
        border-radius: 15px;
        display: inline-block;
        margin: 5px;
    }
    .career-level-card {
        background-color: #576f96;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 10px 0;
        cursor: pointer;
        transition: transform 0.2s;
    }
    .career-level-card:hover {
        transform: translateY(-5px);
    }
    .selected {
        border: 2px solid #1f77b4;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'career_level' not in st.session_state:
    st.session_state.career_level = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Main UI
st.title("🎯 Smart ATS Resume Analyzer by MZ-tools")
st.markdown("#### Optimize your resume for your dream tech role! 📝")

# Career Level Selection
st.markdown("### 1. What best describes you? 👤")
cols = st.columns(3)
for i, (level, description) in enumerate(CAREER_LEVELS.items()):
    with cols[i]:
        card_style = "selected" if st.session_state.career_level == level else ""
        st.markdown(f"""
            <div class='career-level-card {card_style}' onclick=''>
                <h3>{level}</h3>
                <p>{description}</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button(f"Choose {level}", key=f"btn_{level}"):
            st.session_state.career_level = level

# Initialize analysis before the button block
analysis = {}

if st.session_state.career_level:
    # Job Role Selection
    st.markdown("### 2. Select Job Role 💼")
    role = st.selectbox(
        "Choose the position you're applying for:", list(JOB_ROLES.keys()))

    # Resume Upload
    st.markdown("### 3. Upload Resume 📄")
    uploaded_file = st.file_uploader(
        "Upload your resume (PDF format)", type="pdf")

    if uploaded_file:
        st.markdown("### Job Description Preview 📋")
        st.markdown(f"<div class='highlight'>{
                    JOB_ROLES[role]}</div>", unsafe_allow_html=True)

        if st.button("Analyze Resume ✨"):
            with st.spinner('Analyzing your resume... 🔍'):
                # Extract text and get analysis
                resume_text = extract_text_from_pdf(uploaded_file)
                if resume_text:
                    response = get_gemini_response(
                        resume_text, JOB_ROLES[role], st.session_state.career_level)
                    if response: 
                        analysis = parse_gemini_response(response)

    # Create two columns for the gauge charts
    score_col1, score_col2 = st.columns(2)

    with score_col1:
        # ATS Score Gauge - using the new parsing method
        if analysis:
            score = int(analysis['ats_score'])  # Now safe to convert to int
            fig1 = create_gauge_chart(score, "ATS Match Score")
            st.plotly_chart(fig1, use_container_width=True)

    with score_col2:
        # Global Percentile Gauge - using the new parsing method
        if analysis:
            # Now safe to convert to float
            percentile = float(analysis['global_percentile'])
            fig2 = create_gauge_chart(percentile, "Global Percentile")
            st.plotly_chart(fig2, use_container_width=True)

           # Display results in tabs
    tab1, tab2, tab3 = st.tabs(["Skills Analysis", "Detailed Feedback", "Chat with AI"])

    with tab1:
        if analysis:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### ✅ Matching Skills")
                for skill in analysis['key_skills']:
                    st.markdown(f"<div class='skills-item'>{skill}</div>", unsafe_allow_html=True)

            with col2:
                st.markdown("### ❌ Missing Skills")
                for skill in analysis['missing_skills']:
                    st.markdown(f"<div class='skills-item'>{skill}</div>", unsafe_allow_html=True)

    with tab2:
        if analysis:
            st.markdown("### 📊 Experience Analysis")
            for point in analysis['experience_analysis']:
                st.markdown(f"- {point}")

            st.markdown("### 📝 Profile Summary")
            st.markdown(f"<div class='highlight'>{analysis['profile_summary']}</div>", unsafe_allow_html=True)

            st.markdown("### 💡 Improvement Suggestions")
            for suggestion in analysis['improvement_suggestions']:
                st.markdown(f"- {suggestion}")

            st.markdown("### 🎯 ATS Optimization Tips")
            for tip in analysis['ats_optimization_tips']:
                st.markdown(f"- {tip}")

    with tab3:
        st.markdown("### 💬 Chat with AI about your Resume")

        # Display chat history
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['content']}")
            else:
                st.markdown(f"**AI:** {msg['content']}")

        # Chat input
        user_question = st.text_input("Ask a question about your resume or the analysis:")
        if st.button("Send"):
            if user_question:
                # Add user message to chat history
                st.session_state.chat_history.append({"role": "user", "content": user_question})

                # Generate AI response
                chat_prompt = f"""Based on the resume analysis above, please answer this question:
                {user_question}"""
                try:
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    chat_response = model.generate_content(chat_prompt)

                    # Add AI response to chat history
                    st.session_state.chat_history.append({"role": "assistant", "content": chat_response.text})

                    # Rerun to update chat display
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")

# Footer with tips
st.markdown("---")
st.markdown("### 💪 Tips for Success")
with st.expander("Click to see resume optimization tips"):
    st.markdown("""
    1. **Tailor your resume for each role**
       - Use relevant keywords from the job description
       - Highlight experiences that match the role requirements
    
    2. **Format for ATS Success**
       - Use simple, standard fonts (Arial, Calibri)
       - Avoid tables, images, and complex formatting
       - Use standard section headings """)