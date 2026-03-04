import { Router, Request, Response } from "express";
import { getShopifySession } from "./auth";

const router = Router();

async function shopifyGraphQL(shop: string, accessToken: string, query: string, variables?: Record<string, any>) {
  const response = await fetch(`https://${shop}/admin/api/2024-01/graphql.json`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Shopify-Access-Token": accessToken,
    },
    body: JSON.stringify({ query, variables }),
  });

  if (!response.ok) {
    throw new Error(`Shopify API error: ${response.status}`);
  }

  return response.json();
}

router.get("/products", async (req: Request, res: Response) => {
  const shop = (req.session as any).shopifyShop;
  const accessToken = (req.session as any).shopifyAccessToken;

  if (!shop || !accessToken) {
    return res.status(401).json({ error: "Not authenticated with Shopify" });
  }

  try {
    const query = `
      query {
        products(first: 50) {
          edges {
            node {
              id
              title
              description
              handle
              status
              featuredImage {
                url
              }
              variants(first: 1) {
                edges {
                  node {
                    price
                  }
                }
              }
            }
          }
        }
      }
    `;

    const data = await shopifyGraphQL(shop, accessToken, query);
    const products = data.data.products.edges.map((edge: any) => ({
      id: edge.node.id,
      title: edge.node.title,
      description: edge.node.description,
      handle: edge.node.handle,
      status: edge.node.status,
      image: edge.node.featuredImage?.url,
      price: edge.node.variants.edges[0]?.node.price,
    }));

    res.json({ products });
  } catch (error) {
    console.error("Error fetching products:", error);
    res.status(500).json({ error: "Failed to fetch products" });
  }
});

router.post("/products/:productId/generate-description", async (req: Request, res: Response) => {
  const shop = (req.session as any).shopifyShop;
  const accessToken = (req.session as any).shopifyAccessToken;
  const { productId } = req.params;
  const { tone, keywords, aiModel } = req.body;

  if (!shop || !accessToken) {
    return res.status(401).json({ error: "Not authenticated with Shopify" });
  }

  try {
    const getProductQuery = `
      query getProduct($id: ID!) {
        product(id: $id) {
          id
          title
          description
          productType
          tags
          vendor
        }
      }
    `;

    const productData = await shopifyGraphQL(shop, accessToken, getProductQuery, { id: productId });
    const product = productData.data.product;

    if (!product) {
      return res.status(404).json({ error: "Product not found" });
    }

    const prompt = `Generate a compelling product description for an e-commerce product.

Product Title: ${product.title}
Product Type: ${product.productType || "General"}
Vendor: ${product.vendor || "Unknown"}
Tags: ${product.tags?.join(", ") || "None"}
Current Description: ${product.description || "No description"}

Tone: ${tone || "professional"}
Keywords to include: ${keywords || "quality, value"}

Write a persuasive 2-3 paragraph product description that:
1. Highlights key features and benefits
2. Uses the specified tone
3. Incorporates the keywords naturally
4. Encourages purchase

Return only the description text, no additional commentary.`;

    const aiResponse = await fetch("/api/ai/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: prompt,
        model: aiModel || "claude",
      }),
    });

    let generatedDescription = "";
    
    if (aiResponse.ok) {
      const aiData = await aiResponse.json();
      generatedDescription = aiData.response || aiData.message || "";
    } else {
      generatedDescription = `Discover the exceptional quality of ${product.title}. ` +
        `This ${product.productType || "product"} combines innovative design with premium materials, ` +
        `delivering outstanding value for discerning customers. ` +
        `Perfect for those who appreciate ${keywords || "quality and craftsmanship"}.`;
    }

    res.json({
      productId,
      originalDescription: product.description,
      generatedDescription,
      aiModel: aiModel || "fallback",
    });
  } catch (error) {
    console.error("Error generating description:", error);
    res.status(500).json({ error: "Failed to generate description" });
  }
});

router.put("/products/:productId/description", async (req: Request, res: Response) => {
  const shop = (req.session as any).shopifyShop;
  const accessToken = (req.session as any).shopifyAccessToken;
  const { productId } = req.params;
  const { description } = req.body;

  if (!shop || !accessToken) {
    return res.status(401).json({ error: "Not authenticated with Shopify" });
  }

  try {
    const mutation = `
      mutation updateProduct($input: ProductInput!) {
        productUpdate(input: $input) {
          product {
            id
            title
            description
          }
          userErrors {
            field
            message
          }
        }
      }
    `;

    const result = await shopifyGraphQL(shop, accessToken, mutation, {
      input: {
        id: productId,
        descriptionHtml: description,
      },
    });

    if (result.data.productUpdate.userErrors?.length > 0) {
      return res.status(400).json({ 
        error: result.data.productUpdate.userErrors[0].message 
      });
    }

    res.json({
      success: true,
      product: result.data.productUpdate.product,
    });
  } catch (error) {
    console.error("Error updating product:", error);
    res.status(500).json({ error: "Failed to update product" });
  }
});

router.get("/shop", async (req: Request, res: Response) => {
  const shop = (req.session as any).shopifyShop;
  const accessToken = (req.session as any).shopifyAccessToken;

  if (!shop || !accessToken) {
    return res.status(401).json({ error: "Not authenticated with Shopify" });
  }

  try {
    const query = `
      query {
        shop {
          name
          email
          myshopifyDomain
          plan {
            displayName
          }
          primaryDomain {
            url
          }
        }
      }
    `;

    const data = await shopifyGraphQL(shop, accessToken, query);
    res.json({ shop: data.data.shop });
  } catch (error) {
    console.error("Error fetching shop:", error);
    res.status(500).json({ error: "Failed to fetch shop info" });
  }
});

export default router;
