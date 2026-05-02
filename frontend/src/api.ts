const API_URL = 'http://localhost:8000';

export interface ApplicationOut {
  id: number;
  created_at: string;
  job_title: string | null;
  company: string | null;
  job_url: string | null;
  match_score?: number;
  work_mode?: string;
  status: string;
  kanban_status: string;
  gdoc_url?: string;
  applicants_count: number | null;
}

export interface MatchMarkers {
  work_mode?: string | null;
  location?: string | null;
  experience_gap?: string | null;
  salary_range?: string | null;
  relocation_required: boolean;
  visa_sponsorship: boolean;
}

export interface AnalyzeJobResponse {
  application_id: number;
  match: boolean;
  score: number;
  job_title: string | null;
  company: string | null;
  markers: MatchMarkers;
  matched_skills: string[];
  missing_skills: string[];
  applicants_count: number | null;
  recommendation: string;
}

export interface ResumeChange {
  original: string;
  tailored: string;
  reason?: string;
}

export interface GenerateResumeResponse {
  application_id: number;
  gdoc_url: string | null;
  cover_letter_preview: string;
  changes: ResumeChange[];
  tailored_bullets_count: number;
  status: string;
}

export const fetchApplications = async (): Promise<ApplicationOut[]> => {
  const res = await fetch(`${API_URL}/applications`);
  if (!res.ok) throw new Error('Failed to fetch applications');
  return res.json();
};

export const analyzeJob = async (jd_url?: string, jd_text?: string): Promise<AnalyzeJobResponse> => {
  const res = await fetch(`${API_URL}/analyze-job`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jd_url, jd_text })
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to analyze job');
  }
  return res.json();
};

export const generateResume = async (application_id: number, custom_note?: string): Promise<GenerateResumeResponse> => {
  const res = await fetch(`${API_URL}/generate-resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ application_id, approved: true, custom_note })
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to generate resume');
  }
  return res.json();
};

export const fetchApplicationDetails = async (id: number): Promise<any> => {
  const res = await fetch(`${API_URL}/applications/${id}`);
  if (!res.ok) throw new Error('Failed to fetch application details');
  return res.json();
};

export const deleteApplication = async (id: number): Promise<void> => {
  const res = await fetch(`${API_URL}/applications/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete application');
};

export const updateApplicationStatus = async (id: number, status: string): Promise<void> => {
  const res = await fetch(`${API_URL}/applications/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status })
  });
  if (!res.ok) throw new Error('Failed to update status');
};

export const updateKanbanStatus = async (id: number, kanban_status: string): Promise<void> => {
  const res = await fetch(`${API_URL}/api/applications/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kanban_status })
  });
  if (!res.ok) throw new Error('Failed to update kanban status');
};
