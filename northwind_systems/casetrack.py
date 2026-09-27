"""SYS-04 CaseTrack (simulated). 2011, Java / SQL Server, vendor CaseTrack Ltd. The complaint and case
system. Cases transferred in from other channels arrive by nightly batch and lose their history.

    uvicorn northwind_systems.casetrack:app --port 9002
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from northwind_systems.common import SIMULATED, page, query

app = FastAPI(title="CaseTrack (SYS-04)", description=SIMULATED)


def _case(c: dict) -> dict:
    return {
        "caseRef": c["case_ref"], "externalRef": c["external_ref"], "openedDate": c["opened"],
        "caseType": c["category"].upper().replace(" - ", "_").replace(" ", "_"), "caseStatus": c["status"].upper(),
        "ownerQueue": c["owner_team"], "originSystem": c["origin_system"], "importedViaBatch": c["transferred"],
        "activity": [{"timestamp": e["at"], "activityType": e["type"], "user": e["by"], "text": e["note"]} for e in c["events"]],
    }


@app.get("/casetrack/rest/v1/cases", summary="Cases for a party, or by external (Northwind) reference")
def cases(partyId: str | None = None, externalRef: str | None = None):
    if partyId:
        rows = query("casetrack", "SELECT doc FROM cases WHERE party_id = ? ORDER BY case_ref", partyId)
    elif externalRef:
        rows = query("casetrack", "SELECT doc FROM cases WHERE external_ref = ?", externalRef)
    else:
        raise HTTPException(400, {"error": "partyId or externalRef required"})
    return {"totalCount": len(rows), "cases": [_case(c) for c in rows]}


STYLE = """body{font:13px Arial,sans-serif;background:#eef1f5;margin:0;color:#222}
.top{background:#5b2c6f;color:#fff;padding:10px 16px;font-size:16px}.top small{opacity:.7;margin-left:10px}
.nav{background:#e6dcea;padding:6px 16px;border-bottom:1px solid #c9b8d3;color:#5b2c6f}
.main{padding:16px}input{padding:4px;border:1px solid #999;width:180px}button{padding:4px 10px;background:#5b2c6f;color:#fff;border:0;cursor:pointer}
.case{background:#fff;border:1px solid #ccc;margin:12px 0}.ch{background:#f4eef7;padding:8px 10px;border-bottom:1px solid #ddd;font-weight:bold}
table{border-collapse:collapse;width:100%}td{border-top:1px solid #eee;padding:5px 10px;vertical-align:top}
.t{white-space:nowrap;color:#666;width:150px}.u{color:#5b2c6f;width:110px}.imp{background:#fff4d6}"""

BODY = """<div class="top">CaseTrack Enterprise 7.3<small>Customer Operations (SIMULATED)</small></div>
<div class="nav">Home &rsaquo; Cases &rsaquo; Search</div><div class="main">
<form onsubmit="go(event)">Party ID: <input id="p" placeholder="P000000" autofocus> <button>Search</button></form><div id="out"></div></div>
<script>
async function go(e){e.preventDefault();const p=document.getElementById('p').value.trim(),o=document.getElementById('out');
const r=await (await fetch('casetrack/rest/v1/cases?partyId='+encodeURIComponent(p))).json();
if(!r.totalCount){o.innerHTML='<p>No cases found.</p>';return}
o.innerHTML='<p>'+r.totalCount+' case(s)</p>'+r.cases.map(c=>'<div class="case"><div class="ch">'+c.caseRef+' &middot; '+c.caseType+' &middot; '+c.caseStatus+
' &middot; Queue: '+c.ownerQueue+' &middot; Ext: '+c.externalRef+'</div><table>'+c.activity.map(a=>'<tr class="'+(a.activityType==='IMPORTED'?'imp':'')+
'"><td class="t">'+a.timestamp.replace('T',' ').slice(0,16)+'</td><td class="u">'+a.user+'</td><td>'+a.activityType+': '+a.text+'</td></tr>').join('')+'</table></div>').join('')}
</script>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def console():
    return page("CaseTrack - Case Search", STYLE, BODY)
