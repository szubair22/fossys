#!/bin/bash

# Test SMTP Configuration with Resend
# This script authenticates as superuser and sends a test email

PB_URL="${PB_URL:-http://localhost:8090}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@orgmeet.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-AdminPassword123}"
TEST_EMAIL="${TEST_EMAIL:-test@example.com}"

echo "Testing SMTP configuration..."
echo "PocketBase URL: $PB_URL"
echo "Admin Email: $ADMIN_EMAIL"
echo "Test Email: $TEST_EMAIL"
echo ""

# Step 1: Authenticate as superuser
echo "Step 1: Authenticating as superuser..."
AUTH_RESPONSE=$(curl -s -X POST "$PB_URL/api/collections/_superusers/auth-with-password" \
    -H "Content-Type: application/json" \
    -d "{\"identity\": \"$ADMIN_EMAIL\", \"password\": \"$ADMIN_PASSWORD\"}")

TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.token // empty')

if [ -z "$TOKEN" ]; then
    echo "Failed to authenticate!"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi

echo "Authentication successful!"
echo ""

# Step 2: Get current settings to verify SMTP is configured
echo "Step 2: Checking SMTP settings..."
SETTINGS_RESPONSE=$(curl -s "$PB_URL/api/settings" \
    -H "Authorization: $TOKEN")

SMTP_ENABLED=$(echo "$SETTINGS_RESPONSE" | jq -r '.smtp.enabled // false')
SMTP_HOST=$(echo "$SETTINGS_RESPONSE" | jq -r '.smtp.host // "not configured"')

echo "SMTP Enabled: $SMTP_ENABLED"
echo "SMTP Host: $SMTP_HOST"
echo ""

if [ "$SMTP_ENABLED" != "true" ]; then
    echo "Warning: SMTP is not enabled!"
fi

# Step 3: Send test email
echo "Step 3: Sending test email to $TEST_EMAIL..."
TEST_RESPONSE=$(curl -s -X POST "$PB_URL/api/settings/test/email" \
    -H "Content-Type: application/json" \
    -H "Authorization: $TOKEN" \
    -d "{\"email\": \"$TEST_EMAIL\", \"template\": \"verification\"}")

echo "Response: $TEST_RESPONSE"
echo ""

# Check if successful (empty response means success in PocketBase)
if [ -z "$TEST_RESPONSE" ] || [ "$TEST_RESPONSE" = "{}" ]; then
    echo "SUCCESS: Test email sent! Check your inbox at $TEST_EMAIL"
else
    ERROR=$(echo "$TEST_RESPONSE" | jq -r '.message // "Unknown error"')
    echo "Failed to send test email: $ERROR"
fi
