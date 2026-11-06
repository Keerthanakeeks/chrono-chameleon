const express = require('express');
const fs = require('fs');
const path = require('path');
const http = require('http');

const SHARED = path.join(__dirname, '..', 'shared_logs');
const app = express();
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

function readLines(file) {
  try {
    return fs.readFileSync(path.join(SHARED, file), 'utf8')
      .split('\n').filter(Boolean).map(l => {
        try { return JSON.parse(l); } catch { return null; }
      }).filter(Boolean);
  } catch { return []; }
}

function readLocalContainers() {
  try {
    return JSON.parse(fs.readFileSync(path.join(SHARED, 'containers.json'), 'utf8'));
  } catch { return []; }
}

function dockerState(cb) {
  const opts = { socketPath: '/var/run/docker.sock', path: '/containers/json?all=true', method: 'GET' };
  const req = http.request(opts, res => {
    let data = '';
    res.on('data', c => data += c);
    res.on('end', () => {
      try {
        const containers = JSON.parse(data).map(c => ({
          name: c.Names[0].replace('/', ''), status: c.Status,
          port: Object.keys(c.Ports)[0] ? Object.values(c.Ports)[0].PublicPort : null,
        }));
        cb(containers.length ? containers : readLocalContainers());
      } catch { cb(readLocalContainers()); }
    });
  });
  req.on('error', () => cb(readLocalContainers()));
  req.end();
}

app.get('/api/state', (req, res) => {
  dockerState(containers => {
    res.json({
      containers, attacks: readLines('attack.log').slice(-100).reverse(),
      bans: readLines('bans.txt').reverse(), recon: readLines('recon.json').reverse(),
    });
  });
});

app.listen(6060, () => console.log('[SOC] Control Center on http://localhost:6060'));
