import React, { useState, useEffect } from 'react';
import { submitJob, getJobStatus, getJobTranscription, approveJob, getJobResults, getOutroTemplates, abortJob, getJobsHistory } from '../services/api.ts';
import { SubtitleEditor } from './SubtitleEditor.tsx';

type AppState = 'IDLE' | 'UPLOADING' | 'EXTRACTING' | 'WAITING_FOR_REVIEW' | 'QUEUED' | 'GENERATING' | 'COMPLETED' | 'ERROR';

interface LangResult {
    lang_code: string;
    lang_name: string;
    download_url: string;
}

const API_HOST = `${window.location.protocol}//${window.location.hostname}:8080`;

const LANG_LABELS: Record<string, string> = {
    de: '🇩🇪 德语', es: '🇪🇸 西班牙语', fr: '🇫🇷 法语',
    id: '🇮🇩 印尼语', it: '🇮🇹 意大利语', pl: '🇵🇱 波兰语',
    pt: '🇵🇹 葡萄牙语', ru: '🇷🇺 俄语', tr: '🇹🇷 土耳其语',
};

const LANG_ORDER = ['de','es','fr','id','it','pl','pt','ru','tr'];

const STATUS_LABELS: Record<string, { text: string; color: string; icon: string }> = {
    waiting:         { text: '等待中',    color: '#64748b', icon: '⏳' },
    translating:     { text: '翻译中',    color: '#f59e0b', icon: '📝' },
    waiting_dubbing: { text: '等待配音',  color: '#94a3b8', icon: '🕒' },
    dubbing:         { text: '配音中',    color: '#8b5cf6', icon: '🎙️' },
    rendering:       { text: '渲染中',    color: '#3b82f6', icon: '🎬' },
    done:            { text: '已完成',    color: '#10b981', icon: '✅' },
};

const TEMPLATE_LABELS: Record<string, string> = {
    'transparent': '透明落版 (叠加)',
    'pixel': '像素落版 (替换)',
    'tavern': '酒馆落版 (替换)'
};

export const Dashboard: React.FC = () => {
    const [state, setState] = useState<AppState>('IDLE');
    const [jobId, setJobId] = useState<string | null>(null);
    const [transcription, setTranscription] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [results, setResults] = useState<LangResult[]>([]);
    const [fileName, setFileName] = useState<string>('');
    const [langProgress, setLangProgress] = useState<Record<string, string>>({});
    const [completedCount, setCompletedCount] = useState(0);
    const [totalCount, setTotalCount] = useState(9);
    
    // Outro Template state
    const [templates, setTemplates] = useState<string[]>([]);
    const [selectedTemplate, setSelectedTemplate] = useState<string>('');
    
    // History state
    const [history, setHistory] = useState<any[]>([]);
    const [showSidebar, setShowSidebar] = useState(true);

    // Initial load: check LocalStorage + Load History
    useEffect(() => {
        const init = async () => {
            // Load History
            try {
                const histRes = await getJobsHistory();
                setHistory(histRes.jobs || []);
            } catch (e) {
                console.error("加载历史记录失败:", e);
            }

            // Recovery from LocalStorage
            const lastJobId = localStorage.getItem('activeJobId');
            if (lastJobId && state === 'IDLE') {
                setJobId(lastJobId);
            }
        };
        init();
    }, []);

    // Update LocalStorage when jobId changes
    useEffect(() => {
        if (jobId) {
            localStorage.setItem('activeJobId', jobId);
        }
    }, [jobId]);

    // Load templates on mount
    useEffect(() => {
        const loadTemplates = async () => {
            try {
                const res = await getOutroTemplates();
                setTemplates(res.templates || []);
                if (res.templates && res.templates.length > 0) {
                    setSelectedTemplate(res.templates[0]);
                }
            } catch (e) {
                console.error("加载落版模板失败:", e);
            }
        };
        loadTemplates();
    }, []);

    // Polling logic
    useEffect(() => {
        let timer: any;
        if (jobId && state !== 'COMPLETED' && state !== 'ERROR' && state !== 'IDLE') {
            timer = setInterval(async () => {
                try {
                    const statusRes = await getJobStatus(jobId);
                    
                    if (statusRes.progress) {
                        setLangProgress(statusRes.progress);
                        setCompletedCount(statusRes.completed || 0);
                        setTotalCount(statusRes.total || 9);
                    }
                    
                    if (statusRes.status === 'WAITING_FOR_REVIEW' && state !== 'WAITING_FOR_REVIEW') {
                        const transRes = await getJobTranscription(jobId);
                        setTranscription(transRes);
                        setState('WAITING_FOR_REVIEW');
                    } else if (statusRes.status === 'QUEUED') {
                        setState('QUEUED');
                    } else if (statusRes.status === 'PROCESSING') {
                        // Task has started on worker
                        setState('EXTRACTING');
                    } else if (statusRes.status === 'GENERATING') {
                        setState('GENERATING');
                    } else if (statusRes.status === 'COMPLETED') {
                        const res = await getJobResults(jobId);
                        setResults(res.languages || []);
                        setState('COMPLETED');
                    } else if (statusRes.status === 'ABORTED') {
                        setState('IDLE');
                        setJobId(null);
                    }
                } catch (e) {
                    console.error("轮询出错:", e);
                }
            }, 1500);
        } else if (jobId && state === 'IDLE') {
            // Recovery check
            getJobStatus(jobId).then(statusRes => {
                if (statusRes.status === 'COMPLETED') {
                    getJobResults(jobId).then(res => {
                        setResults(res.languages || []);
                        setState('COMPLETED');
                    });
                } else if (statusRes.status === 'WAITING_FOR_REVIEW') {
                    getJobTranscription(jobId).then(transRes => {
                        setTranscription(transRes);
                        setState('WAITING_FOR_REVIEW');
                    });
                } else {
                    setState(statusRes.status as AppState);
                }
            }).catch(() => {
                localStorage.removeItem('activeJobId');
                setJobId(null);
            });
        }
        return () => clearInterval(timer);
    }, [state, jobId]);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setFileName(file.name);
        setState('UPLOADING');
        try {
            const res = await submitJob(file);
            setJobId(res.job_id);
            setState('EXTRACTING');
            
            // Refresh history
            const histRes = await getJobsHistory();
            setHistory(histRes.jobs || []);
        } catch (e: any) {
            const errorMsg = e.response?.data?.detail || e.message || "上传失败";
            setError(errorMsg);
            setState('ERROR');
        }
    };

    const handleApprove = async (validatedSubtitles: any[], outroStartTime: number | null, subtitleYPercent: number) => {
        if (!jobId) return;
        setState('GENERATING');
        try {
            // BACKWARDS ALIGNMENT MAPPING
            // pixel/tavern are REPLACE (is_overlay=false), transparent/others are OVERLAY (true)
            const isOverlay = !(selectedTemplate === 'pixel' || selectedTemplate === 'tavern');
            
            await approveJob(jobId, { 
                validated_subtitles: validatedSubtitles,
                outro_start_time: outroStartTime,
                outro_template_id: selectedTemplate || null,
                subtitle_y_percent: subtitleYPercent,
                is_overlay: isOverlay
            });
        } catch (e: any) {
            setError(e.message || "提交审核失败");
            setState('ERROR');
        }
    };

    const handleAbort = async (skipConfirm = false) => {
        if (!jobId) return;
        const msg = "⚠️ 确定要终止正在处理的任务并物理删除文件夹吗？此操作不可撤销。";
        if (skipConfirm || window.confirm(msg)) {
            try {
                await abortJob(jobId);
                resetToNewJob();
                // Refresh history
                try {
                    const histRes = await getJobsHistory();
                    setHistory(histRes.jobs || []);
                } catch (e) {
                    console.error("刷新历史记录失败:", e);
                }
            } catch (e) {
                alert("终止任务失败: " + e);
            }
        }
    };

    const resetToNewJob = () => {
        localStorage.removeItem('activeJobId');
        setJobId(null);
        setTranscription(null);
        setResults([]);
        setLangProgress({});
        setState('IDLE');
        setFileName('');
        setError(null);
    };

    const loadJob = (id: string) => {
        setJobId(id);
        setTranscription(null);
        setResults([]);
        setLangProgress({});
        setState('IDLE'); 
        localStorage.setItem('activeJobId', id);
    };

    return (
        <div style={{ ...styles.container, display: 'flex', minHeight: '100vh', width: '100vw', padding: 0, alignItems: 'stretch' }}>
            {/* Sidebar */}
            {showSidebar && (
                <div style={{
                    width: '320px',
                    backgroundColor: '#0f172a',
                    borderRight: '1px solid #1e293b',
                    display: 'flex',
                    flexDirection: 'column',
                    padding: '1.5rem 1rem',
                    flexShrink: 0
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                        <h2 style={{ fontSize: '1.1rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            🕒 历史任务
                        </h2>
                    </div>

                    <button 
                        onClick={resetToNewJob}
                        style={{
                            width: '100%',
                            padding: '0.8rem',
                            backgroundColor: '#3b82f6',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.6rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            marginBottom: '1.5rem',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.5rem',
                            boxShadow: '0 4px 12px rgba(59,130,246,0.3)'
                        }}
                    >
                        ➕ 新建任务
                    </button>

                    <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {history.length > 0 ? history.map(h => (
                            <div 
                                key={h.job_id} 
                                onClick={() => loadJob(h.job_id)}
                                style={{
                                    padding: '0.75rem',
                                    borderRadius: '0.5rem',
                                    backgroundColor: jobId === h.job_id ? '#1e293b' : 'transparent',
                                    border: '1px solid',
                                    borderColor: jobId === h.job_id ? '#3b82f6' : '#334155',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s'
                                }}
                            >
                                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {h.display_name || h.filename}
                                </div>
                                <div style={{ fontSize: '0.7rem', color: h.status === 'COMPLETED' ? '#10b981' : '#94a3b8', marginTop: '0.3rem', display: 'flex', justifyContent: 'space-between' }}>
                                    <span>{h.status}</span>
                                    <span>{new Date(h.created_at * 1000).toLocaleDateString()}</span>
                                </div>
                            </div>
                        )) : (
                            <div style={{ color: '#475569', fontSize: '0.85rem', textAlign: 'center', marginTop: '2rem' }}>
                                暂无历史记录
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Main Content Area */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', overflowY: 'auto', padding: '2rem 1rem' }}>
                <header style={{ ...styles.header, maxWidth: '1200px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1.5rem', marginBottom: '1.5rem' }}>
                         <button 
                            onClick={() => setShowSidebar(!showSidebar)}
                            style={{ backgroundColor: 'transparent', border: '1px solid #334155', color: '#94a3b8', padding: '0.5rem 1rem', borderRadius: '0.5rem', cursor: 'pointer', fontSize: '0.85rem', whiteSpace: 'nowrap' }}
                         >
                            {showSidebar ? '◀ 收起侧栏' : '▶ 任务历史'}
                         </button>
                         <h1 style={{ ...styles.title, margin: 0 }}>视频本地化工具</h1>
                    </div>
                    <p style={styles.subtitle}>上传一个无字幕的英文视频，AI 自动生成 9 种语言的配音版本</p>
                </header>

                {/* Step indicator */}
                <div style={styles.steps}>
                    <Step num={1} label="上传视频" active={state === 'IDLE' || state === 'UPLOADING'} done={['EXTRACTING','WAITING_FOR_REVIEW','GENERATING','COMPLETED'].includes(state)} />
                    <div style={styles.stepLine} />
                    <Step num={2} label="AI 识别字幕" active={state === 'EXTRACTING'} done={['WAITING_FOR_REVIEW','GENERATING','COMPLETED'].includes(state)} />
                    <div style={styles.stepLine} />
                    <Step num={3} label="审核确认" active={state === 'WAITING_FOR_REVIEW'} done={['GENERATING','COMPLETED'].includes(state)} />
                    <div style={styles.stepLine} />
                    <Step num={4} label="生成 & 下载" active={state === 'GENERATING' || state === 'COMPLETED'} done={state === 'COMPLETED'} />
                </div>

                <main style={{ ...styles.main, maxWidth: '1200px' }}>
                    {/* IDLE: Template Selection + Upload */}
                    {state === 'IDLE' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                            <div style={styles.templateSection}>
                                <h3 style={{ margin: '0 0 1.5rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    🎬 第一步：选择落版模板
                                    <span style={{ fontSize: '0.85rem', fontWeight: 400, color: '#94a3b8' }}>（自动识别帧、精准替换）</span>
                                </h3>
                                <div style={{ ...styles.templateGrid, gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
                                    {templates.length > 0 ? (
                                        templates.map(t => (
                                            <div 
                                                key={t} 
                                                onClick={() => setSelectedTemplate(t)}
                                                style={{
                                                    ...styles.templateCard,
                                                    borderColor: selectedTemplate === t ? '#3b82f6' : '#334155',
                                                    backgroundColor: selectedTemplate === t ? '#1e293b' : '#0f172a',
                                                    transform: selectedTemplate === t ? 'scale(1.02)' : 'scale(1)',
                                                }}
                                            >
                                                <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>📁</div>
                                                <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                                                    {TEMPLATE_LABELS[t.toLowerCase()] || t}
                                                </div>
                                                {selectedTemplate === t && <div style={styles.checkMark}>✓</div>}
                                            </div>
                                        ))
                                    ) : (
                                        <div style={{ color: '#94a3b8', fontSize: '0.9rem', padding: '2rem', border: '1px dashed #334155', borderRadius: '0.75rem', gridColumn: '1 / -1', textAlign: 'center' }}>
                                            未检测到落版模板，请将模板放入 worker/assets/outros 目录
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div style={styles.uploadZone}>
                                <label style={styles.uploadLabel}>
                                    <div style={styles.uploadIcon}>☁️</div>
                                    <span style={{ fontSize: '1.4rem', fontWeight: 700 }}>点击或拖拽上传视频</span>
                                    <span style={{ fontSize: '1rem', color: '#fca5a5', fontWeight: 700, marginTop: '0.5rem' }}>
                                        ⚠️ 仅支持 1080 x 1920 (9:16) 尺寸
                                    </span>
                                    <span style={{ fontSize: '0.9rem', color: '#94a3b8' }}>支持 MP4 / MOV / AVI</span>
                                    <input type="file" accept="video/*" onChange={handleUpload} style={{ display: 'none' }} />
                                </label>
                            </div>
                        </div>
                    )}

                    {/* Loading / Queued */}
                    {(state === 'UPLOADING' || state === 'EXTRACTING' || state === 'QUEUED') && (
                        <div style={styles.loadingCard}>
                            {state === 'QUEUED' ? (
                                <div style={{ fontSize: '4rem', marginBottom: '1.5rem' }}>⏳</div>
                            ) : (
                                <div style={{ ...styles.spinner, width: '4rem', height: '4rem' }} />
                            )}
                            <h2 style={{ ...styles.statusText, fontSize: '1.5rem', marginBottom: '1rem' }}>
                                {state === 'UPLOADING' && "⏳ 正在上传视频..."}
                                {state === 'EXTRACTING' && "🔍 AI 正在识别语音和字幕..."}
                                {state === 'QUEUED' && "🚦 显卡忙碌，任务排队中..."}
                            </h2>
                            {fileName && <p style={{ color: '#94a3b8', fontSize: '1rem', marginBottom: '1.5rem' }}>处理文件：{fileName}</p>}
                            
                            {state !== 'QUEUED' ? (
                                <div style={{ ...styles.progressBar, height: '8px', maxWidth: '500px', margin: '1rem auto' }}>
                                    <div style={{ ...styles.progressFill, animation: 'progress-pulse 2s ease-in-out infinite' }} />
                                </div>
                            ) : (
                                <button 
                                    onClick={() => handleAbort()}
                                    style={{
                                        backgroundColor: '#ef4444',
                                        color: 'white',
                                        border: 'none',
                                        padding: '0.8rem 2.5rem',
                                        borderRadius: '0.6rem',
                                        cursor: 'pointer',
                                        fontWeight: 700,
                                        marginTop: '1.5rem'
                                    }}
                                >
                                    🛑 取消任务排队
                                </button>
                            )}
                        </div>
                    )}

                    {/* GENERATING */}
                    {state === 'GENERATING' && (
                        <div style={styles.loadingCard}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: '1.5rem' }}>
                                <h2 style={{ ...styles.statusText, margin: 0, fontSize: '1.4rem' }}>🎬 正在完成本地化渲染</h2>
                                <button onClick={() => handleAbort()} style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: '1px solid #ef4444', padding: '0.4rem 1rem', borderRadius: '0.5rem', cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600 }}>🛑 终止全部</button>
                            </div>
                            <p style={{ color: '#94a3b8', fontSize: '1.1rem', marginBottom: '2rem' }}>
                                进度：已完成 <span style={{ color: '#10b981', fontWeight: 800 }}>{completedCount}</span> / {totalCount} 核心语言
                            </p>

                            <div style={{ ...styles.langGrid, gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))' }}>
                                {LANG_ORDER.map(lang => {
                                    const status = langProgress[lang] || 'waiting';
                                    const info = STATUS_LABELS[status] || STATUS_LABELS.waiting;
                                    return (
                                        <div key={lang} style={{ ...styles.langCard, padding: '1.2rem', borderColor: info.color, opacity: status === 'waiting' ? 0.4 : 1 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', width: '100%' }}>
                                                <span style={{ fontSize: '1.8rem' }}>{LANG_LABELS[lang]?.split(' ')[0]}</span>
                                                <div style={{ textAlign: 'left' }}>
                                                    <div style={{ fontWeight: 700, fontSize: '1rem' }}>{LANG_LABELS[lang]?.split(' ')[1]}</div>
                                                    <div style={{ fontSize: '0.8rem', color: info.color }}>{info.icon} {info.text}</div>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Review */}
                    {state === 'WAITING_FOR_REVIEW' && transcription && jobId && (
                        <div style={{ width: '100%' }}>
                             <SubtitleEditor 
                                jobId={jobId}
                                initialSegments={transcription.segments} 
                                onConfirm={handleApprove} 
                                onAbort={() => handleAbort(true)} 
                            />
                        </div>
                    )}

                    {/* Completed */}
                    {state === 'COMPLETED' && (
                        <div style={{ ...styles.successCard, padding: '4rem 2rem' }}>
                            <div style={{ ...styles.successIcon, fontSize: '5rem' }}>🎊</div>
                            <h2 style={{ fontSize: '2.5rem', margin: '1rem 0' }}>本地化制作完成！</h2>
                            <p style={{ color: '#a7f3d0', fontSize: '1.2rem', marginBottom: '1.5rem' }}>已成功生成 9 种语言的高清配音视频</p>
                            
                            <div style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'center' }}>
                                <a 
                                    href={`${API_HOST}/api/v1/jobs/${jobId}/download-all`}
                                    download
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.75rem',
                                        padding: '1.2rem 3rem',
                                        background: 'linear-gradient(135deg, #10b981, #059669)',
                                        color: 'white',
                                        textDecoration: 'none',
                                        borderRadius: '1.2rem',
                                        fontWeight: 800,
                                        fontSize: '1.2rem',
                                        boxShadow: '0 8px 24px rgba(16,185,129,0.4)',
                                        transition: 'all 0.3s ease'
                                    }}
                                    onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                                    onMouseOut={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                                >
                                    🗜️ 一键打包下载全部视频 (ZIP)
                                </a>
                            </div>

                            <div style={{ ...styles.downloadGrid, gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.5rem' }}>
                                {results.map(r => (
                                    <a key={r.lang_code} href={`${API_HOST}${r.download_url}`} download style={{ ...styles.downloadCard, padding: '1.5rem' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', width: '100%' }}>
                                            <span style={{ fontSize: '2rem' }}>{LANG_LABELS[r.lang_code]?.split(' ')[0] || '🌐'}</span>
                                            <div style={{ textAlign: 'left' }}>
                                                <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{LANG_LABELS[r.lang_code]?.split(' ')[1] || r.lang_code}</div>
                                                <div style={{ fontSize: '0.85rem', color: '#6ee7b7' }}>1080p MP4</div>
                                            </div>
                                            <span style={{ ...styles.downloadBadge, marginLeft: 'auto' }}>⬇ 下载</span>
                                        </div>
                                    </a>
                                ))}
                            </div>
                            <button 
                                onClick={resetToNewJob} 
                                style={{ ...styles.button, marginTop: '3.5rem', padding: '1.2rem 4rem', fontSize: '1.2rem', backgroundColor: '#334155' }}
                            >
                                处理下一个视频
                            </button>
                        </div>
                    )}

                    {/* Error */}
                    {state === 'ERROR' && (
                        <div style={styles.errorCard}>
                            <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>⚠️</div>
                            <h2 style={{ fontSize: '2rem' }}>处理失败</h2>
                            <p style={{ color: '#fca5a5', fontSize: '1.1rem', margin: '1rem 0 2rem' }}>{error}</p>
                            <button onClick={resetToNewJob} style={{ ...styles.button, padding: '1rem 3rem' }}>返回主界面</button>
                        </div>
                    )}
                </main>
            </div>
        </div>
    );
};

const Step: React.FC<{ num: number; label: string; active: boolean; done: boolean }> = ({ num, label, active, done }) => (
    <div style={{ textAlign: 'center', opacity: active || done ? 1 : 0.4 }}>
        <div style={{
            width: '2.5rem', height: '2.5rem', borderRadius: '50%', margin: '0 auto 0.5rem',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700,
            backgroundColor: done ? '#059669' : active ? '#3b82f6' : '#334155',
            color: 'white', fontSize: '1rem',
            boxShadow: active ? '0 0 12px rgba(59,130,246,0.5)' : 'none',
            transition: 'all 0.3s ease',
        }}>
            {done ? '✓' : num}
        </div>
        <span style={{ fontSize: '0.8rem', color: active ? '#f8fafc' : '#94a3b8' }}>{label}</span>
    </div>
);

const styles: Record<string, React.CSSProperties> = {
    container: { backgroundColor: '#0f172a', color: '#f8fafc', fontFamily: "'Inter', sans-serif" },
    header: { textAlign: 'center', marginBottom: '2rem', width: '100%' },
    title: { fontSize: '2.5rem', fontWeight: 800, background: 'linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' },
    subtitle: { color: '#94a3b8', fontSize: '1.1rem', marginTop: '0.5rem' },
    steps: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', marginBottom: '2.5rem' },
    stepLine: { width: '3rem', height: '2px', backgroundColor: '#334155' },
    main: { width: '100%' },
    templateSection: { backgroundColor: '#1e293b', padding: '2rem', borderRadius: '1.5rem', border: '1px solid #334155' },
    templateGrid: { display: 'grid', gap: '1rem' },
    templateCard: { position: 'relative', padding: '1.5rem', borderRadius: '1rem', border: '2px solid transparent', cursor: 'pointer', textAlign: 'center', transition: 'all 0.2s ease' },
    checkMark: { position: 'absolute', top: '0.75rem', right: '0.75rem', backgroundColor: '#3b82f6', color: 'white', width: '1.5rem', height: '1.5rem', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.9rem' },
    uploadZone: { border: '3px dashed #334155', borderRadius: '2rem', padding: '5rem 2rem', textAlign: 'center', cursor: 'pointer', backgroundColor: '#1e293b60', transition: 'all 0.3s ease', marginTop: '1rem' },
    uploadLabel: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', cursor: 'pointer', color: '#cbd5e1' },
    uploadIcon: { fontSize: '4rem' },
    loadingCard: { backgroundColor: '#1e293b', padding: '4rem 2rem', borderRadius: '2rem', textAlign: 'center', border: '1px solid #334155', width: '100%' },
    spinner: { border: '5px solid #334155', borderTopColor: '#3b82f6', borderRadius: '50%', margin: '0 auto', animation: 'spin 1s linear infinite' },
    statusText: { fontWeight: 700 },
    progressBar: { backgroundColor: '#0f172a', borderRadius: '4px', overflow: 'hidden' },
    progressFill: { height: '100%', background: 'linear-gradient(to right, #3b82f6, #8b5cf6)', borderRadius: '4px' },
    langGrid: { display: 'grid', gap: '1rem' },
    langCard: { display: 'flex', backgroundColor: '#0f172a', borderRadius: '1rem', border: '2px solid #334155', transition: 'all 0.3s ease' },
    successCard: { textAlign: 'center', backgroundColor: '#064e3b', borderRadius: '2rem', border: '1px solid #059669' },
    successIcon: { marginBottom: '1rem' },
    downloadGrid: { display: 'grid' },
    downloadCard: { display: 'flex', backgroundColor: '#065f46', borderRadius: '1.2rem', border: '1px solid #059669', cursor: 'pointer', textDecoration: 'none', color: '#f8fafc', transition: 'all 0.2s ease' },
    downloadBadge: { fontSize: '0.8rem', color: '#6ee7b7', backgroundColor: '#064e3b', padding: '0.3rem 0.8rem', borderRadius: '0.6rem', fontWeight: 700 },
    button: { border: 'none', borderRadius: '1rem', fontWeight: 800, cursor: 'pointer', transition: 'all 0.2s ease', color: 'white' },
    errorCard: { backgroundColor: '#450a0a', padding: '4rem 2rem', borderRadius: '2rem', border: '1px solid #991b1b', textAlign: 'center' }
};
