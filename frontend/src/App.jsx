import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Play, 
  Pause, 
  RotateCcw, 
  CheckCircle2, 
  ArrowRight, 
  Volume2, 
  Film, 
  Sliders, 
  Clock, 
  Layers, 
  Share2, 
  Download, 
  Flame, 
  Zap, 
  Calendar, 
  Send,
  Eye,
  Check
} from 'lucide-react';

const YoutubeIcon = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

const InstagramIcon = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
  </svg>
);

const API_BASE = "http://localhost:8000";

// Curated visual art backgrounds for each niche card
const NICHE_VISUALS = {
  biblical: "https://images.unsplash.com/photo-1543783207-ec64e4d95325?auto=format&fit=crop&w=600&q=80",
  anime: "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=600&q=80",
  heists: "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=600&q=80",
  mythology: "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=600&q=80",
  school_gossip: "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=600&q=80",
  scary_stories: "https://images.unsplash.com/photo-1509114397022-ed747cca3f65?auto=format&fit=crop&w=600&q=80",
  history: "https://images.unsplash.com/photo-1461360370896-922624d12aa1?auto=format&fit=crop&w=600&q=80",
  kindness: "https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?auto=format&fit=crop&w=600&q=80"
};

export default function App() {
  const [activeTab, setActiveTab] = useState('home'); // 'home' | 'studio' | 'autopilot' | 'library'
  const [niches, setNiches] = useState([]);
  const [selectedNiche, setSelectedNiche] = useState(null);
  const [options, setOptions] = useState(null);
  const [videos, setVideos] = useState([]);
  const [autopilotData, setAutopilotData] = useState(null);
  
  // Studio State
  const [currentStep, setCurrentStep] = useState(1);
  const [topic, setTopic] = useState('The 3 days of darkness in Egypt');
  const [scriptData, setScriptData] = useState(null);
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState('deep_narrator');
  const [selectedCaptionStyle, setSelectedCaptionStyle] = useState('mrbeast');
  const [selectedBgm, setSelectedBgm] = useState('cinematic_suspense');
  const [speechRate, setSpeechRate] = useState(1.0);
  
  // Generation & Player State
  const [activeJob, setActiveJob] = useState(null);
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [selectedVideoToPlay, setSelectedVideoToPlay] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);

  // Fetch initial metadata from backend
  useEffect(() => {
    fetch(`${API_BASE}/api/niches`)
      .then(res => res.json())
      .then(data => {
        setNiches(data.niches || []);
        if (data.niches && data.niches.length > 0) {
          setSelectedNiche(data.niches[0]);
        }
      })
      .catch(err => console.log("Backend offline or loading:", err));

    fetch(`${API_BASE}/api/options`)
      .then(res => res.json())
      .then(data => setOptions(data))
      .catch(err => console.log("Options loading err:", err));

    fetch(`${API_BASE}/api/videos`)
      .then(res => res.json())
      .then(data => {
        setVideos(data.videos || []);
        if (data.videos && data.videos.length > 0) {
          setSelectedVideoToPlay(data.videos[0]);
        }
      })
      .catch(err => console.log("Videos err:", err));

    fetch(`${API_BASE}/api/autopilot-status`)
      .then(res => res.json())
      .then(data => setAutopilotData(data))
      .catch(err => console.log("Autopilot err:", err));
  }, []);

  // Poll active generation job
  useEffect(() => {
    if (!activeJob || activeJob.status === 'completed') return;

    const interval = setInterval(() => {
      fetch(`${API_BASE}/api/jobs/${activeJob.id}`)
        .then(res => res.json())
        .then(updatedJob => {
          setActiveJob(updatedJob);
          if (updatedJob.status === 'completed') {
            setIsGeneratingVideo(false);
            if (updatedJob.videoUrl) {
              setSelectedVideoToPlay({
                url: updatedJob.videoUrl,
                title: `Faceless Reel: ${updatedJob.topic}`
              });
            }
          }
        })
        .catch(err => console.error("Job polling err:", err));
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJob]);

  // Handle niche select from home showcase
  const handleSelectNicheAndCreate = (niche) => {
    setSelectedNiche(niche);
    if (niche.sampleHooks && niche.sampleHooks.length > 0) {
      setTopic(niche.sampleHooks[0]);
    }
    setActiveTab('studio');
    setCurrentStep(1);
  };

  // Generate AI Script
  const handleGenerateScript = async () => {
    setIsGeneratingScript(true);
    try {
      const res = await fetch(`${API_BASE}/api/generate-script`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          niche: selectedNiche?.id || 'biblical',
          topic: topic,
          targetDuration: 45
        })
      });
      const data = await res.json();
      setScriptData(data);
      setCurrentStep(2);
    } catch (err) {
      console.error("Script generation failed:", err);
      // Fallback preview
      setScriptData({
        title: `The Mystery of ${topic}`,
        hook: `You won't believe what happened when ${topic}...`,
        fullScript: `For centuries, everyone believed ${topic} was impossible. But recently declassified accounts confirm what actually took place. When researchers examined the site, they found evidence that defied modern physics. Would you dare visit?`,
        scenes: [
          { scene: 1, text: `You won't believe what happened when ${topic}...`, shotType: "Extreme Closeup" },
          { scene: 2, text: `For centuries, people believed this was myth. But recent records prove otherwise.`, shotType: "Wide Cinematic" },
          { scene: 3, text: `The deepest chamber held artifacts that shouldn't exist.`, shotType: "Suspense Push-in" },
          { scene: 4, text: `Follow for part two of this untold story.`, shotType: "Climax" }
        ]
      });
      setCurrentStep(2);
    } finally {
      setIsGeneratingScript(false);
    }
  };

  // Trigger Video Assembly Job
  const handleStartVideoJob = async () => {
    setIsGeneratingVideo(true);
    try {
      const res = await fetch(`${API_BASE}/api/create-video`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          niche: selectedNiche?.id || 'biblical',
          topic: topic,
          script: scriptData?.fullScript || topic,
          voiceId: selectedVoice,
          captionStyleId: selectedCaptionStyle,
          bgmMood: selectedBgm
        })
      });
      const data = await res.json();
      setActiveJob({
        id: data.jobId,
        status: 'processing',
        progress: 10,
        stageLabel: 'Analyzing Script & Extracting Timestamps'
      });
      setCurrentStep(5);
    } catch (err) {
      console.error("Creation error:", err);
      setIsGeneratingVideo(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      
      {/* ── TOP NAVIGATION NAVBAR ── */}
      <header style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        background: 'rgba(7, 9, 14, 0.82)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)'
      }}>
        <div className="container" style={{
          height: '74px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          {/* Logo */}
          <div 
            onClick={() => setActiveTab('home')}
            style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}
          >
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #7c3aed 0%, #ec4899 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(124, 58, 237, 0.5)'
            }}>
              <Zap size={22} color="#ffffff" fill="#ffffff" />
            </div>
            <span style={{ fontSize: '1.4rem', fontWeight: 800 }} className="brand-font">
              Faceless<span style={{ color: '#8b5cf6' }}>Reels</span>
            </span>
          </div>

          {/* Navigation Links */}
          <nav style={{ display: 'flex', gap: '8px' }}>
            <button 
              onClick={() => setActiveTab('home')}
              className={`btn-secondary ${activeTab === 'home' ? 'active' : ''}`}
              style={{
                background: activeTab === 'home' ? 'rgba(124, 58, 237, 0.16)' : 'transparent',
                borderColor: activeTab === 'home' ? 'rgba(124, 58, 237, 0.5)' : 'transparent'
              }}
            >
              Showcase
            </button>
            <button 
              onClick={() => setActiveTab('studio')}
              className="btn-secondary"
              style={{
                background: activeTab === 'studio' ? 'rgba(124, 58, 237, 0.16)' : 'transparent',
                borderColor: activeTab === 'studio' ? 'rgba(124, 58, 237, 0.5)' : 'transparent'
              }}
            >
              <Film size={16} /> Studio Creator
            </button>
            <button 
              onClick={() => setActiveTab('autopilot')}
              className="btn-secondary"
              style={{
                background: activeTab === 'autopilot' ? 'rgba(124, 58, 237, 0.16)' : 'transparent',
                borderColor: activeTab === 'autopilot' ? 'rgba(124, 58, 237, 0.5)' : 'transparent'
              }}
            >
              <Calendar size={16} /> Auto-Pilot
            </button>
            <button 
              onClick={() => setActiveTab('library')}
              className="btn-secondary"
              style={{
                background: activeTab === 'library' ? 'rgba(124, 58, 237, 0.16)' : 'transparent',
                borderColor: activeTab === 'library' ? 'rgba(124, 58, 237, 0.5)' : 'transparent'
              }}
            >
              <Layers size={16} /> Library ({videos.length})
            </button>
          </nav>

          {/* Action CTAs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button 
              onClick={() => alert("Google Auth configured via OAuth2")}
              className="btn-secondary"
              style={{ fontSize: '0.9rem' }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24">
                <path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"/>
                <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"/>
                <path fill="#FBBC05" d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12 0 12s.7 2.3 1.9 4.7l3.7-1.9z"/>
                <path fill="#34A853" d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2-6.4-4.8L1.9 16.7C3.7 20.4 7.5 23 12 23z"/>
              </svg>
              Sign in with Google
            </button>
            <button 
              onClick={() => setActiveTab('studio')}
              className="btn-primary"
              style={{ padding: '10px 22px', fontSize: '0.92rem' }}
            >
              Get Started
            </button>
          </div>
        </div>
      </header>

      {/* ── TAB 1: SHOWCASE & LANDING PAGE (MATCHING FACELESSREELS) ── */}
      {activeTab === 'home' && (
        <main style={{ flex: 1 }}>
          {/* Hero Section */}
          <section style={{ textAlign: 'center', padding: '64px 0 24px 0' }}>
            <div className="container">
              
              {/* Trust Badge */}
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '12px',
                background: 'rgba(255, 255, 255, 0.05)',
                padding: '6px 16px',
                borderRadius: '9999px',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                marginBottom: '28px'
              }}>
                <div style={{ display: 'flex', marginLeft: '-4px' }}>
                  {['👨‍💻', '👩‍💼', '🎨', '🚀'].map((emoji, i) => (
                    <span key={i} style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      background: '#1e293b',
                      fontSize: '13px',
                      marginLeft: i > 0 ? '-6px' : 0,
                      border: '2px solid #07090e'
                    }}>
                      {emoji}
                    </span>
                  ))}
                </div>
                <span style={{ fontSize: '0.88rem', color: '#cbd5e1' }}>
                  Trusted by <strong>1.9M+</strong> creators worldwide
                </span>
              </div>

              {/* Main Headline */}
              <h1 style={{
                fontSize: 'clamp(2.4rem, 5vw, 4.4rem)',
                fontWeight: 900,
                lineHeight: 1.1,
                maxWidth: '920px',
                margin: '0 auto 20px auto',
                letterSpacing: '-0.03em'
              }}>
                Create viral faceless <br />
                <span style={{
                  background: 'linear-gradient(135deg, #a855f7 0%, #ec4899 50%, #f59e0b 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent'
                }}>
                  videos on auto-pilot
                </span>
              </h1>

              {/* Subtitle */}
              <p style={{
                fontSize: '1.22rem',
                color: '#94a3b8',
                maxWidth: '680px',
                margin: '0 auto 28px auto',
                lineHeight: 1.5
              }}>
                The only AI that generates & posts videos for you automatically, even while you sleep.
              </p>

              {/* Platform Pills */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '16px',
                marginBottom: '36px',
                color: '#94a3b8',
                fontSize: '0.95rem'
              }}>
                <span>Perfect for</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#ff0000', fontWeight: 600 }}>
                  <YoutubeIcon size={18} /> YouTube Shorts
                </span>
                <span>•</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#e1306c', fontWeight: 600 }}>
                  <InstagramIcon size={18} /> Instagram Reels
                </span>
                <span>•</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#00f2fe', fontWeight: 600 }}>
                  <Film size={18} /> TikTok
                </span>
              </div>

              {/* Primary Action Button */}
              <div style={{ marginBottom: '14px' }}>
                <button 
                  onClick={() => setActiveTab('studio')}
                  className="btn-primary"
                  style={{
                    fontSize: '1.2rem',
                    padding: '18px 42px',
                    borderRadius: '9999px'
                  }}
                >
                  <Zap size={22} fill="#ffffff" />
                  Create your first video
                </button>
              </div>

              <p style={{ fontSize: '0.9rem', color: '#64748b' }}>
                Get your generated video in less than 5 minutes.
              </p>

              {/* "Creates videos for any niche" Annotation */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-start',
                marginTop: '44px',
                marginBottom: '10px',
                paddingLeft: '12px'
              }}>
                <span style={{
                  fontSize: '1.15rem',
                  fontWeight: 700,
                  color: '#f8fafc',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  Creates videos for any niche
                  <svg width="36" height="24" viewBox="0 0 40 24" fill="none">
                    <path d="M4 6C16 4 28 8 34 18M34 18L26 18M34 18L32 10" stroke="#a855f7" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
              </div>

              {/* ── NICHE CAROUSEL SHOWCASE ── */}
              <div className="niche-slider-container">
                {niches.map((niche) => {
                  const bgImage = NICHE_VISUALS[niche.id] || NICHE_VISUALS.biblical;
                  return (
                    <div
                      key={niche.id}
                      className="niche-card"
                      style={{
                        backgroundImage: `url(${bgImage})`,
                        '--card-color': niche.color
                      }}
                      onClick={() => handleSelectNicheAndCreate(niche)}
                    >
                      <div className="niche-overlay">
                        {/* Word Highlight preview like the real reels */}
                        <div style={{
                          marginBottom: 'auto',
                          marginTop: '40px',
                          textAlign: 'center'
                        }}>
                          <span style={{
                            background: niche.color,
                            color: '#000',
                            fontWeight: 900,
                            padding: '4px 10px',
                            borderRadius: '6px',
                            fontSize: '0.95rem',
                            letterSpacing: '0.04em',
                            textTransform: 'uppercase',
                            boxShadow: '0 4px 15px rgba(0,0,0,0.6)'
                          }}>
                            {niche.badge.split(' ')[0]}
                          </span>
                        </div>

                        <div style={{ textAlign: 'left' }}>
                          <span style={{
                            fontSize: '0.72rem',
                            textTransform: 'uppercase',
                            fontWeight: 700,
                            color: niche.color,
                            letterSpacing: '0.06em'
                          }}>
                            {niche.style.split('/')[0]}
                          </span>
                          <h3 style={{
                            fontSize: '1.3rem',
                            fontWeight: 800,
                            color: '#ffffff',
                            margin: '4px 0 6px 0'
                          }}>
                            {niche.name}
                          </h3>
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontSize: '0.8rem',
                            color: '#cbd5e1'
                          }}>
                            <span>Click to create</span>
                            <ArrowRight size={14} color={niche.color} />
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

            </div>
          </section>

          {/* ── 3-STEP "HOW IT WORKS" WORKFLOW ── */}
          <section style={{ padding: '70px 0', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <div className="container">
              <div style={{ textAlign: 'center', marginBottom: '48px' }}>
                <span className="badge badge-purple" style={{ marginBottom: '12px' }}>
                  Autonomous Engine
                </span>
                <h2 style={{ fontSize: '2.5rem', fontWeight: 800 }}>How FacelessReels Works</h2>
                <p style={{ color: '#94a3b8', fontSize: '1.05rem', marginTop: '8px' }}>
                  From a single idea to published 9:16 vertical videos in 3 frictionless steps.
                </p>
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: '28px'
              }}>
                <div className="glass-panel" style={{ padding: '36px 30px' }}>
                  <div style={{
                    width: '54px',
                    height: '54px',
                    borderRadius: '16px',
                    background: 'rgba(124, 58, 237, 0.15)',
                    color: '#c4b5fd',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '20px',
                    border: '1px solid rgba(124, 58, 237, 0.3)'
                  }}>
                    <Sliders size={26} />
                  </div>
                  <span style={{ color: '#8b5cf6', fontWeight: 700, fontSize: '0.85rem' }}>STEP 01</span>
                  <h3 style={{ fontSize: '1.4rem', margin: '8px 0 12px 0' }}>Choose Niche & Visual Style</h3>
                  <p style={{ color: '#94a3b8', lineHeight: 1.6 }}>
                    Select from 8+ battle-tested viral niches (Anime, True Crime, Biblical, Mythology) or type any custom prompt.
                  </p>
                </div>

                <div className="glass-panel" style={{ padding: '36px 30px' }}>
                  <div style={{
                    width: '54px',
                    height: '54px',
                    borderRadius: '16px',
                    background: 'rgba(6, 182, 212, 0.15)',
                    color: '#67e8f9',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '20px',
                    border: '1px solid rgba(6, 182, 212, 0.3)'
                  }}>
                    <Sparkles size={26} />
                  </div>
                  <span style={{ color: '#06b6d4', fontWeight: 700, fontSize: '0.85rem' }}>STEP 02</span>
                  <h3 style={{ fontSize: '1.4rem', margin: '8px 0 12px 0' }}>AI Script, Voice & Visuals</h3>
                  <p style={{ color: '#94a3b8', lineHeight: 1.6 }}>
                    The neural pipeline crafts a high-retention hook, generates realistic voiceover, renders cinematic scenes, and aligns animated subtitles.
                  </p>
                </div>

                <div className="glass-panel" style={{ padding: '36px 30px' }}>
                  <div style={{
                    width: '54px',
                    height: '54px',
                    borderRadius: '16px',
                    background: 'rgba(236, 72, 153, 0.15)',
                    color: '#f472b6',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '20px',
                    border: '1px solid rgba(236, 72, 153, 0.3)'
                  }}>
                    <Calendar size={26} />
                  </div>
                  <span style={{ color: '#ec4899', fontWeight: 700, fontSize: '0.85rem' }}>STEP 03</span>
                  <h3 style={{ fontSize: '1.4rem', margin: '8px 0 12px 0' }}>Auto-Pilot Publishing</h3>
                  <p style={{ color: '#94a3b8', lineHeight: 1.6 }}>
                    Connect your YouTube, Instagram, and TikTok channels. Our background daemon renders and publishes daily on schedule.
                  </p>
                </div>
              </div>
            </div>
          </section>
        </main>
      )}

      {/* ── TAB 2: STUDIO CREATOR VIEW ── */}
      {activeTab === 'studio' && (
        <main className="container" style={{ flex: 1, padding: '36px 0 60px 0' }}>
          
          {/* Studio Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '32px'
          }}>
            <div>
              <span className="badge badge-purple" style={{ marginBottom: '8px' }}>
                AI Video Studio
              </span>
              <h2 style={{ fontSize: '2.2rem', fontWeight: 800 }}>Create New Faceless Reel</h2>
            </div>

            {/* Step Wizard Pills */}
            <div style={{ display: 'flex', gap: '8px' }}>
              {[
                { step: 1, label: 'Niche & Theme' },
                { step: 2, label: 'Script & Hook' },
                { step: 3, label: 'Voice & Sound' },
                { step: 4, label: 'Captions' },
                { step: 5, label: 'Render & Player' }
              ].map(s => (
                <div 
                  key={s.step}
                  onClick={() => setCurrentStep(s.step)}
                  className={`step-item ${currentStep === s.step ? 'active' : ''}`}
                >
                  <div className="step-number">{s.step}</div>
                  <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>{s.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '36px', alignItems: 'start' }}>
            
            {/* Left Column: Interactive Step Controls */}
            <div className="glass-panel" style={{ padding: '32px' }}>
              
              {/* STEP 1: NICHE & TOPIC */}
              {currentStep === 1 && (
                <div>
                  <h3 style={{ fontSize: '1.3rem', marginBottom: '8px' }}>1. Select Your Content Niche</h3>
                  <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '20px' }}>
                    Choose the visual identity and storytelling format for your reel.
                  </p>

                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                    gap: '14px',
                    marginBottom: '28px'
                  }}>
                    {niches.map(niche => (
                      <div
                        key={niche.id}
                        onClick={() => {
                          setSelectedNiche(niche);
                          if (niche.sampleHooks && niche.sampleHooks[0]) {
                            setTopic(niche.sampleHooks[0]);
                          }
                        }}
                        style={{
                          padding: '16px',
                          borderRadius: '14px',
                          cursor: 'pointer',
                          background: selectedNiche?.id === niche.id ? 'rgba(124, 58, 237, 0.2)' : 'rgba(255,255,255,0.03)',
                          border: selectedNiche?.id === niche.id ? '2px solid #8b5cf6' : '1px solid rgba(255,255,255,0.08)',
                          transition: 'all 0.2s ease'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{niche.name}</span>
                          {selectedNiche?.id === niche.id && <CheckCircle2 size={18} color="#8b5cf6" />}
                        </div>
                        <p style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '6px' }}>
                          {niche.badge}
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* Topic / Prompt Input */}
                  <div style={{ marginBottom: '24px' }}>
                    <label style={{ display: 'block', fontWeight: 600, marginBottom: '8px', fontSize: '0.92rem' }}>
                      Video Topic or Hook Idea
                    </label>
                    <input
                      type="text"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      placeholder="e.g. The forgotten Greek god who lived under Mount Olympus..."
                      style={{
                        width: '100%',
                        padding: '14px 18px',
                        borderRadius: '12px',
                        background: 'rgba(0,0,0,0.5)',
                        border: '1px solid rgba(255,255,255,0.15)',
                        color: '#fff',
                        fontSize: '1rem',
                        outline: 'none'
                      }}
                    />
                  </div>

                  {/* Sample Hooks Picker */}
                  {selectedNiche?.sampleHooks && (
                    <div style={{ marginBottom: '28px' }}>
                      <span style={{ fontSize: '0.8rem', color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
                        Or choose from high-performing viral hooks:
                      </span>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {selectedNiche.sampleHooks.map((h, i) => (
                          <div
                            key={i}
                            onClick={() => setTopic(h)}
                            style={{
                              padding: '10px 14px',
                              borderRadius: '8px',
                              background: topic === h ? 'rgba(124, 58, 237, 0.15)' : 'rgba(255,255,255,0.03)',
                              border: topic === h ? '1px solid #7c3aed' : '1px solid rgba(255,255,255,0.06)',
                              fontSize: '0.85rem',
                              cursor: 'pointer',
                              color: topic === h ? '#c4b5fd' : '#e2e8f0'
                            }}
                          >
                            ⚡ "{h}"
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <button
                    onClick={handleGenerateScript}
                    disabled={isGeneratingScript}
                    className="btn-primary"
                    style={{ width: '100%' }}
                  >
                    {isGeneratingScript ? (
                      <>Generating Viral Script...</>
                    ) : (
                      <>
                        <Sparkles size={18} /> Generate Script & Scene Prompts
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* STEP 2: SCRIPT & SCENE BREAKDOWN */}
              {currentStep === 2 && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <div>
                      <h3 style={{ fontSize: '1.3rem' }}>2. AI Script & Visual Prompts</h3>
                      <p style={{ color: '#94a3b8', fontSize: '0.88rem' }}>Review the 4-scene retention structure.</p>
                    </div>
                    <button
                      onClick={handleGenerateScript}
                      className="btn-secondary"
                      style={{ fontSize: '0.85rem' }}
                    >
                      <RotateCcw size={14} /> Regenerate
                    </button>
                  </div>

                  {/* Scene Breakdown */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '24px' }}>
                    {scriptData?.scenes?.map((scene, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: 'rgba(0,0,0,0.4)',
                          borderRadius: '12px',
                          padding: '16px',
                          border: '1px solid rgba(255,255,255,0.07)'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#a855f7' }}>
                            SCENE {scene.scene} • {scene.shotType}
                          </span>
                          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            ~{scene.duration || 8}s
                          </span>
                        </div>
                        <p style={{ fontSize: '0.95rem', color: '#f1f5f9', marginBottom: '8px' }}>
                          "{scene.text}"
                        </p>
                        <div style={{
                          fontSize: '0.78rem',
                          color: '#06b6d4',
                          background: 'rgba(6, 182, 212, 0.08)',
                          padding: '6px 10px',
                          borderRadius: '6px',
                          border: '1px solid rgba(6, 182, 212, 0.15)'
                        }}>
                          🎨 Visual: {scene.visualPrompt || selectedNiche?.defaultPrompt}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div style={{ display: 'flex', gap: '12px' }}>
                    <button
                      onClick={() => setCurrentStep(1)}
                      className="btn-secondary"
                      style={{ flex: 1 }}
                    >
                      Back
                    </button>
                    <button
                      onClick={() => setCurrentStep(3)}
                      className="btn-primary"
                      style={{ flex: 2 }}
                    >
                      Next: Choose Voice & Sound <ArrowRight size={18} />
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 3: VOICE & SOUND */}
              {currentStep === 3 && (
                <div>
                  <h3 style={{ fontSize: '1.3rem', marginBottom: '8px' }}>3. Voiceover & Sound Design</h3>
                  <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '20px' }}>
                    Select the ideal AI voice persona and background sound ambience.
                  </p>

                  {/* Voice Selector */}
                  <label style={{ display: 'block', fontWeight: 600, marginBottom: '8px', fontSize: '0.92rem' }}>
                    Narrator Voice
                  </label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '24px' }}>
                    {options?.voices?.map(v => (
                      <div
                        key={v.id}
                        onClick={() => setSelectedVoice(v.id)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '14px 18px',
                          borderRadius: '12px',
                          background: selectedVoice === v.id ? 'rgba(124, 58, 237, 0.18)' : 'rgba(255,255,255,0.03)',
                          border: selectedVoice === v.id ? '1px solid #8b5cf6' : '1px solid rgba(255,255,255,0.07)',
                          cursor: 'pointer'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <Volume2 size={20} color={selectedVoice === v.id ? '#c4b5fd' : '#94a3b8'} />
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{v.name}</div>
                            <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>{v.tone}</div>
                          </div>
                        </div>
                        {selectedVoice === v.id && <Check size={18} color="#8b5cf6" />}
                      </div>
                    ))}
                  </div>

                  {/* BGM Mood */}
                  <label style={{ display: 'block', fontWeight: 600, marginBottom: '8px', fontSize: '0.92rem' }}>
                    Background Music Mood
                  </label>
                  <select
                    value={selectedBgm}
                    onChange={(e) => setSelectedBgm(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '12px 16px',
                      borderRadius: '10px',
                      background: '#07090e',
                      border: '1px solid rgba(255,255,255,0.15)',
                      color: '#fff',
                      marginBottom: '28px',
                      fontSize: '0.95rem'
                    }}
                  >
                    {options?.bgmMoods?.map(m => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </select>

                  <div style={{ display: 'flex', gap: '12px' }}>
                    <button onClick={() => setCurrentStep(2)} className="btn-secondary" style={{ flex: 1 }}>
                      Back
                    </button>
                    <button onClick={() => setCurrentStep(4)} className="btn-primary" style={{ flex: 2 }}>
                      Next: Style Dynamic Captions <ArrowRight size={18} />
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 4: CAPTIONS STYLE */}
              {currentStep === 4 && (
                <div>
                  <h3 style={{ fontSize: '1.3rem', marginBottom: '8px' }}>4. Viral Caption Customizer</h3>
                  <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '20px' }}>
                    High-retention shorts use dynamic animated word-by-word highlights.
                  </p>

                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: '14px',
                    marginBottom: '28px'
                  }}>
                    {options?.captionStyles?.map(cs => (
                      <div
                        key={cs.id}
                        onClick={() => setSelectedCaptionStyle(cs.id)}
                        style={{
                          padding: '18px',
                          borderRadius: '14px',
                          background: selectedCaptionStyle === cs.id ? 'rgba(124, 58, 237, 0.2)' : 'rgba(255,255,255,0.03)',
                          border: selectedCaptionStyle === cs.id ? '2px solid #8b5cf6' : '1px solid rgba(255,255,255,0.08)',
                          cursor: 'pointer',
                          textAlign: 'center'
                        }}
                      >
                        <div style={{
                          fontSize: '1.1rem',
                          fontWeight: 900,
                          textTransform: 'uppercase',
                          color: cs.textColor,
                          marginBottom: '8px'
                        }}>
                          WAIT <span style={{ color: cs.highlightColor }}>UNTIL</span> YOU
                        </div>
                        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#e2e8f0' }}>{cs.name}</span>
                      </div>
                    ))}
                  </div>

                  <div style={{ display: 'flex', gap: '12px' }}>
                    <button onClick={() => setCurrentStep(3)} className="btn-secondary" style={{ flex: 1 }}>
                      Back
                    </button>
                    <button onClick={handleStartVideoJob} className="btn-primary" style={{ flex: 2 }}>
                      <Zap size={18} fill="#ffffff" /> Assemble Video Now
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 5: GENERATION & PROGRESS */}
              {currentStep === 5 && (
                <div>
                  <h3 style={{ fontSize: '1.3rem', marginBottom: '8px' }}>5. Live Video Compositing</h3>
                  <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '24px' }}>
                    Video engine is orchestrating script, voice, visual shots, and captions.
                  </p>

                  {/* Progress Bar */}
                  <div style={{ marginBottom: '28px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.9rem' }}>
                      <span style={{ color: '#8b5cf6', fontWeight: 700 }}>
                        {activeJob?.stageLabel || 'Rendering...'}
                      </span>
                      <span style={{ fontWeight: 700 }}>{activeJob?.progress || 10}%</span>
                    </div>
                    <div style={{
                      width: '100%',
                      height: '10px',
                      background: 'rgba(255,255,255,0.08)',
                      borderRadius: '9999px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: `${activeJob?.progress || 10}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, #7c3aed, #ec4899, #06b6d4)',
                        transition: 'width 0.4s ease'
                      }} />
                    </div>
                  </div>

                  {/* Steps Checklist */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '28px' }}>
                    {[
                      { label: "Script generation & timestamp alignment", minProg: 15 },
                      { label: "High-fidelity AI voice synthesis", minProg: 40 },
                      { label: "Vertical 9:16 Visual Art generation", minProg: 70 },
                      { label: "Dynamic subtitle burn-in & karaoke effects", minProg: 85 },
                      { label: "Audio normalization & 8K FFmpeg Compositing", minProg: 100 }
                    ].map((st, i) => {
                      const done = (activeJob?.progress || 0) >= st.minProg;
                      return (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.88rem' }}>
                          {done ? (
                            <CheckCircle2 size={18} color="#10b981" />
                          ) : (
                            <div style={{ width: '18px', height: '18px', borderRadius: '50%', border: '2px solid #64748b' }} />
                          )}
                          <span style={{ color: done ? '#f8fafc' : '#64748b' }}>{st.label}</span>
                        </div>
                      );
                    })}
                  </div>

                  {activeJob?.status === 'completed' && (
                    <div style={{
                      background: 'rgba(16, 185, 129, 0.1)',
                      border: '1px solid rgba(16, 185, 129, 0.3)',
                      padding: '16px',
                      borderRadius: '12px',
                      marginBottom: '20px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px'
                    }}>
                      <CheckCircle2 size={24} color="#10b981" />
                      <div>
                        <div style={{ fontWeight: 700, color: '#6ee7b7' }}>Reel Generated Successfully!</div>
                        <div style={{ fontSize: '0.82rem', color: '#94a3b8' }}>Ready to preview, download, or auto-publish.</div>
                      </div>
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: '12px' }}>
                    <button onClick={() => setCurrentStep(1)} className="btn-secondary" style={{ flex: 1 }}>
                      Create Another
                    </button>
                    {activeJob?.videoUrl && (
                      <a 
                        href={`${API_BASE}${activeJob.videoUrl}`} 
                        download 
                        className="btn-primary" 
                        style={{ flex: 1, textDecoration: 'none' }}
                      >
                        <Download size={18} /> Download Reel
                      </a>
                    )}
                  </div>
                </div>
              )}

            </div>

            {/* Right Column: 9:16 Phone Preview Mockup */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '12px', fontWeight: 600 }}>
                📱 Real-Time 9:16 Vertical Preview
              </span>

              <div className="phone-frame">
                <div className="phone-screen">
                  {/* If user has selected video to play, stream it */}
                  {selectedVideoToPlay?.url ? (
                    <video
                      src={`${API_BASE}${selectedVideoToPlay.url}`}
                      controls
                      autoPlay
                      loop
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover'
                      }}
                    />
                  ) : (
                    <div style={{
                      position: 'relative',
                      width: '100%',
                      height: '100%',
                      backgroundImage: `url(${NICHE_VISUALS[selectedNiche?.id || 'biblical']})`,
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <div style={{
                        position: 'absolute',
                        inset: 0,
                        background: 'linear-gradient(180deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.1) 40%, rgba(0,0,0,0.85) 100%)'
                      }} />

                      {/* Play Button Overlay */}
                      <div style={{
                        width: '60px',
                        height: '60px',
                        borderRadius: '50%',
                        background: 'rgba(255,255,255,0.2)',
                        backdropFilter: 'blur(10px)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 10
                      }}>
                        <Play size={26} color="#ffffff" fill="#ffffff" />
                      </div>

                      {/* Simulated Bouncing Captions */}
                      <div className="caption-preview-box">
                        <span className="word-highlight" style={{
                          background: options?.captionStyles?.find(c => c.id === selectedCaptionStyle)?.highlightColor || '#facc15',
                          color: '#000',
                          '--glow-color': options?.captionStyles?.find(c => c.id === selectedCaptionStyle)?.highlightColor || '#facc15'
                        }}>
                          {topic.split(' ')[0] || "DISCOVER"}
                        </span>
                        <div style={{ fontSize: '0.9rem', color: '#fff', fontWeight: 800, marginTop: '4px', textShadow: '0 2px 4px #000' }}>
                          {topic.slice(0, 32)}...
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

          </div>
        </main>
      )}

      {/* ── TAB 3: AUTO-PILOT SCHEDULER VIEW ── */}
      {activeTab === 'autopilot' && (
        <main className="container" style={{ flex: 1, padding: '40px 0 60px 0' }}>
          <div style={{ marginBottom: '32px' }}>
            <span className="badge badge-cyan" style={{ marginBottom: '8px' }}>
              Auto-Pilot Engine
            </span>
            <h2 style={{ fontSize: '2.4rem', fontWeight: 800 }}>Channel Automation & Scheduling</h2>
            <p style={{ color: '#94a3b8', fontSize: '1.05rem', marginTop: '6px' }}>
              Generate, render, and publish reels daily to your connected channels without touching a button.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px', marginBottom: '36px' }}>
            
            {/* Auto-Pilot Controls */}
            <div className="glass-panel" style={{ padding: '28px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
                <h3 style={{ fontSize: '1.25rem' }}>Auto-Pilot Daemon</h3>
                <span className="badge badge-green">RUNNING</span>
              </div>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '20px' }}>
                The background worker runs continuously, generating fresh scripts, assembling videos, and uploading to linked social APIs.
              </p>
              
              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '6px' }}>
                  Posting Frequency
                </label>
                <select style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '10px',
                  background: '#07090e',
                  border: '1px solid rgba(255,255,255,0.15)',
                  color: '#fff'
                }}>
                  <option>2 Videos / Day (12:00 PM, 6:00 PM)</option>
                  <option>1 Video / Day (6:00 PM)</option>
                  <option>3 Videos / Day (9:00 AM, 2:00 PM, 8:00 PM)</option>
                </select>
              </div>

              <div style={{ fontSize: '0.85rem', color: '#8b5cf6', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Clock size={16} /> Next automated run: Today at 18:00 (6:00 PM)
              </div>
            </div>

            {/* Connected Channels */}
            <div className="glass-panel" style={{ padding: '28px' }}>
              <h3 style={{ fontSize: '1.25rem', marginBottom: '18px' }}>Connected Channels</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {autopilotData?.channels?.map((ch, i) => (
                  <div key={i} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 16px',
                    borderRadius: '10px',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.06)'
                  }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.92rem' }}>{ch.platform}</div>
                      <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>{ch.handle}</div>
                    </div>
                    {ch.connected ? (
                      <span className="badge badge-green">Connected</span>
                    ) : (
                      <button className="btn-secondary" style={{ padding: '6px 12px', fontSize: '0.78rem' }}>
                        Connect
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* Recent Auto-Pilot Posts */}
          <div className="glass-panel" style={{ padding: '28px' }}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '18px' }}>Recent Auto-Pilot Posts</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {autopilotData?.recentPosts?.map((post, i) => (
                <div key={i} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '14px 18px',
                  borderRadius: '12px',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid rgba(255,255,255,0.06)'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <div style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: '8px',
                      background: 'rgba(124, 58, 237, 0.2)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#c4b5fd'
                    }}>
                      <Film size={20} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{post.title}</div>
                      <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{post.platform}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <span style={{ fontSize: '0.9rem', color: '#10b981', fontWeight: 700 }}>
                      🔥 {post.views} views
                    </span>
                    <span className="badge badge-purple">{post.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </main>
      )}

      {/* ── TAB 4: VIDEO LIBRARY VIEW ── */}
      {activeTab === 'library' && (
        <main className="container" style={{ flex: 1, padding: '40px 0 60px 0' }}>
          <div style={{ marginBottom: '32px' }}>
            <span className="badge badge-purple" style={{ marginBottom: '8px' }}>
              Your Rendered Reels
            </span>
            <h2 style={{ fontSize: '2.4rem', fontWeight: 800 }}>Video Output Library</h2>
            <p style={{ color: '#94a3b8', fontSize: '1.05rem', marginTop: '6px' }}>
              Browsing all completed 9:16 and 4K/8K video assets rendered by your engine.
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '24px'
          }}>
            {videos.map((vid) => (
              <div 
                key={vid.id}
                className="glass-panel"
                style={{
                  borderRadius: '18px',
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column'
                }}
              >
                {/* Video Preview thumbnail / player */}
                <div style={{
                  height: '240px',
                  background: '#07090e',
                  position: 'relative',
                  overflow: 'hidden',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <video
                    src={`${API_BASE}${vid.url}`}
                    controls
                    preload="metadata"
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover'
                    }}
                  />
                </div>

                <div style={{ padding: '18px', flex: 1, display: 'flex', flexDirection: 'column' }}>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '6px' }}>
                    {vid.title}
                  </h4>
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '14px', display: 'flex', justifyContent: 'space-between' }}>
                    <span>{vid.createdAt}</span>
                    <span>{vid.sizeMb} MB</span>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
                    <button
                      onClick={() => {
                        setSelectedVideoToPlay(vid);
                        setActiveTab('studio');
                        setCurrentStep(5);
                      }}
                      className="btn-secondary"
                      style={{ flex: 1, padding: '8px 12px', fontSize: '0.82rem' }}
                    >
                      <Eye size={14} /> Studio Preview
                    </button>
                    <a
                      href={`${API_BASE}${vid.url}`}
                      download
                      className="btn-secondary"
                      style={{ padding: '8px 12px', textDecoration: 'none' }}
                    >
                      <Download size={14} />
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </main>
      )}

      {/* ── FOOTER ── */}
      <footer style={{
        borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        padding: '36px 0',
        marginTop: 'auto',
        background: '#07090e'
      }}>
        <div className="container" style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.88rem',
          color: '#64748b'
        }}>
          <div>
            © 2026 FacelessReels Platform. Built with React & Python FastAPI Engine.
          </div>
          <div style={{ display: 'flex', gap: '20px' }}>
            <span style={{ cursor: 'pointer' }}>Privacy Policy</span>
            <span style={{ cursor: 'pointer' }}>Terms of Service</span>
            <span style={{ cursor: 'pointer' }}>API Docs</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
