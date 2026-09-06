const express = require('express');
const cors = require('cors');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'thyrocare_b2b_secret_key_2026';
const ADMIN_PASSWORD_HASH = bcrypt.hashSync('Abhinandanverma@8811', 10);

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const doctorsDb = new Map();
let ordersDb = [];
const WHATSAPP_TARGETS = ["6284828212", "7719401188"];

const fs = require('fs');

let TEST_CATALOG = [];
const catalogFilePath = path.join(__dirname, 'catalog_data.json');
if (fs.existsSync(catalogFilePath)) {
  TEST_CATALOG = JSON.parse(fs.readFileSync(catalogFilePath, 'utf8'));
  console.log(`[CATALOG] Loaded ${TEST_CATALOG.length} diagnostic tests from catalog_data.json.`);
} else {
  TEST_CATALOG = [
    { code: 'THY001', name: 'Thyroid Profile Total (T3, T4, TSH)', specimen: 'Blood / Serum', mrp: 600, b2b_rate: 250, description: 'Evaluation of thyroid gland function.' }
  ];
}

function seedDatabase() {
  const salt = bcrypt.genSaltSync(10);
  doctorsDb.set('DOC1001', {
    doctor_id: 'DOC1001',
    passcode_hash: bcrypt.hashSync('thyrocare123', salt),
    doctor_name: 'Dr. A. Sharma, MD',
    clinic_name: 'Apex Diagnostic & Healthcare Clinic',
    is_active: true,
    created_at: new Date('2025-01-15T08:00:00Z').toISOString()
  });

  doctorsDb.set('DOC1002', {
    doctor_id: 'DOC1002',
    passcode_hash: bcrypt.hashSync('clinic456', salt),
    doctor_name: 'Dr. Priya Nair, MBBS, DNB',
    clinic_name: 'Nair HealthCare & Diagnostics',
    is_active: true,
    created_at: new Date('2025-02-01T10:30:00Z').toISOString()
  });

  doctorsDb.set('DOC1003', {
    doctor_id: 'DOC1003',
    passcode_hash: bcrypt.hashSync('locked789', salt),
    doctor_name: 'Dr. Rajesh Verma, MD',
    clinic_name: 'Metro Wellness Center',
    is_active: false,
    created_at: new Date('2025-02-10T14:15:00Z').toISOString()
  });

  const now = new Date();
  const demoSamples = [
    { daysAgo: 0, pat: "Sunil Kumar", mob: "9876543210", doc: "DOC1001", tests: ["THY001", "HBA003"] },
    { daysAgo: 2, pat: "Meena Agarwal", mob: "9812345678", doc: "DOC1001", tests: ["LIP002", "VIT004"] },
    { daysAgo: 5, pat: "Rohan Gupta", mob: "9988776655", doc: "DOC1002", tests: ["CBC007", "LFT005"] },
    { daysAgo: 15, pat: "Ananya Roy", mob: "9765432109", doc: "DOC1001", tests: ["THY001", "RFT006"] },
    { daysAgo: 45, pat: "Vikram Singh", mob: "9654321098", doc: "DOC1002", tests: ["CAR008", "HBA003"] }
  ];

  demoSamples.forEach((sample, idx) => {
    const placedDt = new Date(now.getTime() - (sample.daysAgo * 24 * 60 * 60 * 1000));
    const doc = doctorsDb.get(sample.doc);
    const selectedTests = TEST_CATALOG.filter(t => sample.tests.includes(t.code));
    const mrpTotal = selectedTests.reduce((a, b) => a + b.mrp, 0);
    const b2bTotal = selectedTests.reduce((a, b) => a + b.b2b_rate, 0);

    ordersDb.push({
      order_id: `ORD-2026-${1000 + idx + 1}`,
      placed_at: placedDt.toISOString(),
      doctor_id: doc.doctor_id,
      doctor_name: doc.doctor_name,
      clinic_name: doc.clinic_name,
      patient_name: sample.pat,
      patient_mobile: sample.mob,
      tests: selectedTests,
      total_mrp: mrpTotal,
      total_b2b: b2bTotal,
      total_savings: mrpTotal - b2bTotal,
      recipient_numbers: WHATSAPP_TARGETS,
      status: "COMPLETED"
    });
  });
}

seedDatabase();

app.post('/api/v1/auth/verify-passcode', (req, res) => {
  const { doctor_id, passcode } = req.body;
  if (!doctor_id || !passcode) return res.status(400).json({ error: 'Doctor ID and Passcode required.' });

  const doc = doctorsDb.get(doctor_id.trim().toUpperCase());
  if (!doc || !bcrypt.compareSync(passcode.trim(), doc.passcode_hash)) {
    return res.status(401).json({ error: 'Invalid credentials.' });
  }

  if (!doc.is_active) return res.status(403).json({ error: 'Account suspended.' });

  const token = jwt.sign({ doctor_id: doc.doctor_id, doctor_name: doc.doctor_name }, JWT_SECRET, { expiresIn: '8h' });
  return res.json({ message: 'Success', token, doctor: doc });
});

app.post('/api/v1/admin/auth', (req, res) => {
  const { password } = req.body;
  if (password && bcrypt.compareSync(password.trim(), ADMIN_PASSWORD_HASH)) {
    const adminToken = jwt.sign({ admin: true }, JWT_SECRET, { expiresIn: '4h' });
    return res.json({ message: 'Admin verified', admin_token: adminToken });
  }
  return res.status(401).json({ error: 'Invalid Admin Password.' });
});

app.get('/api/v1/admin/orders', (req, res) => {
  const range = req.query.range || 'all';
  const { start, end } = req.query;
  const now = new Date();

  let filtered = ordersDb.filter(o => {
    const dt = new Date(o.placed_at);
    const daysDiff = (now.getTime() - dt.getTime()) / (1000 * 3600 * 24);

    if (range === '7days') return daysDiff >= 0 && daysDiff <= 7;
    if (range === 'month') return daysDiff >= 0 && daysDiff <= 30;
    if (range === 'custom' && start && end) {
      const sDt = new Date(start);
      const eDt = new Date(end);
      eDt.setHours(23, 59, 59, 999);
      return dt >= sDt && dt <= eDt;
    }
    return true;
  });

  filtered.sort((a, b) => new Date(b.placed_at) - new Date(a.placed_at));

  return res.json({
    total_orders: filtered.length,
    total_revenue_b2b: filtered.reduce((a, b) => a + b.total_b2b, 0),
    total_mrp_val: filtered.reduce((a, b) => a + b.total_mrp, 0),
    total_savings_val: filtered.reduce((a, b) => a + b.total_savings, 0),
    range_applied: range,
    orders: filtered
  });
});

app.get('/api/v1/catalog', (req, res) => res.json({ total: TEST_CATALOG.length, catalog: TEST_CATALOG }));

app.listen(PORT, () => console.log(`Thyrocare Express Server running on port ${PORT}`));
