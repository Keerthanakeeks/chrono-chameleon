const express = require('express');
const fs = require('fs');
const path = require('path');

const MODE = process.env.MODE || 'trap';
const PORT = process.env.PORT || 8000;
const SHARED_DIR = process.env.SHARED_LOGS || (fs.existsSync('/shared_logs') ? '/shared_logs' : path.join(__dirname, '..', 'shared_logs'));
const LOG_PATH = path.join(SHARED_DIR, 'attack.log');
const BAN_QUEUE = path.join(SHARED_DIR, 'ban_queue.log');

const app = express();
app.use(express.json());

function clientIp(req) {
  const raw = req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown';
  return raw.replace(/^::ffff:/, '').replace(/^::1$/, '127.0.0.1');
}

function logEvent(type, req, extra = {}) {
  const entry = JSON.stringify({
    type, ip: clientIp(req), port: Number(PORT), mode: MODE,
    path: req.path, ua: req.headers['user-agent'] || 'unknown',
    time: new Date().toISOString(), ...extra,
  });
  try { fs.appendFileSync(LOG_PATH, entry + '\n'); } catch (e) {}
}

function triggerBan(req, reason) {
  try {
    fs.appendFileSync(BAN_QUEUE, JSON.stringify({
      ip: clientIp(req), reason, port: Number(PORT), time: new Date().toISOString(),
    }) + '\n');
  } catch (e) {}
  logEvent('HONEYTOKEN_HIT', req, { reason });
}

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

if (MODE === 'real') {
  app.get('/', (req, res) => {
    res.json({ status: 'success', message: 'Real application is alive', active_port: Number(PORT), mode: MODE });
  });
  app.listen(PORT, () => console.log(`[REAL] Protected app live on ${PORT}`));
}
