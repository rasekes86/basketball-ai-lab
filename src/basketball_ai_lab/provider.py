"""Key-free ESPN NBA reader with small, explicit request budget.

ESPN endpoints are public/undocumented, NOT a commercial API contract.
No retries on 429/403, no bypass, no aggressive scraping.
"""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"

class SourceError(Exception):
    pass

class Client:
    def __init__(self, fetch=None, max_calls=60, timeout=12, min_interval=0.30):
        self.fetch = fetch or self._fetch
        self.max_calls = max_calls
        self.timeout = timeout
        self.min_interval=max(0.0,float(min_interval)) if fetch is None else 0.0
        self._last_attempt=None
        self.calls = 0
        self.errors = []
        self.consecutive_failures = 0
        self.blocked_reason = None

    def _fetch(self, url):
        req=Request(url, headers={"User-Agent":"BasketballAILab/0.1 (noncommercial, low-rate)",
                                  "Accept":"application/json"})
        with urlopen(req,timeout=self.timeout) as r:
            if r.status != 200:
                raise SourceError("Respuesta HTTP inesperada")
            return json.loads(r.read(6_000_000))

    def get(self, resource, params=None):
        if self.blocked_reason:
            raise SourceError("Acceso ESPN detenido por seguridad: "+self.blocked_reason)
        if self.calls >= self.max_calls:
            raise SourceError("Cupo interno ESPN agotado; detener consultas")
        if resource not in ("scoreboard", "teams"):
            raise ValueError("Ruta no autorizada")
        url=f"{BASE}/{resource}" + ("?"+urlencode(params) if params else "")
        self.calls += 1
        if self.min_interval and self._last_attempt is not None:
            remaining=self.min_interval-(time.monotonic()-self._last_attempt)
            if remaining>0:time.sleep(remaining)
        self._last_attempt=time.monotonic()
        try:
            obj=self.fetch(url)
        except (HTTPError,URLError,TimeoutError,ValueError,OSError,SourceError) as e:
            kind=("HTTP_"+str(e.code)) if isinstance(e,HTTPError) else type(e).__name__
            self.consecutive_failures+=1
            self.errors.append({"fuente":resource,"tipo":kind})
            if isinstance(e,HTTPError) and e.code in (401,403,429):
                self.blocked_reason=kind
            elif self.consecutive_failures>=3:
                self.blocked_reason="TRES_FALLOS_CONSECUTIVOS"
            raise SourceError(f"ESPN {resource}: {kind}") from None
        self.consecutive_failures=0
        if not isinstance(obj,dict):
            self.errors.append({"fuente":resource,"tipo":"FormatoNoJSON"})
            raise SourceError("La respuesta no era un documento JSON")
        return obj

    def scoreboard(self, day):
        return self.get("scoreboard", {"dates":day.strftime("%Y%m%d"),"limit":100})

    def teams(self):
        return self.get("teams", {"limit":50})
