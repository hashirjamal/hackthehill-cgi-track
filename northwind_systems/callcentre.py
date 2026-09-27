"""SYS-05 CallCentre One (simulated). 2015, SaaS telephony + CRM, vendor Vonovia, REST API. Every call
with its agent, wrap-up code and the notes the agent typed - fast, abbreviated, inconsistent.

    uvicorn northwind_systems.callcentre:app --port 9003
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from northwind_systems.common import SIMULATED, page, query

app = FastAPI(title="CallCentre One (SYS-05)", description=SIMULATED)


@app.get("/v1/contacts/{contactId}/interactions", summary="Calls for a contact, newest first; q filters the notes")
def interactions(contactId: str, q: str | None = None, limit: int = 20):
    rows = query("callcentre", "SELECT doc FROM interactions WHERE contact_id = ? ORDER BY started_at DESC", contactId)
    if q:
        words = q.lower().split()
        rows = [r for r in rows if any(w in (r["notes"] + " " + r["wrap_code"]).lower() for w in words)]
    return {
        "contactId": contactId, "count": len(rows[:limit]),
        "data": [{
            "interactionId": f"INT-{contactId[3:]}-{i:03d}", "channel": "VOICE", "direction": "INBOUND",
            "startedAt": r["started_at"] + "Z", "durationSec": r["duration_s"], "queue": r["queue"],
            "agent": {"id": r["agent_id"], "displayName": r["agent"]}, "wrapUpCode": r["wrap_code"],
            "notes": r["notes"], "linkedRef": r["related_ref"],
        } for i, r in enumerate(rows[:limit], start=1)],
    }


STYLE = """body{font:14px system-ui,sans-serif;background:#f5f7fb;margin:0}
.top{background:#0f766e;color:#fff;padding:12px 20px;display:flex;justify-content:space-between}
.main{max-width:900px;margin:20px auto;padding:0 16px}input{padding:8px;border:1px solid #cbd5e1;border-radius:6px;width:220px}
button{padding:8px 14px;border:0;border-radius:6px;background:#0f766e;color:#fff;cursor:pointer}
.call{background:#fff;border-radius:8px;padding:12px 14px;margin:10px 0;box-shadow:0 1px 2px rgba(0,0,0,.06)}
.meta{color:#64748b;font-size:12px;display:flex;gap:14px;flex-wrap:wrap}.code{background:#ccfbf1;color:#115e59;border-radius:4px;padding:1px 6px}
.notes{margin-top:6px;font-family:ui-monospace,Menlo,monospace;font-size:13px}"""

BODY = """<div class="top"><b>CallCentre One</b><span>Agent desktop (SIMULATED)</span></div><div class="main">
<form onsubmit="go(event)"><input id="c" placeholder="Contact ID, e.g. C1-1234567" autofocus> <input id="q" placeholder="search notes (optional)"> <button>Search</button></form>
<div id="out"></div></div>
<script>
async function go(e){e.preventDefault();const c=document.getElementById('c').value.trim(),q=document.getElementById('q').value.trim(),o=document.getElementById('out');
const r=await (await fetch('v1/contacts/'+encodeURIComponent(c)+'/interactions'+(q?'?q='+encodeURIComponent(q):''))).json();
o.innerHTML='<p>'+r.count+' interaction(s)</p>'+r.data.map(i=>'<div class="call"><div class="meta"><span>'+new Date(i.startedAt).toLocaleString('en-GB')+
'</span><span>'+Math.round(i.durationSec/60)+' min</span><span>'+i.agent.displayName+' ('+i.agent.id+')</span><span class="code">'+i.wrapUpCode+'</span>'+
(i.linkedRef?'<span>ref '+i.linkedRef+'</span>':'')+'</div><div class="notes">'+i.notes+'</div></div>').join('')}
</script>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def console():
    return page("CallCentre One - Agent Desktop", STYLE, BODY)
