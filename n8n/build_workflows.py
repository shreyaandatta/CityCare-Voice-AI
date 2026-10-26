"""
Write importable n8n workflow files that match the live deployment.
Code nodes are filled in from n8n/code_nodes/*.js.

After importing into your own n8n:
  1. Create the data tables CityCare_Calls and Doctors (see README) and pick them in the Data Table nodes.
  2. In "Sort by Triage", replace __SET_IN_N8N__ with your own dashboard key.
  3. Optionally add an SMTP credential to "Alert ER Desk (email)" and enable it.
"""
import json, uuid
from pathlib import Path

HERE = Path(__file__).parent
CODE = {p.name: p.read_text() for p in (HERE / "code_nodes").glob("*.js")}
CALLS_TABLE, DOCTORS_TABLE = "Eeksa088B3rNsZSx", "nQOIRVUdB9oBw0a2"   # IDs in the original instance


def nid():
    return str(uuid.uuid4())


def code(name, file, pos, mode="runOnceForEachItem"):
    return {"id": nid(), "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2, "position": pos,
            "parameters": {"mode": mode, "language": "javaScript", "jsCode": CODE[file]}}


def table_get(name, table, pos):
    return {"id": nid(), "name": name, "type": "n8n-nodes-base.dataTable", "typeVersion": 1, "position": pos,
            "alwaysOutputData": True,
            "parameters": {"resource": "row", "operation": "get", "returnAll": True,
                           "dataTableId": {"__rl": True, "mode": "id", "value": table}}}


def link(*names):
    return {a: {"main": [[{"node": b, "type": "main", "index": 0}]]} for a, b in zip(names, names[1:])}


def if_node(name, left, right, pos):
    return {"id": nid(), "name": name, "type": "n8n-nodes-base.if", "typeVersion": 2, "position": pos,
            "parameters": {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                                          "conditions": [{"id": nid(), "leftValue": left, "rightValue": right,
                                                          "operator": {"type": "string", "operation": "equals"}}],
                                          "combinator": "and"}, "options": {}}}


CAD = "$json.body.call.call_analysis.custom_analysis_data"
FIELDS = [("call_id", "string", "$json.body.call.call_id"), ("patient_name", "string", CAD + ".patient_name"),
          ("patient_phone", "string", CAD + ".patient_phone"), ("age", "number", CAD + ".age"),
          ("symptoms", "string", CAD + ".symptoms"), ("preferred_department", "string", CAD + ".preferred_department"),
          ("request_type", "string", CAD + ".request_type"), ("appointment_details", "string", CAD + ".appointment_details"),
          ("call_summary", "string", "$json.body.call.call_analysis.call_summary"),
          ("call_successful", "boolean", "$json.body.call.call_analysis.call_successful"),
          ("transcript", "string", "$json.body.call.transcript")]
P = "$('Pick Doctor & Slot').item.json"

pipeline_nodes = [
    {"id": nid(), "name": "Retell Webhook", "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 0],
     "webhookId": nid(), "parameters": {"httpMethod": "POST", "path": "retell-call", "options": {}}},
    if_node("Is Call Finished?", "={{ $json.body.event }}", "call_analyzed", [240, 0]),
    {"id": nid(), "name": "Ignore Other Events", "type": "n8n-nodes-base.noOp", "typeVersion": 1, "position": [480, 100], "parameters": {}},
    {"id": nid(), "name": "Extract Call Record", "type": "n8n-nodes-base.set", "typeVersion": 3.4, "position": [480, -100],
     "parameters": {"assignments": {"assignments": [{"id": nid(), "name": n, "type": t, "value": "={{ " + v + " }}"} for n, t, v in FIELDS]},
                    "options": {"ignoreConversionErrors": True}}},
    code("Fuzzy Triage", "fuzzy_triage.js", [720, -100]),
    code("Department Router", "department_router.js", [960, -100]),
    table_get("Load Doctors", DOCTORS_TABLE, [1200, -100]),
    code("Pick Doctor & Slot", "pick_doctor_slot.js", [1440, -100], "runOnceForAllItems"),
    {"id": nid(), "name": "Save to CityCare_Calls", "type": "n8n-nodes-base.dataTable", "typeVersion": 1, "position": [1680, -100],
     "parameters": {"dataTableId": {"__rl": True, "mode": "id", "value": CALLS_TABLE},
                    "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []}, "options": {}}},
    if_node("Is Emergency?", "={{ " + P + ".triage_label }}", "Emergency", [1920, -100]),
    {"id": nid(), "name": "Alert ER Desk (email)", "type": "n8n-nodes-base.emailSend", "typeVersion": 2.1, "position": [2160, -200],
     "disabled": True, "notes": "Add an SMTP credential and the ER desk address, then enable this node.",
     "parameters": {"fromEmail": "citycare-voice-ai@example.com", "toEmail": "er-desk@example.com", "emailFormat": "text",
                    "subject": "=EMERGENCY call: {{ " + P + ".patient_name }} (triage score {{ " + P + ".triage_score }})",
                    "text": "=Emergency call received by the voice agent.\n\n" + "\n".join(
                        f"{label}: {{{{ {P}.{field} }}}}" for label, field in
                        [("Patient", "patient_name"), ("Phone", "patient_phone"), ("Age", "age"), ("Symptoms", "symptoms"),
                         ("Triage score", "triage_score"), ("Summary", "call_summary")]), "options": {}}},
]
pipeline_conn = link("Extract Call Record", "Fuzzy Triage", "Department Router", "Load Doctors", "Pick Doctor & Slot",
                     "Save to CityCare_Calls", "Is Emergency?")
pipeline_conn["Retell Webhook"] = {"main": [[{"node": "Is Call Finished?", "type": "main", "index": 0}]]}
pipeline_conn["Is Call Finished?"] = {"main": [[{"node": "Extract Call Record", "type": "main", "index": 0}],
                                               [{"node": "Ignore Other Events", "type": "main", "index": 0}]]}
pipeline_conn["Is Emergency?"] = {"main": [[{"node": "Alert ER Desk (email)", "type": "main", "index": 0}], []]}

api_nodes = [
    {"id": nid(), "name": "Status Check", "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 0], "webhookId": nid(),
     "parameters": {"httpMethod": "POST", "path": "citycare-status", "responseMode": "lastNode", "options": {}}},
    table_get("Load Calls (status)", CALLS_TABLE, [240, 0]),
    code("Find Latest Booking", "find_booking.js", [480, 0], "runOnceForAllItems"),
    {"id": nid(), "name": "Dashboard Feed", "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 300], "webhookId": nid(),
     "parameters": {"httpMethod": "GET", "path": "citycare-calls", "responseMode": "lastNode", "options": {"allowedOrigins": "*"}}},
    table_get("Load Calls (dashboard)", CALLS_TABLE, [240, 300]),
    code("Sort by Triage", "dashboard_feed.js", [480, 300], "runOnceForAllItems"),
]
api_conn = {**link("Status Check", "Load Calls (status)", "Find Latest Booking"),
            **link("Dashboard Feed", "Load Calls (dashboard)", "Sort by Triage")}

for fname, name, nodes, conn in [
        ("workflow_call_pipeline.json", "CityCare Hospital - Voice AI Call Pipeline", pipeline_nodes, pipeline_conn),
        ("workflow_status_api.json", "CityCare Hospital - Status & Dashboard API", api_nodes, api_conn)]:
    (HERE / fname).write_text(json.dumps({"name": name, "nodes": nodes, "connections": conn,
                                          "settings": {"executionOrder": "v1"}}, indent=2))
    print("wrote", fname)
