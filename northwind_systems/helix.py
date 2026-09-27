"""SYS-02 Helix CIS (simulated). 2004, Oracle Forms / Oracle 11g, vendor Helix Systems. The system of
record for account data, for every region - and so the one place that knows each customer's ids in
the other systems. Billing for the four new-stack regions (Aurora bills Barrowdale and Dunmoor).

    uvicorn northwind_systems.helix:app --port 9005
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from northwind_systems.common import SIMULATED, page, query

app = FastAPI(title="Helix CIS (SYS-02)", description=SIMULATED)


def _customer(c: dict) -> dict:
    return {
        "customerId": c["helix_id"],
        "accountRef": c["account_id"],
        "name": {"title": c["title"], "given": c["first_name"], "family": c["last_name"]},
        "address": {"line1": c["address"], "postcode": c["postcode"], "region": c["region"]},
        "contact": {"mobile": c["phone"], "email": c["email"]},
        "customerSince": c["customer_since"],
        "paymentMethod": c["payment_method"],
        "priorityServicesRegister": [{"need": n, "registered": True} for n in c["psr_needs"]],
        "balance": {"arrears": c["arrears"], "currency": "GBP"},
        "paymentArrangement": c["payment_plan"],
        "billingSystem": "AURORA" if c["aurora_acct_no"] else "HELIX",
        # Cross-references: the only place that joins a customer up across the estate.
        "externalIds": {
            "auroraAcctNo": c["aurora_acct_no"], "callCentreOneContactId": c["crm_contact_id"],
            "caseTrackPartyId": c["casetrack_party_id"], "connectUserId": c["connect_user_id"],
        },
    }


@app.get("/helix/api/v2/customers", summary="Find a customer by Northwind account reference")
def find_customer(accountRef: str):
    rows = query("helix", "SELECT doc FROM customers WHERE account_ref = ?", accountRef)
    if not rows:
        raise HTTPException(404, {"errorCode": "HX-404-CUST", "message": f"No customer with accountRef {accountRef}"})
    return _customer(rows[0])


@app.get("/helix/api/v2/customers/{customerId}/invoices", summary="Invoices (new-stack regions only)")
def invoices(customerId: str, limit: int = 12):
    rows = query("helix", "SELECT doc FROM invoices WHERE helix_id = ?", customerId)
    rows = sorted(rows, key=lambda b: b["issued"], reverse=True)[:limit]
    return {
        "customerId": customerId,
        "invoices": [{
            "invoiceNo": f"INV-{customerId[3:]}-{b['seq']:03d}", "issuedOn": b["issued"],
            "period": {"from": b["period_from"], "to": b["period_to"]}, "readingType": b["read_type"],
            "meterReading": {"previous": b["previous_reading"], "current": b["reading"]},
            "consumptionKwh": b["units_kwh"], "amountDue": {"value": b["amount"], "currency": "GBP"},
            "status": b["status"], "tariff": b["tariff"],
        } for b in rows],
    }


STYLE = """body{background:#d4d0c8;font:12px Tahoma,Verdana,sans-serif;margin:0}
.bar{background:linear-gradient(#0a246a,#3a6ea5);color:#fff;font-weight:bold;padding:4px 8px}
.win{margin:16px;border:2px outset #fff;background:#d4d0c8}.inner{padding:10px}
label{display:inline-block;width:130px}input{font:12px Tahoma;border:2px inset #fff;padding:2px;width:160px}
button{font:12px Tahoma;border:2px outset #fff;background:#d4d0c8;padding:2px 12px;cursor:pointer}
fieldset{border:1px solid #808080;margin:10px 0}legend{color:#0a246a;font-weight:bold}
table{border-collapse:collapse;background:#fff;width:100%}td,th{border:1px solid #a0a0a0;padding:3px 6px;text-align:left}
th{background:#ece9d8}.ro{background:#fff;border:1px inset #aaa;padding:2px 4px;display:inline-block;min-width:160px}
.foot{font-size:11px;color:#444;padding:4px 10px;border-top:1px solid #aaa}"""

BODY = """<div class="win"><div class="bar">Helix CIS 4.2 - Customer Maintenance [CUSTMNT01] &nbsp; (SIMULATED)</div><div class="inner">
<form onsubmit="go(event)"><label>Account Ref:</label><input id="a" placeholder="ACC-000000" autofocus> <button>Query</button></form>
<div id="out"></div></div><div class="foot">Oracle Forms Runtime &nbsp;|&nbsp; Record: 1/1 &nbsp;|&nbsp; &lt;OSC&gt;</div></div>
<script>
const f=(l,v)=>'<div><label>'+l+'</label><span class="ro">'+(v??'')+'</span></div>';
async function go(e){e.preventDefault();const a=document.getElementById('a').value.trim(),o=document.getElementById('out');
const r=await fetch('helix/api/v2/customers?accountRef='+encodeURIComponent(a));if(!r.ok){o.innerHTML='<p>FRM-40350: Query caused no records to be retrieved.</p>';return}
const c=await r.json();let h='<fieldset><legend>Customer</legend>'+f('Customer Id',c.customerId)+f('Name',c.name.title+' '+c.name.given+' '+c.name.family)+
f('Address',c.address.line1+', '+c.address.postcode)+f('Region',c.address.region)+f('Customer since',c.customerSince)+f('Payment method',c.paymentMethod)+'</fieldset>'+
'<fieldset><legend>Account</legend>'+f('Arrears (GBP)',c.balance.arrears.toFixed(2))+f('Arrangement',c.paymentArrangement?c.paymentArrangement.status+' @ '+c.paymentArrangement.agreed_monthly+'/mth':'None')+
f('PSR',c.priorityServicesRegister.map(p=>p.need).join('; ')||'None')+f('Billing system',c.billingSystem)+'</fieldset>'+
'<fieldset><legend>External references</legend>'+Object.entries(c.externalIds).map(([k,v])=>f(k,v||'-')).join('')+'</fieldset>';
if(c.billingSystem==='HELIX'){const inv=await (await fetch('helix/api/v2/customers/'+c.customerId+'/invoices')).json();
h+='<fieldset><legend>Invoices</legend><table><tr><th>Invoice</th><th>Issued</th><th>Reading</th><th>kWh</th><th>Amount</th><th>Status</th></tr>'+
inv.invoices.map(i=>'<tr><td>'+i.invoiceNo+'</td><td>'+i.issuedOn+'</td><td>'+i.readingType+'</td><td>'+i.consumptionKwh+'</td><td>'+i.amountDue.value.toFixed(2)+'</td><td>'+i.status+'</td></tr>').join('')+'</table></fieldset>'}
o.innerHTML=h}
</script>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def console():
    return page("Helix CIS - CUSTMNT01", STYLE, BODY)
