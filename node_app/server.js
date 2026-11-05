/**
 * MTD Core App — DUAL MODE (one image, two personalities)
 *   MODE=real → protected application behind the smart proxy
 *   MODE=trap → Mirror Dimension sandbox on vacated ports
 *               - Honey-tokens (/admin-backup etc) → INSTANT ban queue
 *               - Data poisoning (fake user DB)
 *               - Chameleon: Microsoft-IIS/10.0 headers
 */
const express = require('express');
const fs = require('fs');

const MODE = process.env.MODE || 'trap';
const PORT = process.env.PORT || 8000;
const LOG_PATH = '/shared_logs/attack.log';
const BAN_QUEUE = '/shared_logs/ban_queue.log';

const app = express();
app.use(express.json());

function clientIp(req) {
  return req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown';
}

function logEvent(type, req, extra = {}) {
  const entry = JSON.stringify({
    type, ip: clientIp(req), port: PORT, mode: MODE,
    path: req.path, ua: req.headers['user-agent'] || 'unknown',
    time: new Date().toISOString(), ...extra,
  });
  try { fs.appendFileSync(LOG_PATH, entry + '\n'); } catch (e) {}
}

function triggerBan(req, reason) {
  try {
    fs.appendFileSync(BAN_QUEUE, JSON.stringify({
      ip: clientIp(req), reason, port: PORT, time: new Date().toISOString(),
    }) + '\n');
  } catch (e) {}
  logEvent('HONEYTOKEN_HIT', req, { reason });
}

// ---------- DATA POISONING: fake database ----------
const POISON_DB = {
  users: [
    { id: 1001, username: 'admin_backup', password: 'Sup3rS3cret!2024', role: 'superadmin' },
    { id: 1002, username: 'hr_payroll', password: 'Payroll@2025', role: 'finance' },
  ]
};

function poisoned(res) {
  res.set('Server', 'Microsoft-IIS/10.0');
  res.json({ status: 'ok', source: 'internal-db', data: POISON_DB });
}

// ==================== TRAP MODE (Mirror Dimension) ====================
if (MODE === 'trap') {
  app.use((req, res, next) => {
    logEvent('SANDBOX_TOUCH', req);
    res.set('Server', 'Microsoft-IIS/10.0');
    next();
  });

  const HONEY_PATHS = ['/admin-backup', '/backup/admin.zip', '/.aws/credentials'];
  app.get(HONEY_PATHS, (req, res) => {
    triggerBan(req, `honey-token: ${req.path}`);
    res.status(200).json({ status: 'download_ready', token: 'e2f8a1c9-DEAD-BEEF' });
  });

  app.get(['/api/users', '/db'], (req, res) => {
    logEvent('DATA_POISON_SERVED', req, { records: POISON_DB.users.length });
    poisoned(res);
  });

  app.all('*', (req, res) => {
    res.status(403).send('<h1>Forbidden</h1><hr><address>Microsoft-IIS/10.0</address>');
  });

  app.listen(PORT, () => console.log(`[TRAP] Mirror Dimension live on ${PORT} — honey-tokens armed`));
}

// ==================== REAL MODE (protected app) ====================
if (MODE === 'real') {
  app.get('/', (req, res) => {
    res.json({ status: 'success', message: 'Real application is alive', active_port: PORT, mode: MODE });
  });
  app.listen(PORT, () => console.log(`[REAL] Protected app live on ${PORT}`));
}
