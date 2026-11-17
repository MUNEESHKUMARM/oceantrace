'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { SystemStatus } from '@/types';

const NAV_LINKS = [
  { href: '/', label: 'Dashboard' },
  { href: '/analysis', label: 'Analysis' },
  { href: '/vessels', label: 'Vessel Ranking' },
  { href: '/reports', label: 'Reports' },
];

const systemStatus: SystemStatus = {
  satellite: 'online',
  aiEngine: 'ready',
  ais: 'connected',
  wind: 'online',
  current: 'online',
  driftModel: 'ready',
};

function StatusPill({ label, status }: { label: string; status: string }) {
  const color =
    status === 'online' || status === 'ready' || status === 'connected'
      ? '#10b981'
      : status === 'processing' || status === 'running'
      ? '#f59e0b'
      : '#ef4444';

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        padding: '2px 7px',
        background: `${color}10`,
        border: `1px solid ${color}30`,
        borderRadius: '3px',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          width: '5px', height: '5px', borderRadius: '50%',
          background: color,
          boxShadow: `0 0 4px ${color}`,
          animation: status === 'processing' || status === 'running' ? 'pulse-warning 1s infinite' : 'none',
        }}
      />
      <span style={{ fontSize: '0.575rem', fontWeight: 600, letterSpacing: '0.08em', color: '#94a3b8' }}>
        {label}
      </span>
    </div>
  );
}

export default function TopNav() {
  const pathname = usePathname();
  const [utcTime, setUtcTime] = useState('');
  const [aisStatus, setAisStatus] = useState<string>('connected');

  useEffect(() => {
    const fmt = () => new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
    setUtcTime(fmt());
    const id = setInterval(() => setUtcTime(fmt()), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let isMounted = true;
    import('@/lib/api')
      .then(api => api.getAISCollectorStatus())
      .then(status => {
        if (isMounted) {
          setAisStatus(status.connected ? 'connected' : 'disconnected');
        }
      })
      .catch(() => {
        if (isMounted) setAisStatus('disconnected');
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <header
      style={{
        gridColumn: '1 / -1',
        background: 'var(--maritime-900)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        padding: '0 14px',
        height: '48px',
        flexShrink: 0,
        zIndex: 50,
      }}
    >
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
        {/* Ocean Wave Logo */}
        <div
          style={{
            width: '30px', height: '30px',
            background: 'rgba(34, 211, 238, 0.1)',
            border: '1px solid rgba(34, 211, 238, 0.3)',
            borderRadius: '5px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22d3ee" strokeWidth="2">
            <path d="M2 12c1.5-2 3-3 4.5-3s3 2 4.5 2 3-3 4.5-3 3 2 4.5 2" />
            <path d="M2 16c1.5-2 3-3 4.5-3s3 2 4.5 2 3-3 4.5-3 3 2 4.5 2" opacity="0.5" />
            <circle cx="19" cy="5" r="2" fill="#22d3ee" opacity="0.8" />
          </svg>
        </div>

        <div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#e2e8f0', letterSpacing: '0.04em', lineHeight: 1.1 }}>
            OceanTrace <span style={{ color: '#22d3ee' }}>AI</span>
          </div>
          <div style={{ fontSize: '0.52rem', color: '#475569', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            Maritime Intelligence
          </div>
        </div>
      </div>

      {/* Divider */}
      <div style={{ width: '1px', height: '24px', background: 'var(--border-subtle)', flexShrink: 0 }} />

      {/* Navigation */}
      <nav style={{ display: 'flex', gap: '2px', flex: 1 }}>
        {NAV_LINKS.map(link => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              style={{
                padding: '4px 12px',
                borderRadius: '4px',
                fontSize: '0.7rem',
                fontWeight: isActive ? 600 : 400,
                color: isActive ? '#22d3ee' : '#64748b',
                background: isActive ? 'rgba(34, 211, 238, 0.08)' : 'transparent',
                border: isActive ? '1px solid rgba(34, 211, 238, 0.2)' : '1px solid transparent',
                textDecoration: 'none',
                letterSpacing: '0.04em',
                transition: 'all 0.15s ease',
                whiteSpace: 'nowrap',
              }}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>

      {/* Status Pills */}
      <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
        <StatusPill label="SATELLITE" status={systemStatus.satellite} />
        <StatusPill label="AI ENGINE" status={systemStatus.aiEngine} />
        <StatusPill label="AIS" status={aisStatus} />
        <StatusPill label="OCEAN DATA" status={systemStatus.wind} />
        <StatusPill label="DRIFT MODEL" status={systemStatus.driftModel} />
      </div>

      {/* Divider */}
      <div style={{ width: '1px', height: '24px', background: 'var(--border-subtle)', flexShrink: 0 }} />

      {/* UTC Time + User */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.65rem', color: '#94a3b8', fontVariantNumeric: 'tabular-nums', fontFamily: 'monospace' }}>
            {utcTime}
          </div>
          <div style={{ fontSize: '0.55rem', color: '#475569', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            System Time
          </div>
        </div>

        {/* Live indicator */}
        <div
          style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            padding: '3px 8px',
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            borderRadius: '3px',
          }}
        >
          <div style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#10b981', boxShadow: '0 0 6px #10b981' }} />
          <span style={{ fontSize: '0.6rem', fontWeight: 700, color: '#10b981', letterSpacing: '0.1em' }}>LIVE</span>
        </div>

        {/* User Icon */}
        <div
          style={{
            width: '26px', height: '26px',
            borderRadius: '50%',
            background: 'rgba(34, 211, 238, 0.1)',
            border: '1px solid rgba(34, 211, 238, 0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer',
          }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#22d3ee" strokeWidth="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
          </svg>
        </div>
      </div>
    </header>
  );
}
