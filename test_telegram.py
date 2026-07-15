# ============================================================
#  TEST TELEGRAM - Verify alert system works
# ============================================================

from src.signals.alert import AlertManager

print("Testing Telegram alerts...")

alerts = AlertManager()

# Send test message
print("Sending test message...")
if alerts.send_test_message():
    print("✅ Test message sent! Check your Telegram.")
else:
    print("❌ Failed to send test message.")
    print("   Check your TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in .env")