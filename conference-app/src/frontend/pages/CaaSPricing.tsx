/**
 * @file CaaSPricing.tsx
 * @module conference/frontend/pages
 *
 * Conferences-as-a-Service pricing page.
 * Shows three tiers: Starter, Growth, Enterprise.
 * Each tier lists features, limits, and CTA.
 */

import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';

interface PlanCard {
  plan: 'starter' | 'growth' | 'enterprise';
  name: string;
  price: string;
  priceSub: string;
  features: string[];
  limits: string[];
  cta: string;
  accent: string;
  popular?: boolean;
}

const PLANS: PlanCard[] = [
  {
    plan: 'starter',
    name: 'Starter',
    price: 'Free',
    priceSub: 'forever',
    accent: 'var(--accent-cyan)',
    cta: 'Get Started',
    features: [
      'SCBE 14-layer governance scoring',
      'Zoom meeting integration',
      'SSE real-time event streams',
      'NDA signing ceremony',
      'Soft-commit ticker',
      'Live chat + reactions',
    ],
    limits: [
      '2 conferences / month',
      '10 projects / conference',
      '1 API key',
      'Platform branding',
    ],
  },
  {
    plan: 'growth',
    name: 'Growth',
    price: '$99',
    priceSub: '/ month',
    accent: 'var(--accent-green)',
    cta: 'Start Free Trial',
    popular: true,
    features: [
      'Everything in Starter, plus:',
      'Custom branding (colors, logo, tagline)',
      'Custom NDA templates',
      'HYDRA swarm browser audit',
      'Deal room document management',
      'Governance threshold tuning',
    ],
    limits: [
      '10 conferences / month',
      '50 projects / conference',
      '5 API keys',
      'Priority support',
    ],
  },
  {
    plan: 'enterprise',
    name: 'Enterprise',
    price: 'Custom',
    priceSub: 'contact us',
    accent: 'var(--accent-purple)',
    cta: 'Contact Sales',
    features: [
      'Everything in Growth, plus:',
      'Custom domain (yourconference.com)',
      'Unlimited conferences + projects',
      'Unlimited API keys',
      'Dedicated support + SLA',
      'On-premise deployment option',
    ],
    limits: [
      'Unlimited everything',
      'White-glove onboarding',
      'Custom governance rules',
      'SOC 2 compliance ready',
    ],
  },
];

export default function CaaSPricing() {
  const { user } = useAuth();
  const { post } = useApi();
  const [creating, setCreating] = useState(false);
  const [orgSlug, setOrgSlug] = useState('');
  const [orgName, setOrgName] = useState('');
  const [showCreateForm, setShowCreateForm] = useState<string | null>(null);
  const [created, setCreated] = useState<{ slug: string; apiKeyPrefix: string } | null>(null);

  const handleCreate = async (plan: string) => {
    if (!orgName.trim() || !orgSlug.trim()) return;
    setCreating(true);
    const res = await post('/orgs', { name: orgName, slug: orgSlug, plan });
    if (res.success && res.data) {
      setCreated(res.data as any);
      setShowCreateForm(null);
    }
    setCreating(false);
  };

  return (
    <div>
      <div style={{ textAlign: 'center', marginBottom: 48 }}>
        <h1 style={{ fontFamily: 'var(--font-mono)', fontSize: '2.2rem', marginBottom: 8 }}>
          Conferences as a Service
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem', maxWidth: 600, margin: '0 auto' }}>
          Run governance-gated demo days for your community. SCBE-scored projects,
          NDA-locked investor access, live Zoom pitches, and real-time soft-commit tickers.
        </p>
      </div>

      {created && (
        <div className="card" style={{ marginBottom: 32, borderColor: 'var(--accent-green)', maxWidth: 600, margin: '0 auto 32px' }}>
          <h3 style={{ color: 'var(--accent-green)', fontFamily: 'var(--font-mono)', marginBottom: 8 }}>
            Organization Created
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 12 }}>
            Your organization is ready. Share the slug with your team.
          </p>
          <div className="governance-ribbon" style={{ justifyContent: 'flex-start' }}>
            <span className="governance-stat">slug: <span className="value">{created.slug}</span></span>
            <span className="governance-stat">API key: <span className="value">{created.apiKeyPrefix}</span></span>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 24, maxWidth: 960, margin: '0 auto' }}>
        {PLANS.map(plan => (
          <div
            key={plan.plan}
            className="card"
            style={{
              borderColor: plan.popular ? plan.accent : 'var(--border)',
              position: 'relative',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {plan.popular && (
              <div style={{
                position: 'absolute',
                top: -12,
                left: '50%',
                transform: 'translateX(-50%)',
                background: plan.accent,
                color: 'var(--bg-primary)',
                padding: '4px 16px',
                borderRadius: 12,
                fontSize: '0.72rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
              }}>
                MOST POPULAR
              </div>
            )}

            <h3 style={{ fontFamily: 'var(--font-mono)', color: plan.accent, marginBottom: 4, marginTop: plan.popular ? 12 : 0 }}>
              {plan.name}
            </h3>

            <div style={{ marginBottom: 20 }}>
              <span style={{ fontSize: '2rem', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>{plan.price}</span>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginLeft: 6 }}>{plan.priceSub}</span>
            </div>

            <div style={{ flex: 1 }}>
              <h4 style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
                Features
              </h4>
              {plan.features.map((f, i) => (
                <div key={i} style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', padding: '4px 0', display: 'flex', gap: 8 }}>
                  <span style={{ color: plan.accent }}>+</span> {f}
                </div>
              ))}

              <h4 style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: 16, marginBottom: 8 }}>
                Limits
              </h4>
              {plan.limits.map((l, i) => (
                <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-muted)', padding: '3px 0', fontFamily: 'var(--font-mono)' }}>
                  {l}
                </div>
              ))}
            </div>

            {showCreateForm === plan.plan ? (
              <div style={{ marginTop: 20 }}>
                <input
                  placeholder="Organization name"
                  value={orgName}
                  onChange={e => setOrgName(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', marginBottom: 8, fontSize: '0.85rem' }}
                />
                <input
                  placeholder="URL slug (e.g., my-accelerator)"
                  value={orgSlug}
                  onChange={e => setOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                  style={{ width: '100%', padding: '8px 12px', marginBottom: 12, fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}
                />
                <button
                  className="btn-primary"
                  style={{ width: '100%', background: plan.accent, borderColor: plan.accent }}
                  onClick={() => handleCreate(plan.plan)}
                  disabled={creating || !orgName.trim() || !orgSlug.trim()}
                >
                  {creating ? 'Creating...' : 'Create Organization'}
                </button>
              </div>
            ) : (
              <button
                className={plan.popular ? 'btn-primary' : 'btn-secondary'}
                style={{ marginTop: 20, width: '100%', ...(plan.popular ? { background: plan.accent, borderColor: plan.accent } : {}) }}
                onClick={() => {
                  if (user) {
                    setShowCreateForm(plan.plan);
                  } else {
                    window.location.href = '/auth';
                  }
                }}
              >
                {plan.cta}
              </button>
            )}
          </div>
        ))}
      </div>

      {/* How it works */}
      <div style={{ maxWidth: 800, margin: '64px auto 0', textAlign: 'center' }}>
        <h2 style={{ fontFamily: 'var(--font-mono)', marginBottom: 32, color: 'var(--accent-cyan)' }}>
          How CaaS Works
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 32 }}>
          {[
            { step: '01', label: 'Create Org', desc: 'Pick a plan, set your slug, get an API key' },
            { step: '02', label: 'Brand It', desc: 'Custom colors, logo, NDA template, governance thresholds' },
            { step: '03', label: 'Accept Projects', desc: 'Creators submit through your branded portal' },
            { step: '04', label: 'Score + Audit', desc: 'SCBE 14-layer pipeline + HYDRA swarm score every project' },
            { step: '05', label: 'Run Demo Days', desc: 'Zoom meetings, real-time ticker, live chat, soft-commits' },
            { step: '06', label: 'Close Deals', desc: 'NDA-gated deal rooms, cap tables, follow-up' },
          ].map(s => (
            <div key={s.step}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.8rem', color: 'var(--accent-purple)', fontWeight: 800 }}>
                {s.step}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, margin: '6px 0' }}>{s.label}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>{s.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* API section */}
      <div style={{ maxWidth: 700, margin: '64px auto 0' }}>
        <h2 style={{ fontFamily: 'var(--font-mono)', marginBottom: 16, color: 'var(--accent-green)' }}>
          API-First
        </h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 20 }}>
          Every CaaS feature is available through the REST API. Automate conference creation,
          project intake, governance scoring, and deal room management.
        </p>
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: 20,
          fontFamily: 'var(--font-mono)',
          fontSize: '0.8rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.8,
          whiteSpace: 'pre',
          overflow: 'auto',
        }}>
{`# Create a conference via API
curl -X POST /api/conferences \\
  -H "Authorization: Bearer \$USER_TOKEN" \\
  -H "x-org-api-key: caas_your_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "Demo Day Q1 2026",
    "theme": "AI Infrastructure",
    "description": "Quarterly showcase",
    "scheduledAt": "2026-03-20T18:00:00Z"
  }'

# Stream live events (SSE)
curl -N /api/zoom/conferences/:id/events \\
  -H "Authorization: Bearer \$USER_TOKEN"`}
        </div>
      </div>
    </div>
  );
}
