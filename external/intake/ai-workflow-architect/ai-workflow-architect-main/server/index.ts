import express, { type Request, Response, NextFunction } from "express";
import session from "express-session";
import helmet from "helmet";
import cors from "cors";
import { registerRoutes } from "./routes";
import { serveStatic } from "./static";
import { createServer, Server } from "http";

// Create server early for shutdown handling
const app = express();
const httpServer: Server = createServer(app);

// Graceful shutdown handling
let isShuttingDown = false;
const shutdown = (signal: string) => {
  if (isShuttingDown) return;
  isShuttingDown = true;
  console.log(`\nReceived ${signal}. Shutting down gracefully...`);
  
  httpServer.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
  
  // Force exit after 5 seconds if graceful shutdown fails
  setTimeout(() => {
    console.log('Forcing shutdown...');
    process.exit(1);
  }, 5000);
};

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

// Startup logging
console.log("Starting server initialization...");
console.log(`NODE_ENV: ${process.env.NODE_ENV || "development"}`);
console.log(`PORT: ${process.env.PORT || "5000"}`);

// Environment validation - warn but don't crash
const requiredEnvVars = ["DATABASE_URL"];
const productionEnvVars = ["SESSION_SECRET", "APP_ORIGIN"];

const missingVars: string[] = [];
for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    missingVars.push(envVar);
  }
}

if (process.env.NODE_ENV === "production") {
  for (const envVar of productionEnvVars) {
    if (!process.env[envVar]) {
      missingVars.push(envVar);
    }
  }
}

if (missingVars.length > 0) {
  console.error(`Missing required environment variables: ${missingVars.join(", ")}`);
  if (process.env.NODE_ENV === "production") {
    console.error("Cannot start in production without required variables");
    process.exit(1);
  }
}

declare module "http" {
  interface IncomingMessage {
    rawBody: unknown;
  }
}

// Security headers
app.use(helmet({
  contentSecurityPolicy: false, // Vite handles this in dev
  crossOriginEmbedderPolicy: false,
}));

// CORS configuration
const APP_ORIGIN = process.env.APP_ORIGIN || "http://localhost:5000";
app.use(cors({
  origin: APP_ORIGIN,
  credentials: true,
}));

// Session configuration
app.use(
  session({
    secret: process.env.SESSION_SECRET || "dev-secret-change-in-production",
    resave: false,
    saveUninitialized: false,
    cookie: {
      secure: process.env.NODE_ENV === "production",
      httpOnly: true,
      maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
      sameSite: "lax",
    },
  })
);

app.use(
  express.json({
    verify: (req, _res, buf) => {
      req.rawBody = buf;
    },
  }),
);

app.use(express.urlencoded({ extended: false }));

export function log(message: string, source = "express") {
  const formattedTime = new Date().toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });

  console.log(`${formattedTime} [${source}] ${message}`);
}

app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }

      log(logLine);
    }
  });

  next();
});

(async () => {
  try {
    console.log("Registering routes...");
    await registerRoutes(httpServer, app);
    console.log("Routes registered successfully");

    app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
      const status = err.status || err.statusCode || 500;
      const message = err.message || "Internal Server Error";
      console.error(`Error ${status}: ${message}`);
      res.status(status).json({ message });
    });

    // Setup static serving or Vite dev server
    if (process.env.NODE_ENV === "production") {
      console.log("Setting up static file serving for production...");
      serveStatic(app);
    } else {
      console.log("Setting up Vite dev server...");
      const { setupVite } = await import("./vite");
      await setupVite(httpServer, app);
    }

    // Test database connection
    try {
      // Use mock database if no DATABASE_URL is set
      const dbModule = process.env.DATABASE_URL ? "./db" : "./db-mock";
      const { testDatabaseConnection } = await import(dbModule);
      const dbConnected = await testDatabaseConnection();
      console.log(`Database connection test: ${dbConnected ? "SUCCESS" : "FAILED"}`);
    } catch (dbErr) {
      console.error("Database connection test error:", dbErr);
    }

    // ALWAYS serve the app on the port specified in the environment variable PORT
    const port = parseInt(process.env.PORT || "5000", 10);
    httpServer.listen(
      {
        port,
        host: "localhost",
      },
      () => {
        log(`🚀 Server ready on port ${port}`);
        log(`Environment: ${process.env.NODE_ENV || "development"}`);
        log(`Database: ${process.env.DATABASE_URL ? "Connected" : "Not configured"}`);
        console.log(`Server listening on localhost:${port}`);
      },
    );
  } catch (startupError) {
    console.error("Fatal startup error:", startupError);
    process.exit(1);
  }
})();
