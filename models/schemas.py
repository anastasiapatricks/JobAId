"""Pydantic models for structured data validation."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ContactInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None


class Skills(BaseModel):
    technical: List[str] = Field(default_factory=list)
    soft: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None


class EducationEntry(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[str] = None


class ResumeInfo(BaseModel):
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    professional_summary: Optional[str] = None
    skills: Skills = Field(default_factory=Skills)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    industry_terms: List[str] = Field(default_factory=list)
    years_of_experience: Optional[int] = None


class ParsingConfidence(BaseModel):
    confidence: float = 0.0
    missing_fields: List[str] = Field(default_factory=list)
    probing_questions: List[str] = Field(default_factory=list)


class JobListing(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    url: Optional[str] = None
    source: str = "mock"


class ScoredJob(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    score: int = 0
    explanation: str = ""
    keywords: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    url: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    created_at: Optional[str] = None
    category: Optional[str] = None
    source: str = "mock"


class SkillGap(BaseModel):
    skill: str
    importance: str = "medium"
    category: str = "technical"


class UpskillingItem(BaseModel):
    skill: str
    priority: int = 1
    recommended_courses: List[str] = Field(default_factory=list)
    estimated_time: Optional[str] = None


class SalaryInsights(BaseModel):
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    median_salary: Optional[float] = None
    currency: str = "SGD"
    experience_level: Optional[str] = None
    source: str = "seed_data"


class DecisionLogEntry(BaseModel):
    stage: str
    action: str
    reasoning: str
    timestamp: Optional[str] = None
