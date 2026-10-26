// n8n Code node ("Run Once for All Items") behind the /citycare-calls webhook used by the staff dashboard.
// The caller must send header x-dashboard-key matching DASHBOARD_KEY (set in the live workflow, not in git).
const DASHBOARD_KEY = '__SET_IN_N8N__';
const headers = $('Dashboard Feed').first().json.headers || {};
if (headers['x-dashboard-key'] !== DASHBOARD_KEY) {
  return [{ json: { error: 'unauthorized' } }];
}
const calls = $input.all().map(i => i.json).filter(r => r.call_id)
  .sort((a, b) => (b.triage_score || 0) - (a.triage_score || 0) || (b.id || 0) - (a.id || 0))
  .map(({ transcript, ...rest }) => rest);
return [{ json: { generated_at: new Date().toISOString(), count: calls.length, calls } }];
