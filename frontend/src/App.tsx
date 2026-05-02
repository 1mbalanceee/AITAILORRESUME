import React, { useState, useEffect } from 'react';
import { 
  Sparkles, FileText, CheckCircle, Search, 
  ExternalLink, Plus, Trash2, Archive, 
  AlertCircle, Briefcase, Info
} from 'lucide-react';
import { 
  fetchApplications, analyzeJob, generateResume, 
  fetchApplicationDetails, deleteApplication, updateApplicationStatus
} from './api';
import type { ApplicationOut, GenerateResumeResponse } from './api';

const Spinner = () => (
  <svg className="spinner" viewBox="0 0 50 50">
    <circle className="path" cx="25" cy="25" r="20" fill="none" strokeWidth="5"></circle>
  </svg>
);

const ProgressBar = ({ active, label }: { active: boolean, label: string }) => {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let interval: any;
    if (active) {
      setProgress(0);
      interval = setInterval(() => {
        setProgress(prev => {
          if (prev < 40) return prev + 3;
          if (prev < 80) return prev + 1;
          if (prev < 98) return prev + 0.2;
          return prev;
        });
      }, 150);
    } else {
      setProgress(100);
      const timer = setTimeout(() => setProgress(0), 400);
      return () => clearTimeout(timer);
    }
    return () => clearInterval(interval);
  }, [active]);

  if (!active && progress === 0) return null;

  return (
    <div style={{ width: '100%', marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
        <span>{label}</span>
        <span>{Math.round(progress)}%</span>
      </div>
      <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ 
          width: `${progress}%`, 
          height: '100%', 
          background: 'linear-gradient(90deg, #6366f1, #a855f7)', 
          transition: 'width 0.2s ease-out' 
        }} />
      </div>
    </div>
  );
};

function App() {
  const [applications, setApplications] = useState<ApplicationOut[]>([]);
  const [activeAppId, setActiveAppId] = useState<number | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  
  // App States
  const [url, setUrl] = useState('');
  const [text, setText] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isFetchingDetails, setIsFetchingDetails] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Resume Generation State
  const [customNote, setCustomNote] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [genResult, setGenResult] = useState<GenerateResumeResponse | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await fetchApplications();
      setApplications(data);
    } catch (e) {
      console.error(e);
    }
  };

  const filteredApps = applications.filter(app => 
    showArchived ? app.status === 'archived' : app.status !== 'archived'
  );

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url && !text) {
      setError("Please provide either a URL or Job Description text.");
      return;
    }
    
    setIsAnalyzing(true);
    setError(null);
    setAnalysisResult(null);
    setGenResult(null);
    
    try {
      const res = await analyzeJob(url, text);
      setAnalysisResult({
        ...res,
        id: res.application_id,
        report: {
          markers: res.markers,
          matched_skills: res.matched_skills,
          missing_skills: res.missing_skills,
          recommendation: res.recommendation,
          score: res.score,
          job_title: res.job_title,
          company: res.company
        }
      });
      setActiveAppId(res.application_id);
      loadHistory();
    } catch (e: any) {
      setError(e.message || "An error occurred during analysis.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSelectApplication = async (appId: number) => {
    setIsFetchingDetails(true);
    setActiveAppId(appId);
    setAnalysisResult(null);
    setGenResult(null);
    setError(null);
    try {
      const details = await fetchApplicationDetails(appId);
      setAnalysisResult(details);
      if (details.gdoc_url) {
        setGenResult({
          application_id: details.id,
          gdoc_url: details.gdoc_url,
          cover_letter_preview: details.cover_letter?.substring(0, 500) || '',
          changes: details.report?.changes || [],
          tailored_bullets_count: details.report?.bullets_count || 0,
          status: details.status
        });
      }
    } catch (e: any) {
      setError(e.message || "Failed to load details");
    } finally {
      setIsFetchingDetails(false);
    }
  };

  const handleGenerate = async () => {
    const id = analysisResult?.id || analysisResult?.application_id;
    if (!id) return;
    
    setIsGenerating(true);
    setError(null);
    try {
      const res = await generateResume(id, customNote);
      setGenResult(res);
      // Refresh current view
      const details = await fetchApplicationDetails(id);
      setAnalysisResult(details);
      loadHistory();
    } catch (e: any) {
      setError(`Generation failed: ${e.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleStatusUpdate = async (newStatus: string) => {
    const id = analysisResult?.id || analysisResult?.application_id;
    if (!id) return;
    try {
      await updateApplicationStatus(id, newStatus);
      // Update local state immediately
      setAnalysisResult((prev: any) => ({ ...prev, status: newStatus }));
      if (genResult) setGenResult((prev: any) => ({ ...prev, status: newStatus }));
      loadHistory();
    } catch (e: any) {
      setError("Failed to update status: " + e.message);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!window.confirm("Permanently delete this entry?")) return;
    try {
      await deleteApplication(id);
      if (activeAppId === id) handleNew();
      loadHistory();
    } catch (e: any) {
      setError("Failed to delete: " + e.message);
    }
  };

  const handleNew = () => {
    setActiveAppId(null);
    setAnalysisResult(null);
    setGenResult(null);
    setUrl('');
    setText('');
    setCustomNote('');
    setError(null);
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <h1><Sparkles size={24} /> AI Resume Tailor</h1>
        </div>
        
        <button className="new-btn" onClick={handleNew}>
          <Plus size={18} /> New Application
        </button>

        <div style={{ padding: '0 16px', marginBottom: 16 }}>
          <div style={{ display: 'flex', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', padding: '4px' }}>
            <button 
              onClick={() => setShowArchived(false)}
              style={{ flex: 1, padding: '6px', borderRadius: '6px', fontSize: '0.8rem', background: !showArchived ? 'var(--bg-panel)' : 'transparent', color: !showArchived ? 'white' : 'var(--text-muted)' }}
            >
              Active
            </button>
            <button 
              onClick={() => setShowArchived(true)}
              style={{ flex: 1, padding: '6px', borderRadius: '6px', fontSize: '0.8rem', background: showArchived ? 'var(--bg-panel)' : 'transparent', color: showArchived ? 'white' : 'var(--text-muted)' }}
            >
              Archive
            </button>
          </div>
        </div>

        <div className="history-list">
          {filteredApps.map(app => (
            <div 
              key={app.id} 
              className={`history-item ${activeAppId === app.id ? 'active' : ''}`}
              onClick={() => handleSelectApplication(app.id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <div className="history-title">{app.job_title || 'Untitled'}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Briefcase size={12} /> {app.company || 'Unknown'}
                  </div>
                </div>
                {app.gdoc_url && <FileText size={16} style={{ color: 'var(--accent)', opacity: 0.8 }} />}
              </div>
              
              <div className="history-meta" style={{ marginTop: 8 }}>
                <span>{new Date(app.created_at).toLocaleDateString()}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {app.applicants_count !== undefined && app.applicants_count !== null && (
                    <span style={{ 
                      fontSize: '0.65rem', 
                      padding: '2px 6px', 
                      borderRadius: '4px', 
                      background: app.applicants_count > 300 ? 'rgba(239, 68, 68, 0.2)' : app.applicants_count > 100 ? 'rgba(251, 191, 36, 0.2)' : 'rgba(34, 197, 94, 0.2)',
                      color: app.applicants_count > 300 ? '#f87171' : app.applicants_count > 100 ? '#fbbf24' : '#4ade80'
                    }}>
                      {app.applicants_count} app.
                    </span>
                  )}
                  <span className={`score-badge ${app.match_score! > 0.7 ? 'high' : app.match_score! > 0.4 ? 'medium' : 'low'}`}>
                    {Math.round(app.match_score! * 100)}%
                  </span>
                </div>
              </div>
              
              {app.status === 'applied' && (
                <div style={{ marginTop: 6, fontSize: '0.7rem', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <CheckCircle size={10} /> APPLIED
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        <div className="content-wrapper">
          
          {error && (
            <div className="error-box" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#f87171', padding: '16px', borderRadius: '12px', marginBottom: '24px', border: '1px solid rgba(239,68,68,0.2)', display: 'flex', gap: '12px' }}>
              <AlertCircle size={20} />
              <div style={{ flex: 1 }}>{error}</div>
              <button onClick={() => setError(null)}>✕</button>
            </div>
          )}

          {!analysisResult && !isAnalyzing && !isFetchingDetails && (
            <div className="card">
              <h2 className="card-title"><Search size={24} /> New Job Analysis</h2>
              <form onSubmit={handleAnalyze}>
                <div className="form-group">
                  <label className="form-label">Job URL</label>
                  <input type="url" className="form-input" placeholder="https://..." value={url} onChange={e => setUrl(e.target.value)} />
                </div>
                <div style={{ textAlign: 'center', margin: '12px 0', opacity: 0.5 }}>OR</div>
                <div className="form-group">
                  <label className="form-label">Job Text</label>
                  <textarea className="form-textarea" placeholder="Paste JD here..." value={text} onChange={e => setText(e.target.value)} />
                </div>
                <button type="submit" className="btn-primary"><Sparkles size={18} /> Analyze with Gemini</button>
              </form>
            </div>
          )}

          {(isAnalyzing || isGenerating || isFetchingDetails) && (
            <div className="card" style={{ textAlign: 'center' }}>
              <ProgressBar 
                active={isAnalyzing || isGenerating} 
                label={isAnalyzing ? "Gemini is analyzing the job..." : isGenerating ? "Tailoring your resume & bullets..." : "Fetching details..."} 
              />
              <div style={{ marginTop: 24 }}><Spinner /></div>
            </div>
          )}

          {analysisResult && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
                <div>
                  <h2 className="card-title" style={{ marginBottom: 4 }}>{analysisResult.job_title || analysisResult.report?.job_title}</h2>
                  <div style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Briefcase size={16} /> {analysisResult.company || analysisResult.report?.company}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 12 }}>
                  {analysisResult.status !== 'archived' ? (
                    <button className="btn-secondary" onClick={() => handleStatusUpdate('archived')} title="Archive">
                      <Archive size={18} />
                    </button>
                  ) : (
                    <button className="btn-secondary" onClick={() => handleStatusUpdate('analyzed')} title="Restore">
                      <Plus size={18} />
                    </button>
                  )}
                  <button className="btn-secondary" onClick={(e) => handleDelete(e, analysisResult.id)} style={{ color: 'var(--danger)' }} title="Delete Permanently">
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>

              <div className="results-grid">
                <div className="stat-box" style={{ textAlign: 'center' }}>
                  <div className="stat-label">Match Probability</div>
                  <div className="stat-value score" style={{ color: (analysisResult.match_score || analysisResult.report?.score) > 0.7 ? 'var(--accent)' : '#fbbf24' }}>
                    {Math.round((analysisResult.match_score || analysisResult.report?.score || 0) * 100)}%
                  </div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Competition</div>
                  <div style={{ marginTop: 8 }}>
                    {analysisResult.applicants_count !== undefined && analysisResult.applicants_count !== null ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ 
                          width: 10, height: 10, borderRadius: '50%', 
                          background: analysisResult.applicants_count > 300 ? '#ef4444' : analysisResult.applicants_count > 100 ? '#fbbf24' : '#22c55e' 
                        }} />
                        <span style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{analysisResult.applicants_count}</span>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>applicants</span>
                      </div>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>Unknown</span>
                    )}
                  </div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Quick Info</div>
                  <div className="marker-row"><span>Mode</span><strong>{analysisResult.work_mode || analysisResult.report?.markers?.work_mode || 'N/A'}</strong></div>
                  <div className="marker-row"><span>Status</span><strong style={{ color: 'var(--primary)', textTransform: 'uppercase' }}>{analysisResult.status}</strong></div>
                </div>
              </div>

              <div className="recommendation-box">
                <Info size={18} style={{ float: 'left', marginRight: 12, color: 'var(--primary)' }} />
                {analysisResult.report?.recommendation}
              </div>

              <div style={{ marginTop: 24 }}>
                <h3 style={{ fontSize: '1rem', marginBottom: 12, color: 'var(--accent)' }}>Matched Skills</h3>
                <div className="skills-list">
                  {(analysisResult.report?.matched_skills || []).map((s: string, i: number) => (
                    <span key={i} className="skill-tag matched">{s}</span>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: 16 }}>
                <h3 style={{ fontSize: '1rem', marginBottom: 12, color: '#f87171' }}>Missing Skills (Gaps)</h3>
                <div className="skills-list">
                  {(analysisResult.report?.missing_skills || []).map((s: string, i: number) => (
                    <span key={i} className="skill-tag missing">{s}</span>
                  ))}
                </div>
              </div>

              {/* Generation Section */}
              {!genResult && !isGenerating && (
                <div style={{ marginTop: 40, paddingTop: 32, borderTop: '1px solid var(--border)' }}>
                  <h3 style={{ marginBottom: 16 }}>Generate Tailored Assets</h3>
                  <div className="form-group">
                    <label className="form-label">Add a note for the AI (Optional)</label>
                    <input className="form-input" placeholder="e.g. emphasize my leadership skills..." value={customNote} onChange={e => setCustomNote(e.target.value)} />
                  </div>
                  <button className="btn-primary" onClick={handleGenerate}><FileText size={18} /> Tailor Resume & Bullets</button>
                </div>
              )}

              {genResult && (
                <div style={{ marginTop: 40, paddingTop: 32, borderTop: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <h3 style={{ color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 8 }}><CheckCircle size={20} /> Tailoring Ready</h3>
                    {genResult.status !== 'applied' && (
                      <button className="btn-secondary" onClick={() => handleStatusUpdate('applied')} style={{ background: 'var(--accent)', color: 'white', border: 'none' }}>
                        Mark as Applied
                      </button>
                    )}
                  </div>
                  
                  <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
                    <a href={genResult.gdoc_url!} target="_blank" rel="noreferrer" className="gdoc-link" style={{ marginTop: 0, flex: 1 }}>
                      <ExternalLink size={18} /> Open Resume (Google Doc)
                    </a>
                  </div>

                  <div className="cover-letter">
                    <strong style={{ display: 'block', marginBottom: 8 }}>Cover Letter Preview:</strong>
                    {analysisResult.cover_letter || genResult.cover_letter_preview}...
                  </div>

                  {genResult.changes && genResult.changes.length > 0 && (
                    <div style={{ marginTop: 32 }}>
                      <h3 style={{ fontSize: '1.1rem', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Sparkles size={18} style={{ color: 'var(--accent)' }} /> 
                        Key Resume Adjustments
                      </h3>
                      <div className="changes-list">
                        {genResult.changes.map((change, i) => (
                          <div key={i} className="change-item">
                            <div className="change-original">{change.original}</div>
                            <div className="change-tailored">{change.tailored}</div>
                            {change.reason && (
                              <div className="change-reason">
                                <Info size={12} /> {change.reason}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
