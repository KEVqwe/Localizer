import React, { useState, useRef } from 'react';

interface Segment {
    start: number;
    end: number;
    text: string;
    id?: number;
}

interface Props {
    jobId: string;
    initialSegments: Segment[];
    onConfirm: (validated: Segment[], outroStartTime: number | null, yPercent: number) => void;
    onAbort?: () => void;
}

const API_HOST = `${window.location.protocol}//${window.location.hostname}:8080`;

export const SubtitleEditor: React.FC<Props> = ({ jobId, initialSegments, onConfirm, onAbort }) => {
    const [segments, setSegments] = useState<Segment[]>(
        initialSegments.map((s, i) => ({ ...s, id: i }))
    );
    const [outroIndex, setOutroIndex] = useState<number | null>(null);
    const [yPercent, setYPercent] = useState<number>(0.8); // Default 80% from top
    const [isDragging, setIsDragging] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const handleTextChange = (id: number, newText: string) => {
        setSegments(prev => prev.map(s => s.id === id ? { ...s, text: newText } : s));
    };

    const handleSave = () => {
        let outroStartTime: number | null = null;
        if (outroIndex !== null) {
            outroStartTime = segments[outroIndex].start;
        }
        onConfirm(segments, outroStartTime, yPercent);
    };

    const handleAbort = () => {
        if (window.confirm("⚠️ 确定要放弃当前任务并彻底删除所有已处理文件吗？此操作不可撤销。")) {
            onAbort?.();
        }
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!isDragging || !containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        let y = (e.clientY - rect.top) / rect.height;
        y = Math.max(0.05, Math.min(0.95, y)); // Limit to safe areas
        setYPercent(y);
    };

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = (seconds % 60).toFixed(2);
        return `${mins}:${secs.padStart(5, '0')}`;
    };

    return (
        <div style={styles.editorContainer}>
            {/* Split Layout: Left Preview, Right List */}
            <div style={styles.layout}>
                
                {/* Visual Positioning Preview */}
                <div style={styles.previewSection}>
                    <h3 style={styles.sectionTitle}>🎬 调整字幕位置</h3>
                    <p style={styles.sectionSub}>上下拖动蓝色方框，确定字幕烧录高度</p>
                    
                    <div 
                        ref={containerRef}
                        style={styles.videoContainer}
                        onMouseMove={handleMouseMove}
                        onMouseUp={() => setIsDragging(false)}
                        onMouseLeave={() => setIsDragging(false)}
                    >
                        <video 
                            src={`${API_HOST}/api/v1/jobs/${jobId}/original-video`} 
                            style={styles.originalVideo}
                            muted
                            autoPlay
                            loop
                        />
                        {/* Draggable Placeholder */}
                        <div 
                            onMouseDown={() => setIsDragging(true)}
                            style={{
                                ...styles.subtitlePlaceholder,
                                top: `${yPercent * 100}%`,
                                cursor: isDragging ? 'grabbing' : 'grab',
                            }}
                        >
                            <div style={styles.placeholderHandle}>⠿</div>
                            <span style={styles.placeholderText}>示例字幕：在此高度烧录</span>
                        </div>
                    </div>
                    <div style={styles.posInfo}>
                        当前高度：{Math.round(yPercent * 100)}%
                    </div>
                </div>

                {/* Subtitle List */}
                <div style={styles.listSection}>
                    <div style={styles.editorHeader}>
                        <h2 style={styles.editorTitle}>📝 审核 & 设定落版</h2>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button onClick={handleAbort} style={{ ...styles.saveButton, backgroundColor: '#ef4444' }}>🗑️ 放弃任务</button>
                            <button onClick={handleSave} style={styles.saveButton}>✅ 开启生成</button>
                        </div>
                    </div>

                    <div style={styles.helpTip}>
                        💡 <strong>操作：</strong>核对文字。点击段落右侧「标记为落版起点」后，该段及之后将替换为本地化视频。
                    </div>

                    <div style={styles.segmentList}>
                        {segments.map((seg, idx) => {
                            const isProtected = outroIndex !== null && idx >= outroIndex;
                            return (
                                <div key={seg.id} style={{
                                    ...styles.segmentCard,
                                    borderLeft: isProtected ? '4px solid #fbbf24' : '4px solid #3b82f6',
                                    backgroundColor: isProtected ? '#1e293b' : '#0f172a',
                                }}>
                                    <div style={styles.segmentMeta}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
                                            <span style={styles.segIndex}>#{idx + 1}</span>
                                            <span style={styles.timeTag}>{formatTime(seg.start)}</span>
                                        </div>
                                        <button 
                                            onClick={(e) => { e.stopPropagation(); setOutroIndex(outroIndex === idx ? null : idx); }}
                                            style={{
                                                ...styles.outroBtn,
                                                backgroundColor: outroIndex === idx ? '#92400e' : '#1e293b',
                                                borderColor: outroIndex === idx ? '#fbbf24' : '#475569',
                                            }}
                                        >
                                            {outroIndex === idx ? '🏁 已标为落版' : '标记为落版'}
                                        </button>
                                    </div>
                                    <textarea
                                        style={{
                                            ...styles.textArea,
                                            textDecoration: isProtected ? 'line-through' : 'none',
                                            opacity: isProtected ? 0.5 : 1,
                                        }}
                                        value={seg.text}
                                        onChange={(e) => handleTextChange(seg.id!, e.target.value)}
                                        rows={1}
                                        disabled={isProtected}
                                    />
                                    {isProtected && (
                                        <div style={styles.protectBanner}>
                                            🎬 <strong>落版区</strong>：不生成字幕与配音
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Bottom Bar */}
            <div style={styles.bottomBar}>
                <button onClick={handleAbort} style={{ ...styles.saveButton, backgroundColor: '#ef4444', padding: '1rem 2.5rem' }}>🗑️ 放弃任务并物理删除</button>
                <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', gap: '0.5rem', alignItems: 'flex-end' }}>
                    <span style={{ color: '#94a3b8', fontSize: '0.9rem' }}>建议：避开视频底部的下载按钮或 UI 元素</span>
                    <button onClick={handleSave} style={{ ...styles.saveButton, padding: '1.2rem 4rem', fontSize: '1.2rem' }}>🚀 确认所有设定并开始任务</button>
                </div>
            </div>
        </div>
    );
};

const styles: Record<string, React.CSSProperties> = {
    editorContainer: {
        backgroundColor: '#1e293b',
        borderRadius: '1.5rem',
        padding: '2rem',
        border: '1px solid #334155',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        width: '1000px',
        maxWidth: '95vw',
        margin: '0 auto',
    },
    layout: {
        display: 'flex',
        gap: '2.5rem',
        height: '620px',
    },
    previewSection: {
        flex: '0 0 320px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
    },
    sectionTitle: { fontSize: '1.2rem', margin: '0 0 0.2rem 0', fontWeight: 700 },
    sectionSub: { fontSize: '0.8rem', color: '#94a3b8', margin: '0 0 1.5rem 0' },
    videoContainer: {
        position: 'relative',
        width: '280px',
        aspectRatio: '9/16',
        backgroundColor: '#000',
        borderRadius: '0.75rem',
        overflow: 'hidden',
        border: '4px solid #334155',
        userSelect: 'none',
    },
    originalVideo: { width: '100%', height: '100%', objectFit: 'contain' },
    subtitlePlaceholder: {
        position: 'absolute',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: '80%',
        backgroundColor: 'rgba(59, 130, 246, 0.9)',
        padding: '8px 12px',
        borderRadius: '4px',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
        border: '2px solid #fff',
        zIndex: 10,
    },
    placeholderHandle: { color: '#fff', fontSize: '14px', fontWeight: 'bold' },
    placeholderText: { color: '#fff', fontSize: '10px', fontWeight: 600, whiteSpace: 'nowrap' },
    posInfo: { marginTop: '1rem', fontSize: '0.9rem', color: '#60a5fa', fontWeight: 700 },
    
    listSection: {
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
    },
    editorHeader: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1rem',
    },
    editorTitle: { fontSize: '1.4rem', margin: 0, fontWeight: 700 },
    saveButton: {
        backgroundColor: '#3b82f6',
        color: 'white',
        border: 'none',
        padding: '0.6rem 1.2rem',
        borderRadius: '0.75rem',
        fontWeight: 600,
        cursor: 'pointer',
        fontSize: '0.9rem',
    },
    helpTip: {
        backgroundColor: '#0f172a',
        padding: '0.8rem 1rem',
        borderRadius: '0.75rem',
        fontSize: '0.8rem',
        color: '#94a3b8',
        marginBottom: '1rem',
    },
    segmentList: {
        flex: 1,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.6rem',
        paddingRight: '0.5rem',
    },
    segmentCard: { padding: '0.8rem 1rem', borderRadius: '0.75rem' },
    segmentMeta: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' },
    segIndex: { color: '#64748b', fontSize: '0.8rem', fontFamily: 'monospace' },
    timeTag: { fontFamily: 'monospace', color: '#60a5fa', fontSize: '0.8rem' },
    outroBtn: { fontSize: '0.75rem', padding: '0.2rem 0.6rem', borderRadius: '0.4rem', border: '1px solid #475569', color: '#f8fafc', cursor: 'pointer' },
    textArea: { width: '100%', backgroundColor: '#0f172a80', border: '1px solid #334155', borderRadius: '0.5rem', color: '#f8fafc', fontSize: '0.95rem', padding: '0.4rem 0.6rem' },
    protectBanner: { fontSize: '0.75rem', color: '#fbbf24', marginTop: '0.4rem' },
    bottomBar: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid #334155' },
};
