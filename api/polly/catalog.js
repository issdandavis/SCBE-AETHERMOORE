'use strict';

const { sendJson, setCors } = require('../_agent_common');
const {
  PRODUCT_CATALOG,
  CONSULTING_TIERS,
  SERVICE_CREDITS_POLICY,
  CONSULTING_LANDING_URL,
  HIRE_EMAIL,
} = require('./commerce');

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'GET') {
    return sendJson(res, 405, { ok: false, error: 'GET only' });
  }

  return sendJson(res, 200, {
    ok: true,
    products: PRODUCT_CATALOG.map((p) => ({
      sku: p.sku,
      name: p.name,
      price_label: p.priceLabel,
      short: p.short,
      checkout_url: p.checkoutUrl,
      delivery_url: p.deliveryUrl,
    })),
    service_credits_policy: SERVICE_CREDITS_POLICY,
    consulting_tiers: CONSULTING_TIERS,
    consulting_landing_url: CONSULTING_LANDING_URL,
    hire_email: HIRE_EMAIL,
  });
};
