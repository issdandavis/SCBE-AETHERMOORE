// Stripe Integration - Standard Environment Variables
import Stripe from 'stripe';

async function getCredentials() {
  const publishableKey = process.env.STRIPE_PUBLISHABLE_KEY;
  const secretKey = process.env.STRIPE_SECRET_KEY;

  if (!secretKey) {
    throw new Error('STRIPE_SECRET_KEY not found - Please add your Stripe secret key to environment variables');
  }

  if (!publishableKey) {
    throw new Error('STRIPE_PUBLISHABLE_KEY not found - Please add your Stripe publishable key to environment variables');
  }

  return {
    publishableKey,
    secretKey,
  };
}

export async function isStripeConnected(): Promise<boolean> {
  try {
    await getCredentials();
    return true;
  } catch {
    return false;
  }
}

export async function getUncachableStripeClient() {
  const { secretKey } = await getCredentials();
  return new Stripe(secretKey, {
    apiVersion: '2025-11-17.clover',
  });
}

export async function getStripePublishableKey() {
  const { publishableKey } = await getCredentials();
  return publishableKey;
}

export async function getStripeSecretKey() {
  const { secretKey } = await getCredentials();
  return secretKey;
}

// Stripe sync functionality removed - use direct Stripe API calls instead
export async function getStripeSync() {
  throw new Error('Stripe sync functionality not available in this deployment. Use direct Stripe API calls instead.');
}

export async function listStripeProducts() {
  const stripe = await getUncachableStripeClient();
  const products = await stripe.products.list({ active: true, limit: 100 });
  return products.data;
}

export async function listStripePrices(productId?: string) {
  const stripe = await getUncachableStripeClient();
  const params: any = { active: true, limit: 100 };
  if (productId) params.product = productId;
  const prices = await stripe.prices.list(params);
  return prices.data;
}

export async function createStripeCustomer(email: string, metadata?: Record<string, string>) {
  const stripe = await getUncachableStripeClient();
  return await stripe.customers.create({ email, metadata });
}

export async function createStripeCheckoutSession(
  customerId: string,
  priceId: string,
  successUrl: string,
  cancelUrl: string,
  mode: 'subscription' | 'payment' = 'subscription'
) {
  const stripe = await getUncachableStripeClient();
  return await stripe.checkout.sessions.create({
    customer: customerId,
    payment_method_types: ['card'],
    line_items: [{ price: priceId, quantity: 1 }],
    mode,
    success_url: successUrl,
    cancel_url: cancelUrl,
  });
}

export async function createStripePortalSession(customerId: string, returnUrl: string) {
  const stripe = await getUncachableStripeClient();
  return await stripe.billingPortal.sessions.create({
    customer: customerId,
    return_url: returnUrl,
  });
}

export async function getStripeSubscription(subscriptionId: string) {
  const stripe = await getUncachableStripeClient();
  return await stripe.subscriptions.retrieve(subscriptionId);
}

export async function cancelStripeSubscription(subscriptionId: string) {
  const stripe = await getUncachableStripeClient();
  return await stripe.subscriptions.cancel(subscriptionId);
}

export async function createStripeProduct(name: string, description?: string, metadata?: Record<string, string>) {
  const stripe = await getUncachableStripeClient();
  return await stripe.products.create({
    name,
    description,
    metadata,
  });
}

export async function createStripePrice(
  productId: string,
  unitAmount: number,
  currency: string = 'usd',
  recurring?: { interval: 'month' | 'year' }
) {
  const stripe = await getUncachableStripeClient();
  const params: any = {
    product: productId,
    unit_amount: unitAmount,
    currency,
  };
  if (recurring) {
    params.recurring = recurring;
  }
  return await stripe.prices.create(params);
}
