# Toss Securities read-only realtime monitor

Status: code scaffold with offline unit tests; account credentials and static-IP authentication NOT yet connected. No fake trades, no automated orders, no buy recommendation.

Official documentation: https://p.tossinvest.com/ko/open-api ; https://developers.tossinvest.com/docs/connection ; https://developers.tossinvest.com/docs/market-data ; https://developers.tossinvest.com/docs/trade

1. In Toss Securities WTS > Settings > Open API, owner generates client_id and client_secret and registers the server's FIXED OUTBOUND PUBLIC IP in Allow IP. GitHub Pages and ordinary GitHub-hosted Actions are not stable-outbound-IP always-on servers.
2. On a dedicated Linux server with static IP, clone Ohoredingdong/Notion. Use Python 3.12+; install services/toss-live/requirements.txt in a virtual environment. Keep credentials in an OS-managed private environment/secret manager, never in files tracked by Git.
3. Required private environment variables: TOSS_CLIENT_ID, TOSS_CLIENT_SECRET, RADAR_VIEW_TOKEN (a DIFFERENT long randomly generated secret for read-only access). Optional: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID for observation alerts. Optional WS_TOPIC_LIMIT defaults 90; WATCH_THRESHOLD_PCT defaults 2; RADAR_BIND_HOST=127.0.0.1; RADAR_PORT=8777.
4. Execute python services/toss-live/worker.py with automatic restart (systemd). The worker reads the repository's stock-opportunity-data.json. Pull updated universe data and restart after changes. Reverse-proxy localhost:8777 via secured HTTPS; do not expose 8777 directly.
5. In the public toss-live-config.json set only enabled true and api_base to that HTTPS hostname. Never put Toss keys or RADAR_VIEW_TOKEN in GitHub. Open https://ohoredingdong.github.io/Notion/toss-live-radar.html and enter the separate view token for that session. Or enter the HTTPS hostname directly.
6. Check /healthz for configured, connected and count. Health does not expose credentials or price. Authenticated /api/status gives latest quotes and watch-only alert history. Telegram messages will only arrive after private configuration.

Security: Toss API credentials may permit ORDERS in other clients even though this application NEVER calls them; protect them as trading credentials. No account, holdings, personal order or condition order endpoints exist in this adapter.

One WebSocket uses trade:kr and trade:us with full-replace subscription. Keepalive is literal PING every 60 seconds, reconnect uses exponential backoff and jitter. One connection per account (avoids the account's limit 2); 90 WebSocket topics by default, remainder of the repository universe refreshed via REST every 60 seconds. REST price snapshot first seeds the baseline. Stale (>90s), future (>5s), malformed, wrong-currency, out-of-order ticks do not produce alerts. REST market data is NOT a guaranteed trade execution quote. WebSocket trades are lossy, so do not reconstruct aggregate volume by summing received messages.

The only generated signals are observation-only watch events after threshold changes SINCE WATCH START or a dated 20-session high reference; 30-minute cooldown per symbol and direction. No strict-green bypass, no actual entry-price instruction or broker order. Daily close and today's percent change are NOT inferred from watcher-start prices. Rerunning resets baseline. Alerts never include personal portfolio data. For data redistribution to third parties obtain rights/permission first.

Offline CI tests use synthetic frames only; no Toss API key, authorized IP, or account is needed. CI success is not proof of a live connection. Never label status connected before real OAuth REST and WebSocket subscription acknowledgement succeed. For production add monitoring, reconnection telemetry, server backup and official session/calendar checks.
