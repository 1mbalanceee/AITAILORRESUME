// API endpoints for the Resume Tailor
const API_BASE_URL = 'http://localhost:8000';

export interface ApplicationOut {
  id: number;
  created_at: string;
  updated_at: string;
  job_title: string | null;
  company: string | null;
  job_url: string | null;
  match_score?: number;
  match_report?: string;
  work_mode?: string;
  experience_gap?: string;
  salary_range?: string;
  status: string;
  kanban_status: string;
  gdoc_url?: string;
  cover_letter?: string;
  tailoring_report?: string;
  notes?: string;
  report?: any; // For frontend-parsed report object
}

export interface GenerateResumeResponse {
  application_id: number;
  gdoc_url: string;
  cover_letter: string;
  tailoring_report: string;
}

export const fetchApplications = async (): Promise<ApplicationOut[]> => {
  const response = await fetch(`${API_BASE_URL}/applications`);
  if (!response.ok) throw new Error('Failed to fetch applications');
  return response.json();
};

export const fetchApplicationDetails = async (id: number): Promise<ApplicationOut> => {
  const response = await fetch(`${API_BASE_URL}/applications/${id}`);
  if (!response.ok) throw new Error('Failed to fetch application details');
  return response.json();
};

export const analyzeJob = async (jobUrl: string): Promise<any> => {
  const response = await fetch(`${API_BASE_URL}/analyze-job`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jd_url: jobUrl }),
  });
  if (!response.ok) throw new Error('Failed to analyze job');
  return response.json();
};

export const generateResume = async (applicationId: number, notes?: string): Promise<GenerateResumeResponse> => {
  const response = await fetch(`${API_BASE_URL}/generate-resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ application_id: applicationId, custom_note: notes }),
  });
  if (!response.ok) throw new Error('Failed to generate resume');
  return response.json();
};

export const deleteApplication = async (id: number): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/applications/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete application');
};

export const updateApplicationStatus = async (id: number, status: string): Promise<ApplicationOut> => {
  const response = await fetch(`${API_BASE_URL}/applications/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  if (!response.ok) throw new Error('Failed to update status');
  return response.json();
};

export const updateKanbanStatus = async (id: number, kanbanStatus: string): Promise<ApplicationOut> => {
  const response = await fetch(`${API_BASE_URL}/applications/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kanban_status: kanbanStatus }),
  });
  if (!response.ok) throw new Error('Failed to update kanban status');
  return response.json();
};

export const dismissApplication = async (id: number): Promise<void> => {
  // We can treat dismissal as moving to an 'archived' status or just deleting it
  // For now, let's just delete it to match previous behavior
  return deleteApplication(id);
};
