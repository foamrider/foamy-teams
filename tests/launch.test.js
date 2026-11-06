// Runs the real launch command (sh + setsid -f) the panel hands to Process.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { spawnSync } = require('node:child_process')
const M = require('../Model.js')

for (const value of [null, [], '', [3], [''], ['  '], ['app', 'a\0b'], 'app']) assert.equal(M.launchCommand(value), null)

const missing = M.launchCommand(['/nonexistent/foamy-teams-test'])
assert.equal(spawnSync(missing[0], missing.slice(1)).status, 127)
const missingOnPath = M.launchCommand(['foamy-teams-no-such-client'])
assert.equal(spawnSync(missingOnPath[0], missingOnPath.slice(1)).status, 127)

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'foamy-teams-launch-'))
try {
  const out = path.join(dir, 'out')
  const marker = path.join(dir, 'never')
  // The client records its arguments, session and parent session, and writes to
  // stdout/stderr, which must not reach the launcher.
  const client = path.join(dir, 'client')
  fs.writeFileSync(client, '#!/bin/sh\n' +
    'read -r stat < /proc/$$/stat; set -- "$@" "$(echo "$stat" | cut -d" " -f6)" "$$"\n' +
    'printf "%s\\n" "$@" > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"\necho leaked; echo leaked >&2\n', { mode: 0o755 })
  const command = M.launchCommand([client, `$(touch ${marker})`, 'two words', '--flag'])
  assert.deepEqual(command.slice(4), [client, `$(touch ${marker})`, 'two words', '--flag'])
  const run = spawnSync(command[0], command.slice(1), { env: { ...process.env, OUT: out } })
  assert.equal(run.status, 0)
  assert.equal(run.stdout.length + run.stderr.length, 0)
  const deadline = Date.now() + 5000
  while (!fs.existsSync(out) && Date.now() < deadline) spawnSync('sleep', ['0.05'])
  const [one, two, three, sid, pid] = fs.readFileSync(out, 'utf8').trimEnd().split('\n')
  assert.deepEqual([one, two, three], [`$(touch ${marker})`, 'two words', '--flag'])
  assert.equal(fs.existsSync(marker), false)
  assert.equal(sid, pid, 'the client leads its own session')
  const ownSid = fs.readFileSync('/proc/self/stat', 'utf8').split(') ')[1].split(' ')[3]
  assert.notEqual(sid, ownSid)
} finally {
  fs.rmSync(dir, { recursive: true, force: true })
}
console.log('launch tests passed')
