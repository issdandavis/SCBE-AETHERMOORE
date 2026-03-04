import { Router, Request, Response } from "express";
import crypto from "crypto";

const router = Router();

const SHOPIFY_API_SECRET = process.env.SHOPIFY_API_SECRET;

function verifyWebhookHmac(rawBody: Buffer, hmac: string): boolean {
  if (!SHOPIFY_API_SECRET) return false;

  const generatedHmac = crypto
    .createHmac("sha256", SHOPIFY_API_SECRET)
    .update(rawBody)
    .digest("base64");

  return crypto.timingSafeEqual(
    Buffer.from(hmac),
    Buffer.from(generatedHmac)
  );
}

function webhookHandler(topic: string) {
  return (req: Request, res: Response) => {
    const hmac = req.headers["x-shopify-hmac-sha256"] as string;
    const shop = req.headers["x-shopify-shop-domain"] as string;
    const rawBody = (req as any).rawBody as Buffer;

    if (!hmac || !rawBody) {
      console.log(`[Shopify Webhook] ${topic}: Missing HMAC or body`);
      return res.status(401).json({ error: "Unauthorized" });
    }

    if (!verifyWebhookHmac(rawBody, hmac)) {
      console.log(`[Shopify Webhook] ${topic}: Invalid HMAC`);
      return res.status(401).json({ error: "Invalid HMAC" });
    }

    console.log(`[Shopify Webhook] ${topic} from ${shop}`);

    res.status(200).json({ received: true });
  };
}

router.post("/customers/redact", webhookHandler("customers/redact"));

router.post("/customers/data_request", webhookHandler("customers/data_request"));

router.post("/shop/redact", webhookHandler("shop/redact"));

router.post("/app/uninstalled", (req: Request, res: Response) => {
  const hmac = req.headers["x-shopify-hmac-sha256"] as string;
  const shop = req.headers["x-shopify-shop-domain"] as string;
  const rawBody = (req as any).rawBody as Buffer;

  if (!hmac || !rawBody || !verifyWebhookHmac(rawBody, hmac)) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  console.log(`[Shopify Webhook] App uninstalled from ${shop}`);

  res.status(200).json({ received: true });
});

router.post("/products/create", (req: Request, res: Response) => {
  const hmac = req.headers["x-shopify-hmac-sha256"] as string;
  const shop = req.headers["x-shopify-shop-domain"] as string;
  const rawBody = (req as any).rawBody as Buffer;

  if (!hmac || !rawBody || !verifyWebhookHmac(rawBody, hmac)) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  const product = req.body;
  console.log(`[Shopify Webhook] Product created in ${shop}: ${product.title}`);

  res.status(200).json({ received: true });
});

router.post("/products/update", (req: Request, res: Response) => {
  const hmac = req.headers["x-shopify-hmac-sha256"] as string;
  const shop = req.headers["x-shopify-shop-domain"] as string;
  const rawBody = (req as any).rawBody as Buffer;

  if (!hmac || !rawBody || !verifyWebhookHmac(rawBody, hmac)) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  const product = req.body;
  console.log(`[Shopify Webhook] Product updated in ${shop}: ${product.title}`);

  res.status(200).json({ received: true });
});

export default router;
