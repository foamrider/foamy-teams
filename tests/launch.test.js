// Runs the real launch command (sh + setsid -f) the panel hands to Process.
const assert = require('node:assert/strict')
const test = require('node:test')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { spawnSync } = require('node:child_process')
const M = require('../Model.js')

test('launchCommand refuses anything but a non-empty argv of strings without NUL', () => {
  for (const value of [null, [], '', [3], [''], ['  '], ['app', 'a\0b'], 'app']) assert.equal(M.launchCommand(value), null, JSON.stringify(value))
})

test('a missing client ends the launcher with exit 127', () => {
  const missing = M.launchCommand(['/nonexistent/foamy-teams-test'])
  assert.equal(spawnSync(missing[0], missing.slice(1)).status, 127, 'absolute path')
  const missingOnPath = M.launchCommand(['foamy-teams-no-such-client'])
  assert.equal(spawnSync(missingOnPath[0], missingOnPath.slice(1)).status, 127, 'PATH lookup')
})

test('the launcher returns at once and the client runs on in its own session with literal arguments', t => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'foamy-teams-launch-'))
  const out = path.join(dir, 'out')
  // Runs after a pass or a failure: stop the client (its pid is the last
  // line of its record) and remove the directory.
  t.after(() => {
    const pid = fs.existsSync(out) ? Number(fs.readFileSync(out, 'utf8').trimEnd().split('\n').pop()) : 0
    if (pid > 0) {
      try {
        process.kill(pid, 'SIGKILL')
      } catch (error) {
        if (error.code !== 'ESRCH') throw error
      }
    }
    fs.rmSync(dir, { recursive: true, force: true })
  })
  const marker = path.join(dir, 'never')
  // The client records its arguments, session and pid, writes to stdout and
  // stderr (which must not reach the launcher), then keeps running like a
  // real Teams window. The sleep bounds a failing run: a launcher that
  // waits for the client, or a client that holds the launcher's pipes,
  // blocks until it ends.
  const client = path.join(dir, 'client')
  fs.writeFileSync(client, '#!/bin/sh\n' +
    'read -r stat < /proc/$$/stat; set -- "$@" "$(echo "$stat" | cut -d" " -f6)" "$$"\n' +
    'printf "%s\\n" "$@" > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"\necho leaked; echo leaked >&2\nexec sleep 10\n', { mode: 0o755 })
  const command = M.launchCommand([client, `$(touch ${marker})`, 'two words', '--flag'])
  const run = spawnSync(command[0], command.slice(1), { env: { ...process.env, OUT: out }, timeout: 5000 })
  assert.equal(run.error, undefined, 'the launcher returns without waiting for the client')
  assert.equal(run.status, 0)
  assert.equal(run.stdout.toString() + run.stderr.toString(), '', 'the client output does not reach the launcher')
  const deadline = Date.now() + 5000
  while (!fs.existsSync(out) && Date.now() < deadline) spawnSync('sleep', ['0.05'])
  assert.ok(fs.existsSync(out), 'the client starts and writes its record within 5 s')
  const [one, two, three, sid, pid] = fs.readFileSync(out, 'utf8').trimEnd().split('\n')
  assert.deepEqual([one, two, three], [`$(touch ${marker})`, 'two words', '--flag'])
  assert.equal(fs.existsSync(marker), false, 'no argument runs as shell code')
  assert.doesNotThrow(() => process.kill(Number(pid), 0), 'the client still runs after the launcher returned')
  assert.equal(sid, pid, 'the client leads its own session')
  const ownSid = fs.readFileSync('/proc/self/stat', 'utf8').split(') ')[1].split(' ')[3]
  assert.notEqual(sid, ownSid)
})
