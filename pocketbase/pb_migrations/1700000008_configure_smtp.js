/// <reference path="../pb_data/types.d.ts" />

/**
 * Migration: Configure SMTP settings for Resend
 *
 * This migration configures PocketBase SMTP to use Resend for sending emails.
 * Resend uses SMTP on smtp.resend.com:465 (TLS)
 *
 * Note: The API key is read from environment variable or uses default from .env.dev
 */

migrate((app) => {
    console.log("[SMTP] Configuring Resend SMTP settings...");

    const settings = app.settings();

    // Read from environment variables (or use defaults)
    const smtpHost = $os.getenv("SMTP_HOST") || "smtp.resend.com";
    const smtpPort = parseInt($os.getenv("SMTP_PORT") || "465");
    const smtpUsername = $os.getenv("SMTP_USERNAME") || "resend";
    const apiKey = $os.getenv("RESEND_API_KEY") || "";
    const senderAddress = $os.getenv("SMTP_SENDER") || "noreply@impshow.com";

    // Only configure if API key is provided
    if (!apiKey) {
        console.log("[SMTP] No RESEND_API_KEY found, skipping SMTP configuration");
        return;
    }

    // Configure SMTP settings
    settings.smtp.enabled = true;
    settings.smtp.host = smtpHost;
    settings.smtp.port = smtpPort;
    settings.smtp.tls = true;
    settings.smtp.authMethod = "PLAIN";
    settings.smtp.username = smtpUsername;
    settings.smtp.password = apiKey;

    // Configure sender information
    settings.meta.senderName = "OrgMeet";
    settings.meta.senderAddress = senderAddress;

    app.save(settings);

    console.log("[SMTP] SMTP settings configured successfully!");
    console.log("[SMTP] Host:", smtpHost);
    console.log("[SMTP] Port:", smtpPort);
    console.log("[SMTP] Sender:", senderAddress);

}, (app) => {
    // Rollback: disable SMTP
    console.log("[SMTP] Rolling back SMTP configuration...");

    const settings = app.settings();
    settings.smtp.enabled = false;
    app.save(settings);
});
