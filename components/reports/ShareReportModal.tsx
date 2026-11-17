'use client';

import React, { useState } from 'react';
import { InvestigationReportResponse } from '@/types';

interface ShareReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: InvestigationReportResponse | null;
  activeSceneId: string | null;
  isDemo: boolean;
  onExportPDF: () => void;
  onExportJSON: () => void;
}

export default function ShareReportModal({
  isOpen,
  onClose,
  report,
  activeSceneId,
  isDemo,
  onExportPDF,
  onExportJSON,
}: ShareReportModalProps) {
  const [copiedMessage, setCopiedMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const sceneId = report?.scene_id || activeSceneId || (isDemo ? 'DEMO-SAR-2026' : 'S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG');
  const attentionLevel = report?.operational_alert?.attention_level || (isDemo ? 'CRITICAL_ATTENTION' : 'NO_EVENT');
  const detectionResult = report?.sar_detection?.oil_detected ? 'OIL SPILL DETECTED' : 'NO SPILL DETECTED';
  
  const reportUrl = typeof window !== 'undefined' ? window.location.href : 'http://localhost:3000/reports';
  const shareText = `OceanTrace AI Investigation Report\nScene ID: ${sceneId}\nAttention Level: ${attentionLevel}\nDetection Result: ${detectionResult}\nView Report: ${reportUrl}`;
  const emailSubject = `OceanTrace AI Investigation Report — ${sceneId}`;

  const showFeedback = (msg: string) => {
    setCopiedMessage(msg);
    setTimeout(() => setCopiedMessage(null), 3000);
  };

  const handleSystemShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `OceanTrace AI Report — ${sceneId}`,
          text: shareText,
          url: reportUrl,
        });
      } catch (err) {
        // User cancelled or share failed
      }
    } else {
      await handleCopyLink();
    }
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(reportUrl);
      showFeedback('REPORT LINK COPIED TO CLIPBOARD');
    } catch (err) {
      showFeedback('FAILED TO COPY LINK');
    }
  };

  const handleWhatsAppShare = () => {
    const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(shareText)}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleEmailShare = () => {
    const url = `mailto:?subject=${encodeURIComponent(emailSubject)}&body=${encodeURIComponent(shareText)}`;
    window.location.href = url;
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(3, 13, 24, 0.85)',
        backdropFilter: 'blur(6px)',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '440px',
          maxWidth: '92vw',
          background: 'var(--maritime-850)',
          border: '1px solid var(--border-medium)',
          borderRadius: '8px',
          padding: '18px 20px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: '0.55rem', color: '#475569', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
              SHARE INVESTIGATION REPORT
            </div>
            <h2 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#e2e8f0', marginTop: '2px' }}>
              {sceneId}
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              fontSize: '1.2rem',
              lineHeight: 1,
              padding: '4px',
            }}
          >
            ✕
          </button>
        </div>

        {/* Feedback Message Banner */}
        {copiedMessage && (
          <div
            style={{
              padding: '6px 12px',
              background: 'rgba(34, 211, 238, 0.12)',
              border: '1px solid rgba(34, 211, 238, 0.3)',
              borderRadius: '4px',
              fontSize: '0.62rem',
              fontWeight: 600,
              color: '#22d3ee',
              textAlign: 'center',
              letterSpacing: '0.08em',
            }}
          >
            {copiedMessage}
          </div>
        )}

        {/* Share Action Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          <button
            className="btn-secondary"
            onClick={handleSystemShare}
            style={{ justifyContent: 'center', fontSize: '0.65rem', padding: '10px 8px' }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
            System Share
          </button>

          <button
            className="btn-secondary"
            onClick={handleWhatsAppShare}
            style={{ justifyContent: 'center', fontSize: '0.65rem', padding: '10px 8px' }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#25D366" strokeWidth="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
            WhatsApp
          </button>

          <button
            className="btn-secondary"
            onClick={handleEmailShare}
            style={{ justifyContent: 'center', fontSize: '0.65rem', padding: '10px 8px' }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
            Email Report
          </button>

          <button
            className="btn-secondary"
            onClick={handleCopyLink}
            style={{ justifyContent: 'center', fontSize: '0.65rem', padding: '10px 8px' }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
            Copy Link
          </button>

          <button
            className="btn-primary"
            onClick={onExportPDF}
            style={{ justifyContent: 'center', fontSize: '0.65rem', padding: '10px 8px' }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            Download PDF
          </button>

          <button
            className="btn-secondary"
            onClick={onExportJSON}
            style={{ justifyContent: 'center', fontSize: '0.65rem', padding: '10px 8px' }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            Download JSON
          </button>
        </div>

        {/* Disclaimer */}
        <div style={{ padding: '8px 10px', background: 'rgba(30, 41, 59, 0.5)', borderRadius: '4px', border: '1px solid rgba(51,65,85,0.4)' }}>
          <p style={{ fontSize: '0.52rem', color: '#64748b', lineHeight: 1.4, margin: 0 }}>
            <strong style={{ color: '#94a3b8' }}>Decision Support Disclaimer:</strong> This shared report contains automated AI satellite analysis. It does not contain sensitive API keys, system credentials, or legal determinations.
          </p>
        </div>
      </div>
    </div>
  );
}
