// n8n Code node ("Run Once for All Items").
// Input items: every row of the Doctors data table. The call comes from the router node.
// Picks the earliest free day for a doctor in the routed department and builds the record to save.
const call = $('Department Router').first().json;
const doctors = $input.all().map(i => i.json).filter(d => d.department === call.department);
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const now = DateTime.now().setZone('Asia/Kolkata');

let doctor = '', appointment_slot = '', booking_status = 'Pending confirmation';
const wantsBooking = !/status|enquiry/i.test(call.request_type || '') || (call.symptoms || '').trim() !== '';

if (call.triage_label === 'Emergency') {
  doctor = 'ER Duty Team';
  appointment_slot = 'Immediately – Emergency department';
  booking_status = 'ER alerted';
} else if (!wantsBooking) {
  booking_status = 'No booking needed';
} else {
  // Urgent calls are seen within a day; routine calls on the day the caller asked for.
  const offset = call.triage_label === 'Urgent' ? Math.min(call.delay_days, 1) : Math.max(call.delay_days, 1);
  for (let i = 0; i < 21 && !doctor; i++) {
    const day = now.plus({ days: offset + i });
    const free = doctors.find(d => (d.days || '').split(',').includes(DAYS[day.weekday % 7]));
    if (free) {
      doctor = free.name;
      appointment_slot = `${day.toFormat('ccc d LLL yyyy')}, ${free.start_time}`;
    }
  }
  if (!doctor) booking_status = 'Needs manual scheduling';
}

const keep = ['call_id', 'patient_name', 'patient_phone', 'age', 'symptoms', 'preferred_department', 'request_type',
  'appointment_details', 'call_summary', 'call_successful', 'transcript', 'severity', 'distress', 'vulnerability',
  'delay_days', 'triage_score', 'triage_label', 'department', 'route_confidence', 'route_source'];
const record = Object.fromEntries(keep.map(k => [k, call[k] === '' || call[k] === undefined ? null : call[k]]));
return [{ json: { ...record, doctor, appointment_slot, booking_status } }];
