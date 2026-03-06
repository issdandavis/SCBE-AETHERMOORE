/**
 * @file billing.ts
 * @module conference/api/services
 *
 * Stripe billing integration for CaaS plan management.
 *
 * - Creates Stripe customers for org owners
 * - Creates checkout sessions for plan upgrades
 * - Handles webhooks (subscription created/updated/deleted)
 * - Manages subscription lifecycle
 *
 * Requires env: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
 * Price IDs: STRIPE_PRICE_GROWTH, STRIPE_PRICE_ENTERPRISE
 */

import Stripe from 'stripe';

// ═══════════════════════════════════════════════════════════════
// Config
// ═══════════════════════════════════════════════════════════════

const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY ?? '';
const STRIPE_WEBHOOK_SECRET = process.env.STRIPE_WEBHOOK_SECRET ?? '';

/** Map plan names to Stripe price IDs (set in env) */
const PRICE_IDS: Record<string, string> = {
  growth: process.env.STRIPE_PRICE_GROWTH ?? 'price_growth_placeholder',
  enterprise: process.env.STRIPE_PRICE_ENTERPRISE ?? 'price_enterprise_placeholder',
};

// ═══════════════════════════════════════════════════════════════
// Stripe Client
// ═══════════════════════════════════════════════════════════════

export class BillingService {
  private stripe: Stripe | null;

  constructor() {
    if (STRIPE_SECRET_KEY && STRIPE_SECRET_KEY !== '') {
      this.stripe = new Stripe(STRIPE_SECRET_KEY, { apiVersion: '2025-04-30.basil' as any });
    } else {
      this.stripe = null;
    }
  }

  isConfigured(): boolean {
    return this.stripe !== null;
  }

  /**
   * Create a Stripe customer for an organization.
   */
  async createCustomer(email: string, orgName: string, orgId: string): Promise<string | null> {
    if (!this.stripe) return `cus_simulated_${orgId.slice(0, 8)}`;

    const customer = await this.stripe.customers.create({
      email,
      name: orgName,
      metadata: { orgId },
    });

    return customer.id;
  }

  /**
   * Create a checkout session for a plan upgrade.
   * Returns the checkout URL to redirect the user to.
   */
  async createCheckoutSession(
    customerId: string,
    plan: 'growth' | 'enterprise',
    orgId: string,
    successUrl: string,
    cancelUrl: string
  ): Promise<{ url: string; sessionId: string }> {
    const priceId = PRICE_IDS[plan];

    if (!this.stripe) {
      // Simulated mode for dev
      return {
        url: `${successUrl}?session_id=sim_${orgId.slice(0, 8)}&plan=${plan}`,
        sessionId: `sim_${orgId.slice(0, 8)}`,
      };
    }

    const session = await this.stripe.checkout.sessions.create({
      customer: customerId,
      mode: 'subscription',
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${successUrl}?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: cancelUrl,
      metadata: { orgId, plan },
    });

    return { url: session.url!, sessionId: session.id };
  }

  /**
   * Create a customer portal session for managing subscriptions.
   */
  async createPortalSession(customerId: string, returnUrl: string): Promise<string> {
    if (!this.stripe) return returnUrl;

    const session = await this.stripe.billingPortal.sessions.create({
      customer: customerId,
      return_url: returnUrl,
    });

    return session.url;
  }

  /**
   * Verify and parse a Stripe webhook event.
   */
  verifyWebhookEvent(payload: Buffer, signature: string): Stripe.Event | null {
    if (!this.stripe || !STRIPE_WEBHOOK_SECRET) return null;

    try {
      return this.stripe.webhooks.constructEvent(payload, signature, STRIPE_WEBHOOK_SECRET);
    } catch {
      return null;
    }
  }

  /**
   * Cancel a subscription.
   */
  async cancelSubscription(subscriptionId: string): Promise<boolean> {
    if (!this.stripe) return true;

    try {
      await this.stripe.subscriptions.cancel(subscriptionId);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get subscription details.
   */
  async getSubscription(subscriptionId: string): Promise<Stripe.Subscription | null> {
    if (!this.stripe) return null;

    try {
      return await this.stripe.subscriptions.retrieve(subscriptionId);
    } catch {
      return null;
    }
  }
}

/** Singleton billing service */
export const billingService = new BillingService();
