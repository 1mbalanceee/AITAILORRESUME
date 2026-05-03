import { useState, useMemo } from 'react';
import { 
  CheckCircle2, 
  Heart, 
  X, 
  ExternalLink, 
  Briefcase, 
  MapPin, 
  Clock,
  Sparkles,
  Search,
  DollarSign,
  TrendingUp
} from 'lucide-react';
import type { ApplicationOut } from '../api';

interface JobFeedProps {
  applications: ApplicationOut[];
  onSave: (id: number) => void;
  onDismiss: (id: number) => void;
  onDiscover: () => void;
  isDiscovering?: boolean;
}

const JobCard = ({ application, onSave, onDismiss }: { application: ApplicationOut, onSave: (id: number) => void, onDismiss: (id: number) => void }) => {
  const score = Math.round((application.match_score || 0) * 100);
  
  const getScoreColor = (s: number) => {
    if (s >= 90) return '#10b981'; // Emerald
    if (s >= 70) return '#6366f1'; // Indigo
    if (s >= 50) return '#fbbf24'; // Amber
    return '#f43f5e'; // Rose
  };

  const getScoreLabel = (s: number) => {
    if (s >= 90) return 'Great Fit';
    if (s >= 70) return 'Strong Fit';
    if (s >= 50) return 'Potential';
    return 'Stretch';
  };

  const color = getScoreColor(score);
  
  let report: any = {};
  try {
    report = typeof application.match_report === 'string' 
      ? JSON.parse(application.match_report) 
      : application.match_report || {};
  } catch(e) {
    report = {};
  }

  const whyFits = report.matched_skills?.slice(0, 3).map((s: string) => s) || [
    "Matches core technical requirements",
    "Company culture alignment",
    "Relevant industry experience"
  ];

  const experience = application.experience_gap || report.markers?.experience_gap;

  return (
    <div className="job-feed-card">
      <div className="card-hero" style={{ background: `linear-gradient(135deg, ${color}15 0%, transparent 100%)` }}>
        <div className="score-display">
          <span className="score-number" style={{ color }}>{score}</span>
          <span className="score-label" style={{ color }}>{getScoreLabel(score)}</span>
        </div>
        
        <div className="job-info">
          <div className="company-name">
            <Briefcase size={14} />
            {application.company || 'Unknown Company'}
          </div>
          <h3 className="job-role">{application.job_title || 'Untitled Role'}</h3>
          <div className="job-tags">
            <span className="job-tag"><MapPin size={12} /> {application.work_mode || 'Remote'}</span>
            {application.salary_range && (
              <span className="job-tag" style={{ color: '#10b981', fontWeight: 'bold', background: 'rgba(16, 185, 129, 0.1)' }}>
                <DollarSign size={12} /> {application.salary_range}
              </span>
            )}
            {experience && (
              <span className="job-tag experience-tag" style={{ border: '1px solid #fbbf24', background: 'rgba(251, 191, 36, 0.1)', color: '#fbbf24', fontWeight: 'bold' }}>
                <Clock size={12} /> {experience}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="why-fits">
        <h4><Sparkles size={12} style={{ display: 'inline', marginRight: 6 }} /> Why it fits</h4>
        <ul className="fits-list">
          {whyFits.map((item: string, idx: number) => (
            <li key={idx} className="fits-item">
              <CheckCircle2 size={16} />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="card-actions">
        <a 
          href={application.job_url || '#'} 
          target="_blank" 
          rel="noopener noreferrer"
          className="btn-secondary"
          style={{ padding: '8px 12px' }}
        >
          <ExternalLink size={16} />
          View Original
        </a>
        
        <div className="action-buttons">
          <button 
            className="icon-btn dismiss" 
            onClick={() => onDismiss(application.id)}
            title="Dismiss"
          >
            <X size={20} />
          </button>
          <button 
            className="icon-btn heart" 
            onClick={() => onSave(application.id)}
            title="Move to Pipeline"
          >
            <Heart size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export const JobFeed = ({ applications, onSave, onDismiss, onDiscover, isDiscovering }: JobFeedProps) => {
  const [searchQuery, setSearchQuery] = useState('');

  // Filtering & Sorting
  const filteredApps = useMemo(() => {
    const filtered = applications.filter(app => {
      const matchesSearch = !searchQuery || 
        (app.job_title?.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (app.company?.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (app.salary_range?.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (app.experience_gap?.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesSearch;
    });

    // Automatic sorting by score descending
    return [...filtered].sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
  }, [applications, searchQuery]);

  // Grouping by discovery session (contiguous blocks within 5 mins)
  const sessions = useMemo(() => {
    if (filteredApps.length === 0) return [];
    
    const sortedByTime = [...filteredApps].sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

    const groups: { time: string, jobs: ApplicationOut[] }[] = [];
    let currentGroup: ApplicationOut[] = [];
    let lastTime: number | null = null;

    sortedByTime.forEach(app => {
      const time = new Date(app.created_at).getTime();
      if (lastTime === null || (lastTime - time) < 300000) { // 5 minutes
        currentGroup.push(app);
      } else {
        // Sort current group by score before finishing it
        const sortedGroup = [...currentGroup].sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
        groups.push({ 
          time: new Date(sortedGroup[0].created_at).toLocaleString('ru-RU', { 
            day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' 
          }), 
          jobs: sortedGroup 
        });
        currentGroup = [app];
      }
      lastTime = time;
    });

    if (currentGroup.length > 0) {
      const sortedGroup = [...currentGroup].sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
      groups.push({ 
        time: new Date(sortedGroup[0].created_at).toLocaleString('ru-RU', { 
          day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' 
        }), 
        jobs: sortedGroup 
      });
    }

    return groups;
  }, [filteredApps]);

  return (
    <div className="feed-container">
      <div style={{ padding: '24px 24px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '800' }}>Job Feed</h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {filteredApps.length} Matches Found (Sorted by Score)
          </span>
        </div>
        
        <div style={{ display: 'flex', gap: '12px', flex: 1, justifyContent: 'flex-end', minWidth: '300px' }}>
          <div className="search-box" style={{ flex: 1, maxWidth: '300px', position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', opacity: 0.5 }} />
            <input 
              type="text" 
              placeholder="Search title, company, experience..." 
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{ width: '100%', padding: '10px 12px 10px 36px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '8px', color: 'white' }}
            />
          </div>

          <button 
            className="new-btn" 
            style={{ width: 'auto', padding: '10px 20px', fontSize: '0.9rem' }} 
            onClick={onDiscover} 
            disabled={isDiscovering}
          >
            <Sparkles size={18} className={isDiscovering ? 'spin' : ''} />
            {isDiscovering ? 'Discovering...' : 'Discover New Jobs'}
          </button>
        </div>
      </div>

      {sessions.length === 0 ? (
        <div className="loader-container">
          <div style={{ opacity: 0.5, textAlign: 'center' }}>
            <Sparkles size={48} style={{ marginBottom: 16 }} />
            <p>No jobs found.</p>
          </div>
        </div>
      ) : (
        <div className="feed-content" style={{ padding: '24px' }}>
          {sessions.map((session, sIdx) => (
            <div key={sIdx} className="discovery-session" style={{ marginBottom: '48px' }}>
              <div className="session-header" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px', opacity: 0.8 }}>
                <div style={{ height: '1px', flex: 1, background: 'linear-gradient(90deg, transparent, var(--border))' }} />
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', fontWeight: '600', color: 'var(--accent)' }}>
                  <Clock size={14} />
                  Search Session {session.time}
                </div>
                <div style={{ height: '1px', flex: 1, background: 'linear-gradient(90deg, var(--border), transparent)' }} />
              </div>
              
              <div className="feed-grid">
                {session.jobs.map(app => (
                  <JobCard 
                    key={app.id} 
                    application={app} 
                    onSave={onSave} 
                    onDismiss={onDismiss} 
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
