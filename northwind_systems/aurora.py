"""SYS-01 Aurora Billing (simulated). 1998, COBOL / DB2 on the mainframe, exposed through CICS-style
transactions. Serves Barrowdale and Dunmoor only. Everything is upper case, amounts are in pence,
dates are YYYYMMDD and read types are single letters (A actual, E estimated, C correction).

    uvicorn northwind_systems.aurora:app --port 9001
"""
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from northwind_systems.common import SIMULATED, page, query

app = FastAPI(title="Aurora Billing (SYS-01)", description=SIMULATED)

_READ = {"ACTUAL": "A", "ESTIMATED": "E", "CORRECTION": "C"}
_STATUS = {"PAID": "PD", "OVERDUE": "OS", "DISPUTED": "DS", "CREDITED": "CR"}


def _d(iso: str | None) -> str:
    return iso.replace("-", "")[:8] if iso else "00000000"


def _bill(b: dict) -> dict:
    return {
        "BILL-SEQ": f"{b['seq']:04d}", "BILL-DT": _d(b["issued"]), "PRD-FROM": _d(b["period_from"]),
        "PRD-TO": _d(b["period_to"]), "RD-TYP": _READ[b["read_type"]],
        "PREV-RDG": f"{b['previous_reading'] or 0:07d}", "CURR-RDG": f"{b['reading'] or 0:07d}",
        "UNITS": f"{b['units_kwh']:06d}", "AMT-DUE-P": f"{round(b['amount'] * 100):+09d}",
        "TRF-CD": b["tariff"], "PAY-STS": _STATUS[b["status"]],
    }


@app.get("/cics/AURB0100", summary="Account inquiry")
def account_inquiry(ACCTNO: str):
    time.sleep(0.4)  # the mainframe round trip
    rows = query("aurora", "SELECT doc FROM accounts WHERE acct_no = ?", ACCTNO)
    if not rows:
        raise HTTPException(404, {"AURB0100-RESP": {"RC": "13", "MSG": "ACCT NOT FOUND"}})
    a = rows[0]
    return {"AURB0100-RESP": {
        "RC": "00", "ACCT-NO": ACCTNO, "CUST-NM": f"{a['last_name'].upper()} {a['first_name'][0]}",
        "ADDR-1": a["address"].upper(), "PSTCD": a["postcode"], "BAL-P": f"{round(a['arrears'] * 100):09d}",
        "ARR-FLG": "Y" if a["arrears"] > 0 else "N", "PP-IND": "Y" if a["payment_plan"] else "N",
        "PAY-MTHD": {"Direct Debit": "DD", "Payment card": "CC", "Cash / PayPoint": "PP"}[a["payment_method"]],
    }}


@app.get("/cics/AURB0200", summary="Bill history")
def bill_history(ACCTNO: str, CNT: int = 12):
    time.sleep(0.4)
    bills = query("aurora", "SELECT doc FROM bills WHERE acct_no = ?", ACCTNO)
    if not bills:
        raise HTTPException(404, {"AURB0200-RESP": {"RC": "13", "MSG": "NO BILLS FOR ACCT"}})
    bills = sorted(bills, key=lambda b: b["issued"], reverse=True)[:CNT]
    return {"AURB0200-RESP": {"RC": "00", "ACCT-NO": ACCTNO, "BILL-CNT": f"{len(bills):03d}", "BILLS": [_bill(b) for b in bills]}}


STYLE = """body{background:#000;color:#33ff33;font:15px/1.35 'Courier New',monospace;margin:0;padding:24px}
.hdr{border-bottom:1px solid #33ff33;padding-bottom:6px;margin-bottom:14px;display:flex;justify-content:space-between}
input{background:#000;color:#33ff33;border:none;border-bottom:1px solid #33ff33;font:inherit;width:12ch;outline:none}
button{background:#33ff33;color:#000;border:none;font:inherit;padding:0 8px;cursor:pointer}
pre{white-space:pre;overflow-x:auto;margin:14px 0}.dim{color:#1f991f}.warn{color:#ffcc00}"""

BODY = """<div class="hdr"><span>AURORA BILLING SYSTEM  -  AURB  -  REGION: BARROWDALE/DUNMOOR</span><span class="dim">SIMULATED</span></div>
<div>TRANSACTION: AURB0200  BILL HISTORY INQUIRY</div><br>
<form onsubmit="go(event)">ACCT-NO ===> <input id="a" placeholder="0000000000" autofocus> <button>ENTER</button></form>
<pre id="out" class="dim">ENTER 10-DIGIT ACCOUNT NUMBER AND PRESS ENTER.
PF3=EXIT  PF7=BKWD  PF8=FWD  PF12=CANCEL</pre>
<script>
async function go(e){e.preventDefault();const a=document.getElementById('a').value.trim();const o=document.getElementById('out');
o.textContent='PROCESSING...';const [r1,r2]=await Promise.all([fetch('cics/AURB0100?ACCTNO='+a),fetch('cics/AURB0200?ACCTNO='+a)]);
if(!r1.ok){o.innerHTML='<span class="warn">RC=13 ACCT NOT FOUND</span>';return}
const acc=(await r1.json())['AURB0100-RESP'],b=(await r2.json())['AURB0200-RESP'];
let s='ACCT-NO: '+acc['ACCT-NO']+'   CUST-NM: '+acc['CUST-NM']+'\\nADDR   : '+acc['ADDR-1']+', '+acc['PSTCD']+
'\\nBAL-P  : '+acc['BAL-P']+'   ARR-FLG: '+acc['ARR-FLG']+'   PP-IND: '+acc['PP-IND']+'   PAY: '+acc['PAY-MTHD']+'\\n\\n'+
'SEQ  BILL-DT   RD PREV-RDG CURR-RDG  UNITS   AMT-DUE-P  TRF-CD      STS\\n'+'-'.repeat(72)+'\\n';
for(const x of b.BILLS){s+=[x['BILL-SEQ'],x['BILL-DT'],' '+x['RD-TYP'],x['PREV-RDG'],x['CURR-RDG'],x.UNITS,' '+x['AMT-DUE-P'],' '+x['TRF-CD'].padEnd(11),x['PAY-STS']].join(' ')+'\\n'}
o.textContent=s+'\\nRD: A=ACTUAL E=ESTIMATED C=CORRECTION   STS: PD OS DS CR';o.className='';}
</script>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def console():
    return page("AURORA - AURB0200", STYLE, BODY)
