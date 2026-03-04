import { Router } from "express";
import authRouter from "./auth";
import webhooksRouter from "./webhooks";
import apiRouter from "./api";

const router = Router();

router.use("/auth", authRouter);
router.use("/webhooks", webhooksRouter);
router.use("/", apiRouter);

export default router;
