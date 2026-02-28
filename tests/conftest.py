"""Shared test fixtures for JobAId tests."""

import pytest


@pytest.fixture
def sample_resume_text():
    """Realistic resume text for testing."""
    return """
    John Doe
    Email: john.doe@example.com
    Phone: +65 9123 4567

    Professional Summary:
    He is an experienced software engineer with 5 years of experience in Python,
    Java, and cloud technologies. Passionate about building scalable systems.

    Skills: Python, Java, AWS, Docker, Kubernetes, PostgreSQL, React

    Experience:
    Senior Software Engineer at TechCorp (2021-2024)
    - Built microservices architecture serving 1M+ users
    - Led team of 4 engineers

    Software Engineer at StartupXYZ (2019-2021)
    - Developed REST APIs using FastAPI
    - Implemented CI/CD pipelines

    Education:
    Bachelor of Computer Science, National University of Singapore (2019)
    """


@pytest.fixture
def sample_resume_info():
    """Parsed resume info structure."""
    return {
        "contact_info": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+65 9123 4567",
        },
        "professional_summary": "He is an experienced software engineer with 5 years of experience.",
        "skills": ["Python", "Java", "AWS", "Docker", "Kubernetes"],
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "TechCorp",
                "duration": "2021-2024",
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Computer Science",
                "institution": "National University of Singapore",
            }
        ],
    }


@pytest.fixture
def sample_state(sample_resume_info):
    """Sample pipeline state with all fields populated."""
    return {
        "resume_info": sample_resume_info,
        "scored_jobs": [
            {"title": "Backend Engineer", "company": "Google", "score": 0.92},
            {"title": "Software Engineer", "company": "Grab", "score": 0.88},
        ],
        "skill_gaps": [
            {"skill": "Terraform", "priority": "high"},
            {"skill": "GraphQL", "priority": "medium"},
        ],
        "final_pitch": "Dear Hiring Manager, I am writing to express my interest...",
    }
