"""SYS-03 Northwind Connect (simulated). 2019, React / Node / Postgres, the customer web and app portal.
Only about a third of customers are registered. Holds what customers wrote to us and the meter
readings they submitted themselves - which nothing downstream ever picks up.

    uvicorn northwind_systems.connect:app --port 9004
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from northwind_systems.common import SIMULATED, page, query

app = FastAPI(title="Northwind Connect (SYS-03)", description=SIMULATED)


def _user(user_id: str) -> dict:
    rows = query("connect", "SELECT doc FROM users WHERE user_id = ?", user_id)
    if not rows:
        raise HTTPException(404, {"error": "user_not_found"})
    return rows[0]


@app.get("/api/v1/users/{userId}/messages", summary="Messages the customer sent through the portal")
def messages(userId: str):
    u = _user(userId)
    return {"userId": userId, "registeredAt": u["registered_on"], "lastLoginAt": u["last_login"],
            "messages": [{"sentAt": m["sent_at"], "subject": m["subject"], "body": m["body"],
                          "attachments": [{"type": "image/jpeg", "name": "meter.jpg"}] if m["has_attachment"] else []}
                         for m in sorted(u["messages"], key=lambda m: m["sent_at"], reverse=True)]}


@app.get("/api/v1/users/{userId}/meter-readings", summary="Meter readings the customer submitted")
def meter_readings(userId: str):
    u = _user(userId)
    return {"userId": userId, "readings": [{"submittedAt": r["submitted_at"], "value": r["reading"], "photo": r["photo"],
                                            "processingStatus": r["status"]} for r in u["meter_readings"]]}


STYLE = """body{font:15px -apple-system,Segoe UI,Roboto,sans-serif;background:#fafafa;margin:0;color:#111}
.top{background:#fff;border-bottom:1px solid #eee;padding:14px 24px;display:flex;align-items:center;gap:10px}
.logo{width:26px;height:26px;border-radius:8px;background:linear-gradient(135deg,#6366f1,#22d3ee)}
.main{max-width:760px;margin:24px auto;padding:0 16px}input{padding:10px 12px;border:1px solid #ddd;border-radius:10px;width:260px}
button{padding:10px 16px;border:0;border-radius:10px;background:#4f46e5;color:#fff;cursor:pointer}
.card{background:#fff;border:1px solid #eee;border-radius:14px;padding:14px 16px;margin:12px 0}
.muted{color:#888;font-size:13px}.pill{background:#fef3c7;color:#92400e;border-radius:99px;padding:2px 8px;font-size:12px}"""

BODY = """<div class="top"><div class="logo"></div><b>Northwind Connect</b><span class="muted">Admin view (SIMULATED)</span></div><div class="main">
<form onsubmit="go(event)"><input id="u" placeholder="User ID, e.g. nwc_ab12cd34ef" autofocus> <button>Open</button></form><div id="out"></div></div>
<script>
async function go(e){e.preventDefault();const u=document.getElementById('u').value.trim(),o=document.getElementById('out');
const r=await fetch('api/v1/users/'+encodeURIComponent(u)+'/messages');if(!r.ok){o.innerHTML='<p class="muted">No registered user.</p>';return}
const m=await r.json(),rd=await (await fetch('api/v1/users/'+encodeURIComponent(u)+'/meter-readings')).json();
o.innerHTML='<p class="muted">Registered '+m.registeredAt+' &middot; last login '+m.lastLoginAt+'</p><h3>Messages</h3>'+
(m.messages.map(x=>'<div class="card"><div class="muted">'+new Date(x.sentAt).toLocaleString('en-GB')+' &middot; '+x.subject+(x.attachments.length?' &middot; 📎 meter.jpg':'')+'</div><p>'+x.body+'</p></div>').join('')||'<p class="muted">None</p>')+
'<h3>Submitted meter readings</h3>'+(rd.readings.map(x=>'<div class="card">'+x.value+' <span class="muted">'+new Date(x.submittedAt).toLocaleString('en-GB')+'</span> <span class="pill">'+x.processingStatus+'</span></div>').join('')||'<p class="muted">None</p>')}
</script>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def console():
    return page("Northwind Connect - Admin", STYLE, BODY)
