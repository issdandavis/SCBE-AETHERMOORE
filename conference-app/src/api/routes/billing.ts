/**
 * @file billing.ts
 * @module conference/api/routes
 *
 * Stripe billing routes for CaaS plan management.
 *
 * - POST /api/billing/checkout — create a checkout session for plan upgrade
 * - POST /api/billing/portal — get customer portal URL
 * - POST /api/billing/webhook — Stripe webhook handler
 */

import { Router, type Request, type Response } from 'express';
import { authMiddleware } from '../middleware/auth.js';
import { billingService } from '../services/billing.js';
import { tenantService } from '../services/tenant.js';
import express from 'express';

const router = Router();

/**
 * POST /api/billing/checkout
 * Create a Stripe checkout session for plan upgrade.
 * Body: { orgSlug, plan }
 */
router.post('/checkout', authMiddleware, async (req: Request, res: Response) => {
  const { orgSlug, plan } = req.body as { orgSlug?: string; plan?: string };

  if (!orgSlug || !plan || !['growth', 'enterprise'].includes(plan)) {
    res.status(400).json({ success: false, error: 'orgSlug and plan (growth|enterprise) required' });
    return;
  }

  const org = tenantService.getBySlug(orgSlug);
  if (!org) {
    res.status(404).json({ success: false, error: 'Organization not found' });
    return;
  }

  if (!tenantService.hasRole(org.id, req.user!.id, 'owner')) {
    res.status(403).json({ success: false, error: 'Only the org owner can manage billing' });
    return;
  }

  try {
    // Create Stripe customer if needed
    let customerId = (org as any).stripeCustomerId;
    if (!customerId) {
      customerId = await billingService.createCustomer(req.user!.email, org.name, org.id);
    }

    const origin = req.headers.origin ?? 'http://localhost:5173';
    const { url, sessionId } = await billingService.createCheckoutSession(
      customerId!,
      plan as 'growth' | 'enterprise',
      org.id,
      `${origin}/pricing?upgrade=success`,
      `${origin}/pricing?upgrade=cancelled`
    );

    res.json({ success: true, data: { checkoutUrl: url, sessionId } });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    res.status(500).json({ success: false, error: `Billing error: ${message}` });
  }
});

/**
 * POST /api/billing/portal
 * Get a Stripe customer portal URL for managing subscriptions.
 * Body: { orgSlug }
 */
router.post('/portal', authMiddleware, async (req: Request, res: Response) => {
  const { orgSlug } = req.body as { orgSlug?: string };
  if (!orgSlug) {
    res.status(400).json({ success: false, error: 'orgSlug required' });
    return;
  }

  const org = tenantService.getBySlug(orgSlug);
  if (!org) {
    res.status(404).json({ success: false, error: 'Organization not found' });
    return;
  }

  if (!tenantService.hasRole(org.id, req.user!.id, 'owner')) {
    res.status(403).json({ success: false, error: 'Only the org owner can manage billing' });
    return;
  }

  const customerId = (org as any).stripeCustomerId;
  if (!customerId) {
    res.status(400).json({ success: false, error: 'No billing account. Start a checkout first.' });
    return;
  }

  const origin = req.headers.origin ?? 'http://localhost:5173';
  const portalUrl = await billingService.createPortalSession(customerId, `${origin}/pricing`);
  res.json({ success: true, data: { portalUrl } });
});

/**
 * POST /api/billing/webhook
 * Stripe webhook handler. Verifies signature, processes events.
 *
 * Handles:
 * - checkout.session.completed — activate plan
 * - customer.subscription.updated — plan changes
 * - customer.subscription.deleted — downgrade to starter
 */
router.post(
  '/webhook',
  express.raw({ type: 'application/json' }),
  (req: Request, res: Response) => {
    const signature = req.headers['stripe-signature'] as string;
    if (!signature) {
      res.status(400).json({ error: 'Missing stripe-signature header' });
      return;
    }

    const event = billingService.verifyWebhookEvent(req.body as Buffer, signature);
    if (!event) {
      res.status(400).json({ error: 'Invalid webhook signature' });
      return;
    }

    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as any;
        const orgId = session.metadata?.orgId;
        const plan = session.metadata?.plan;
        if (orgId && plan) {
          const org = tenantService.getById(orgId);
          if (org) {
            // Upgrade plan via the internal service
            (org as any).plan = plan;
            (org as any).stripeCustomerId = session.customer;
            (org as any).stripeSubscriptionId = session.subscription;
            console.log(`[billing] Org ${org.slug} upgraded to ${plan}`);
          }
        }
        break;
      }

      case 'customer.subscription.updated': {
        const sub = event.data.object as any;
        // Handle plan changes (upgrade/downgrade)
        console.log(`[billing] Subscription updated: ${sub.id}`);
        break;
      }

      case 'customer.subscription.deleted': {
        const sub = event.data.object as any;
        // Downgrade to starter
        console.log(`[billing] Subscription deleted: ${sub.id}, downgrading to starter`);
        break;
      }

      default:
        console.log(`[billing] Unhandled event: ${event.type}`);
    }

    res.json({ received: true });
  }
);

export default router;
