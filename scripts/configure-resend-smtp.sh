#!/bin/bash

# Configure Resend SMTP for PocketBase
# Resend uses SMTP on smtp.resend.com:465 (TLS)

# Configuration
PB_URL="${PB_URL:-http://localhost:8090}"
RESEND_API_KEY="${RESEND_API_KEY:-re_62RzDBVK_QKdUqGudDm4qppV4PxEEqLBG}"

echo "Configuring Resend SMTP for PocketBase..."
echo "PocketBase URL: $PB_URL"

# First, we need admin authentication
# Check if we have admin credentials
if [ -z "$PB_ADMIN_EMAIL" ] || [ -z "$PB_ADMIN_PASSWORD" ]; then
    echo ""
    echo "Note: To configure SMTP via API, you need admin credentials."
    echo "Set PB_ADMIN_EMAIL and PB_ADMIN_PASSWORD environment variables."
    echo ""
    echo "Alternatively, configure SMTP manually in PocketBase Admin UI:"
    echo "  1. Go to $PB_URL/_/"
    echo "  2. Navigate to Settings > Mail settings"
    echo "  3. Configure:"
    echo "     - SMTP Host: smtp.resend.com"
    echo "     - SMTP Port: 465"
    echo "     - Use TLS: Yes"
    echo "     - Username: resend"
    echo "     - Password: $RESEND_API_KEY"
    echo "     - Sender Address: onboarding@resend.dev (or your verified domain)"
    echo ""
    exit 0
fi

# Authenticate as admin
echo "Authenticating as admin..."
AUTH_RESPONSE=$(curl -s -X POST "$PB_URL/api/admins/auth-with-password" \
    -H "Content-Type: application/json" \
    -d "{
        \"identity\": \"$PB_ADMIN_EMAIL\",
        \"password\": \"$PB_ADMIN_PASSWORD\"
    }")

TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.token // empty')

if [ -z "$TOKEN" ]; then
    echo "Failed to authenticate. Response: $AUTH_RESPONSE"
    exit 1
fi

echo "Authenticated successfully!"

# Update SMTP settings
echo "Updating SMTP settings..."
SETTINGS_RESPONSE=$(curl -s -X PATCH "$PB_URL/api/settings" \
    -H "Content-Type: application/json" \
    -H "Authorization: $TOKEN" \
    -d "{
        \"smtp\": {
            \"enabled\": true,
            \"host\": \"smtp.resend.com\",
            \"port\": 465,
            \"tls\": true,
            \"authMethod\": \"PLAIN\",
            \"username\": \"resend\",
            \"password\": \"$RESEND_API_KEY\"
        },
        \"meta\": {
            \"senderName\": \"OrgMeet\",
            \"senderAddress\": \"onboarding@resend.dev\"
        }
    }")

echo "Settings response: $SETTINGS_RESPONSE"

# Test email
echo ""
echo "Testing email configuration..."
TEST_RESPONSE=$(curl -s -X POST "$PB_URL/api/settings/test/email" \
    -H "Content-Type: application/json" \
    -H "Authorization: $TOKEN" \
    -d "{
        \"email\": \"$PB_ADMIN_EMAIL\",
        \"template\": \"verification\"
    }")

echo "Test response: $TEST_RESPONSE"
echo ""
echo "Done! Check your email for the test message."
