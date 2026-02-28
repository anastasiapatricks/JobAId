export interface ResumeUploadResponse {
  session_id: string;
  resume_text: string;
  message: string;
}

export interface ResumeInfo {
  contact_info: {
    name?: string;
    email?: string;
    phone?: string;
    location?: string;
  };
  professional_summary?: string;
  skills: {
    technical: string[];
    soft: string[];
    certifications: string[];
  };
  experience: {
    title?: string;
    company?: string;
    duration?: string;
    description?: string;
  }[];
  education: {
    degree?: string;
    institution?: string;
    year?: string;
  }[];
  industry_terms: string[];
  years_of_experience?: number;
}
