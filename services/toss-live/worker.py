"""Read-only Toss REST/WebSocket monitor. Requires user-owned API keys and a fixed allowlisted IP."""
from __future__ import annotations
import asyncio, json, logging, os, random, sys
from pathlib import Path
from urllib.parse import urlsplit
from aiohttp import ClientSession, ClientTimeout, WSMsgType, web
from core import WatchEngine, normalize_universe, subscription_rows, quote_from_rest, quote_from_trade, parse_time, utcnow

ROOT = Path(__file__).resolve().parents[2]
REST = "https://openapi.tossinvest.com"
WS = "wss://openapi-ws.tossinvest.com/ws/v1"
ORIGIN = "https://ohoredingdong.github.io"
LOG = logging.getLogger("toss-live")
# No account endpoints. No orders, conditional orders, or holdings endpoints.
REST_READ_PATHS = frozenset({"/api/v1/prices"})

class TossReadOnly:
    def __init__(self, session, client_id, client_secret):
        self.session, self.client_id, self.client_secret = session, client_id, client_secret
        self.token, self.expires = None, 0.0
    async def access_token(self):
        if self.token and asyncio.get_running_loop().time() < self.expires-180:
            return self.token
        async with self.session.post(REST+"/oauth2/token", data={
                "client_id":self.client_id, "client_secret":self.client_secret,
                "grant_type":"client_credentials"}, timeout=ClientTimeout(total=12)) as response:
            if response.status != 200:
                # Never output response body; it might contain sensitive information.
                raise RuntimeError("Toss OAuth2 failed HTTP "+str(response.status))
            body = await response.json()
        token = body.get("access_token")
        if not isinstance(token,str) or not token:
            raise RuntimeError("Toss OAuth2 missing token")
        self.token, self.expires = token, asyncio.get_running_loop().time()+max(300,int(body.get("expires_in") or 3600))
        return token
    async def prices(self, symbols):
        path="/api/v1/prices"
        assert path in REST_READ_PATHS
        token=await self.access_token()
        results=[]
        for i in range(0,len(symbols),40):
            chunk=symbols[i:i+40]
            async with self.session.get(REST+path, params={"symbols":",".join(chunk)},
                                        headers={"Authorization":"Bearer "+token},
                                        timeout=ClientTimeout(total=12)) as response:
                if response.status == 429:
                    raise RuntimeError("Toss price rate limit")
                if response.status != 200:
                    raise RuntimeError("Toss price HTTP "+str(response.status))
                data = (await response.json()).get("result") or []
                if not isinstance(data,list):
                    raise ValueError("Toss price array invalid")
                for x in data:
                    q=quote_from_rest(x)
                    if q: results.append(q)
        return results

def cors_headers(request):
    result={"Cache-Control":"no-store", "Vary":"Origin"}
    if request.headers.get("Origin")==ORIGIN:
        result.update({"Access-Control-Allow-Origin":ORIGIN,
                       "Access-Control-Allow-Headers":"Authorization, Content-Type",
                       "Access-Control-Allow-Methods":"GET, OPTIONS"})
    return result

class LiveApp:
    def __init__(self, rows, config):
        self.config=config
        self.rows=rows
        self.engine=WatchEngine(rows, threshold_pct=float(config.get("WATCH_THRESHOLD_PCT","2")))
        self.declared, self.fallback=subscription_rows(rows,max_topics=int(config.get("WS_TOPIC_LIMIT","90")))
        self.ws_count=sum(len(x["codes"]) for x in self.declared)
        self.source_state="not_configured"
        self.connected=False
        self.tasks=[]
        self.session=None
        self.broker=None
    def ready(self):
        return bool(self.config.get("TOSS_CLIENT_ID") and self.config.get("TOSS_CLIENT_SECRET"))
    async def notify(self, event):
        token=self.config.get("TELEGRAM_BOT_TOKEN")
        chat=self.config.get("TELEGRAM_CHAT_ID")
        if not token or not chat: return
        text="🔎 투자 레이더 관찰 · 매수 추천 아님\n"+event["name"]+" ("+event["symbol"]+")\n"
        text+=("가격 "+str(event["price"])+" "+event["currency"]+"\n")
        text+="\n".join(event["reasons"])+"\n시세 기준: "+event["timestamp"]+"\n"
        text+="검증되지 않은 관찰 신호이며 주문은 실행하지 않습니다."
        try:
            # Telegram token is only passed to the HTTPS request, NEVER logs or public JSON.
            async with self.session.post("https://api.telegram.org/bot"+token+"/sendMessage",
                    json={"chat_id":chat,"text":text},timeout=ClientTimeout(total=10)) as res:
                if res.status != 200: LOG.warning("Notification delivery HTTP %s",res.status)
        except Exception:
            LOG.warning("Notification delivery failed (details suppressed)")
    def accept(self, q):
        event=self.engine.ingest(q)
        if event:
            asyncio.create_task(self.notify(event))
    async def poll(self):
        # REST initial snapshots also cover the <100 WS subscription overflow.
        while True:
            try:
                quotes=await self.broker.prices([r["symbol"] for r in self.rows])
                for q in quotes: self.accept(q)
                if not self.connected:
                    self.source_state="rest_only"
            except Exception as exc:
                self.source_state="source_error" if not self.connected else "ws_live_rest_degraded"
                LOG.warning("REST market refresh failed: %s",type(exc).__name__)
            await asyncio.sleep(60)
    async def _keepalive(self,ws):
        while not ws.closed:
            await asyncio.sleep(60)
            if not ws.closed: await ws.send_str("PING")
    async def watch(self):
        attempt=0
        while True:
            try:
                token=await self.broker.access_token()
                async with self.session.ws_connect(WS,headers={"Authorization":"Bearer "+token},
                           heartbeat=None,receive_timeout=220,timeout=ClientTimeout(total=18)) as ws:
                    self.connected=False
                    self.source_state="subscribing"
                    await ws.send_str(json.dumps(self.declared,ensure_ascii=False))
                    keep=asyncio.create_task(self._keepalive(ws))
                    try:
                        async for frame in ws:
                            if frame.type==WSMsgType.TEXT:
                                if frame.data=="PING": await ws.send_str("PING");continue
                                try: msg=json.loads(frame.data)
                                except (ValueError,TypeError): continue
                                tp=msg.get("type")
                                if tp=="subscriptions":
                                    subscribed=msg.get("subscribed") or []
                                    rejected=msg.get("rejected") or []
                                    self.connected=bool(subscribed)
                                    self.source_state="ws_live" if self.connected else "subscription_rejected"
                                    if rejected:
                                        # Rejected names are diagnostic only; do not retry rapidly.
                                        LOG.warning("WebSocket subscription rejected %d items",len(rejected))
                                    attempt=0
                                elif tp=="message":
                                    q=quote_from_trade(msg)
                                    if q: self.accept(q)
                                elif tp=="error":
                                    LOG.warning("WebSocket protocol error: %s",str((msg.get("error") or {}).get("code","unknown"))[:50])
                                    if (msg.get("error") or {}).get("code")=="server-shutdown": break
                            elif frame.type in (WSMsgType.CLOSED,WSMsgType.CLOSE,WSMsgType.ERROR):
                                break
                    finally:
                        keep.cancel()
                        await asyncio.gather(keep,return_exceptions=True)
            except Exception as exc:
                LOG.warning("WebSocket unavailable: %s",type(exc).__name__)
                self.source_state="ws_disconnected"
            self.connected=False
            attempt+=1
            await asyncio.sleep(min(60,2**min(attempt,6))+random.random())
    async def start(self,app):
        self.session=ClientSession(timeout=ClientTimeout(total=15),trust_env=False)
        if self.ready():
            self.broker=TossReadOnly(self.session,self.config["TOSS_CLIENT_ID"],self.config["TOSS_CLIENT_SECRET"])
            self.source_state="connecting"
            self.tasks=[asyncio.create_task(self.poll()),asyncio.create_task(self.watch())]
        else:
            self.source_state="not_configured"
    async def stop(self,app):
        for t in self.tasks: t.cancel()
        if self.tasks: await asyncio.gather(*self.tasks,return_exceptions=True)
        if self.session: await self.session.close()

def make_webapp(state):
    app=web.Application()
    app["live_state"]=state
    async def health(request):
        return web.json_response({
            "status":state.source_state,"configured":state.ready(),"connected":state.connected,
            "watch_count":len(state.rows),"live_buy_recommendations":0,
        },headers=cors_headers(request))
    async def preflight(request):
        return web.Response(status=204,headers=cors_headers(request))
    async def status(request):
        expected=state.config.get("RADAR_VIEW_TOKEN","")
        if not expected:
            return web.json_response({"error":"view_token_not_configured"},status=503,headers=cors_headers(request))
        import hmac
        supplied=request.headers.get("Authorization","")
        if not hmac.compare_digest(supplied,"Bearer "+expected):
            return web.json_response({"error":"access_denied"},status=401,headers=cors_headers(request))
        return web.json_response(state.engine.status(state.connected,state.source_state,state.ws_count,len(state.fallback)),
                                 headers=cors_headers(request))
    app.router.add_get("/healthz",health)
    app.router.add_route("OPTIONS","/api/status",preflight)
    app.router.add_get("/api/status",status)
    app.on_startup.append(state.start)
    app.on_cleanup.append(state.stop)
    return app

def main():
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    raw=json.loads((ROOT/"stock-opportunity-data.json").read_text(encoding="utf-8"))
    rows=normalize_universe(raw)
    if not rows:
        raise RuntimeError("No real source symbols; refusing to start with example prices")
    config=dict(os.environ)
    state=LiveApp(rows,config)
    LOG.info("Toss read-only worker initialized: %d covered, %d WS topics, %d REST overflow; credential configured=%s",
             len(rows),state.ws_count,len(state.fallback),state.ready())
    # Bind localhost by default. HTTPS reverse proxy must perform TLS and restrict access.
    web.run_app(make_webapp(state),host=config.get("RADAR_BIND_HOST","127.0.0.1"),port=int(config.get("RADAR_PORT","8777")))

if __name__=="__main__":
    main()
