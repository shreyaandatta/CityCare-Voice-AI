// n8n Code node ("Run Once for All Items") behind the /citycare-status webhook.
// Retell's custom function sends {args: {phone}}; also accepts ?phone= for testing.
// Returns only appointment details – never symptoms or transcripts.
const req = $('Status Check').first().json;
const raw = req.body?.args?.phone || req.body?.phone || req.query?.phone || '';
const phone = String(raw).replace(/\D/g, '').slice(-10);
const rows = $input.all().map(i => i.json).filter(r => r.patient_phone);
const match = rows
  .filter(r => phone.length >= 6 && String(r.patient_phone).replace(/\D/g, '').slice(-10) === phone)
  .sort((a, b) => (b.id || 0) - (a.id || 0))[0];

if (!match) {
  return [{ json: { found: false, message: 'I could not find any appointment for that number. Would you like to book one?' } }];
}
const message = match.booking_status === 'ER alerted'
  ? `This was handled as an emergency for ${match.patient_name}. Please contact the Emergency department directly.`
  : match.doctor
    ? `${match.patient_name}'s appointment is with ${match.doctor} (${match.department}) on ${match.appointment_slot}. Status: ${match.booking_status}.`
    : `I found a request for ${match.patient_name}. Status: ${match.booking_status}.`;
return [{ json: { found: true, message } }];
