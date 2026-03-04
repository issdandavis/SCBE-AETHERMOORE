import { Router, Request, Response } from "express";
import crypto from "crypto";

const router = Router();

const SHOPIFY_API_KEY = process.env.SHOPIFY_API_KEY;
const SHOPIFY_API_SECRET = process.env.SHOPIFY_API_SECRET;
const APP_URL = process.env.APP_ORIGIN || "https://de1427f3-8456-46c0-b7c0-1b93d8b0f2ab-00-2jrucxt94eeir.picard.replit.dev";
const SCOPES = "read_products,write_products,read_content,write_content";

interface ShopifySession {
  shop: string;
  accessToken: string;
  scope: string;
}

const shopifySessions = new Map<string, ShopifySession>();

function generateNonce(): string {
  return crypto.randomBytes(16).toString("hex");
}

function verifyHmac(query: Record<string, string>, secret: string): boolean {
  const { hmac, ...rest } = query;
  if (!hmac) return false;

  const message = Object.keys(rest)
    .sort()
    .map((key) => `${key}=${rest[key]}`)
    .join("&");

  const generatedHmac = crypto
    .createHmac("sha256", secret)
    .update(message)
    .digest("hex");

  return crypto.timingSafeEqual(
    Buffer.from(hmac, "hex"),
    Buffer.from(generatedHmac, "hex")
  );
}

router.get("/", (req: Request, res: Response) => {
  const shop = req.query.shop as string;

  if (!shop) {
    return res.status(400).json({ error: "Missing shop parameter" });
  }

  if (!SHOPIFY_API_KEY) {
    return res.status(500).json({ error: "Shopify API key not configured" });
  }

  const nonce = generateNonce();
  const redirectUri = `${APP_URL}/api/shopify/auth/callback`;

  const authUrl = `https://${shop}/admin/oauth/authorize?` +
    `client_id=${SHOPIFY_API_KEY}&` +
    `scope=${SCOPES}&` +
    `redirect_uri=${encodeURIComponent(redirectUri)}&` +
    `state=${nonce}`;

  (req.session as any).shopifyNonce = nonce;
  (req.session as any).shopifyShop = shop;

  res.redirect(authUrl);
});

router.get("/callback", async (req: Request, res: Response) => {
  const { shop, code, state, hmac } = req.query as Record<string, string>;

  if (!shop || !code || !state) {
    return res.status(400).json({ error: "Missing required parameters" });
  }

  if (!SHOPIFY_API_KEY || !SHOPIFY_API_SECRET) {
    return res.status(500).json({ error: "Shopify credentials not configured" });
  }

  const storedNonce = (req.session as any).shopifyNonce;
  if (state !== storedNonce) {
    return res.status(403).json({ error: "Invalid state parameter" });
  }

  if (!verifyHmac(req.query as Record<string, string>, SHOPIFY_API_SECRET)) {
    return res.status(403).json({ error: "Invalid HMAC" });
  }

  try {
    const tokenResponse = await fetch(`https://${shop}/admin/oauth/access_token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        client_id: SHOPIFY_API_KEY,
        client_secret: SHOPIFY_API_SECRET,
        code,
      }),
    });

    if (!tokenResponse.ok) {
      throw new Error("Failed to exchange code for access token");
    }

    const tokenData = await tokenResponse.json() as {
      access_token: string;
      scope: string;
    };

    shopifySessions.set(shop, {
      shop,
      accessToken: tokenData.access_token,
      scope: tokenData.scope,
    });

    (req.session as any).shopifyShop = shop;
    (req.session as any).shopifyAccessToken = tokenData.access_token;

    res.redirect(`/shopify/onboarding?shop=${shop}`);
  } catch (error) {
    console.error("Shopify OAuth error:", error);
    res.status(500).json({ error: "OAuth flow failed" });
  }
});

router.get("/session", (req: Request, res: Response) => {
  const shop = (req.session as any).shopifyShop;
  const accessToken = (req.session as any).shopifyAccessToken;

  if (!shop || !accessToken) {
    return res.status(401).json({ authenticated: false });
  }

  res.json({
    authenticated: true,
    shop,
  });
});

export function getShopifySession(shop: string): ShopifySession | undefined {
  return shopifySessions.get(shop);
}

export default router;
