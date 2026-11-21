const assert = require('node:assert/strict')
const test = require('node:test')
const M = require('../Model.js')
const P = require('../Preferences.js')
const Prefs = require('../kit/node-loader.cjs').load('FoamyPrefs')
const manifest = require('../manifest.json')
const F = P.fields
const account = (id, appId) => ({ id, name: id, appId, enabled: true, browser: 'omarchy-launch-webapp', profile: 'Work', url: 'https://teams.microsoft.com', command: [] })
const definitions = [account('work', 'teams-work'), account('personal', 'teams-personal')]
const many = n => Array.from({ length: n }, (_, i) => account(`a${i}`, `teams-${i}`))
const ids = rows => rows.map(r => r.id)

test('accountError accepts a valid list and rejects each invalid account with its own message', () => {
  const one = changes => [{ ...definitions[0], ...changes }]
  const ID = 'Account IDs must be unique.'
  const NAME = 'Enter an account name.'
  const APP = 'Choose a window or enter its application ID.'
  const PROFILE = 'Enter a valid browser profile.'
  const BROWSER = 'Enter a browser executable without arguments.'
  const URL = 'Enter an HTTPS Teams URL.'
  const COMMAND = 'Enter a JSON array of command arguments, or [].'
  // This validator is what keeps javascript: URLs, browser arguments and NUL
  // out of the launch argv, so every rule and every limit has a row.
  const rows = [
    ['a valid list', definitions, ''],
    ['not an array (null)', null, 'Use at most 32 accounts.'],
    ['not an array (object)', {}, 'Use at most 32 accounts.'],
    ['33 accounts', many(33), 'Use at most 32 accounts.'],
    ['32 accounts', many(32), ''],
    ['a null item', [null], 'Invalid account.'],
    ['an array item', [[]], 'Invalid account.'],
    ['a string item', ['x'], 'Invalid account.'],
    ['enabled as a string', one({ enabled: 'true' }), 'Invalid account.'],
    ['a numeric id', one({ id: 3 }), ID],
    ['an empty id', one({ id: '' }), ID],
    ['an id with a space', one({ id: 'a b' }), ID],
    ['an id of 81 characters', one({ id: 'x'.repeat(81) }), ID],
    ['an id of 80 characters', one({ id: 'x'.repeat(80) }), ''],
    ['the same id twice', [definitions[0], { ...definitions[1], id: 'work' }], ID],
    ['a blank name', one({ name: '   ' }), NAME],
    ['a name of 121 characters', one({ name: 'n'.repeat(121) }), NAME],
    ['a name of 120 characters', one({ name: 'n'.repeat(120) }), ''],
    ['a blank application ID', one({ appId: ' ' }), APP],
    ['an application ID of 513 characters', one({ appId: 'a'.repeat(513) }), APP],
    ['an application ID of 512 characters', one({ appId: 'a'.repeat(512) }), ''],
    ['an application ID with a newline', one({ appId: 'a\nb' }), APP],
    ['an application ID used twice in another case', [definitions[0], { ...definitions[1], appId: 'TEAMS-WORK' }], 'This application ID is already assigned to an account.'],
    ['a numeric profile', one({ profile: 3 }), PROFILE],
    ['a profile of 257 characters', one({ profile: 'p'.repeat(257) }), PROFILE],
    ['a profile of 256 characters', one({ profile: 'p'.repeat(256) }), ''],
    ['a profile with a newline', one({ profile: 'a\nb' }), PROFILE],
    ['no profile', one({ profile: '' }), ''],
    ['an empty browser', one({ browser: '' }), BROWSER],
    ['a browser with an argument', one({ browser: 'browser --arg' }), BROWSER],
    ['a browser with a tab', one({ browser: 'a\tb' }), BROWSER],
    ['a javascript: URL', one({ url: 'javascript:bad' }), URL],
    ['an http URL', one({ url: 'http://teams.microsoft.com' }), URL],
    ['an https URL without a host', one({ url: 'https://' }), URL],
    ['an https URL with a space', one({ url: 'https://a b' }), URL],
    ['a file URL', one({ url: 'file:///etc/passwd' }), URL],
    ['an https URL with a path', one({ url: 'https://teams.microsoft.com/v2/' }), ''],
    ['a command as a string', one({ command: 'sh -c bad' }), COMMAND],
    ['a command with a number', one({ command: [3] }), COMMAND],
    ['a command with an empty executable', one({ command: [''] }), COMMAND],
    ['a command with a blank executable', one({ command: ['  ', 'x'] }), COMMAND],
    ['a command argument with NUL', one({ command: ['x', 'a\0b'] }), COMMAND],
    ['a command of 65 items', one({ command: Array(65).fill('x') }), COMMAND],
    ['a command of 64 items', one({ command: Array(64).fill('x') }), ''],
    ['a command argument of 4097 characters', one({ command: ['x', 'y'.repeat(4097)] }), COMMAND],
    ['a command argument of 4096 characters', one({ command: ['x', 'y'.repeat(4096)] }), ''],
  ]
  for (const [name, accounts, message] of rows) assert.equal(P.accountError(accounts), message, name)
})

test('the accounts setting hands accountError to the kit, and a bad stored list reads as empty', () => {
  const bad = [{ ...definitions[0], url: 'javascript:bad' }]
  assert.equal(Prefs.valid(F, 'accounts', definitions), true)
  assert.equal(Prefs.valid(F, 'accounts', bad), false)
  assert.equal(Prefs.problem(F, 'accounts', bad), 'Enter an HTTPS Teams URL.')
  assert.equal(JSON.stringify(Prefs.value(F, { accounts: [null] }, 'accounts')), '[]')
})

test('a Teams title gives the unread count and the context; other titles give an unknown count', () => {
  assert.deepEqual(M.titleState('(12) Chat | Team | Microsoft Teams'), { unread: 12, context: 'Chat | Team' })
  assert.equal(M.titleState('Chat | Microsoft Teams').unread, 0)
  for (const title of ['', 'Loading…', 'Sign in | Microsoft Teams', '(99) unrelated', '(9007199254740992) Microsoft Teams'])
    assert.equal(M.titleState(title).unread, null, title)
  for (const [title, context] of [['Chat   |   Microsoft Teams', 'Chat'], ['(2)  A | B |Microsoft Teams  ', 'A | B'], ['Chat |', 'Chat |'], ['| Microsoft Teams', ''], ['Chat' + ' '.repeat(10) + '| Microsoft Teams', 'Chat']])
    assert.equal(M.titleState(title).context, context, title)
})

test('titleState stays linear on a long run of spaces', () => {
  // Titles reach titleState unbounded except by the Wayland message size (4 KiB).
  // A quadratic suffix pattern took about 5 ms a call here.
  const spaced = 'Chat' + ' '.repeat(4000) + 'x'
  const started = process.hrtime.bigint()
  for (let i = 0; i < 200; i++) M.titleState(spaced)
  assert.ok(Number(process.hrtime.bigint() - started) / 1e6 < 500, 'titleState is linear on long whitespace')
})

const unfocused = { appId: 'TEAMS-WORK', title: '(5) Chat | Microsoft Teams', activated: false, toplevel: 'one' }
const focused = { appId: 'teams-work', title: '(3) Standup | Microsoft Teams', activated: true, toplevel: 'two' }
const foreign = { appId: 'browser', title: '(99) Microsoft Teams', activated: false, toplevel: 'three' }

test('an account row takes the highest count of its windows and the context of the focused one', () => {
  const rows = M.accountsForWindows(definitions, [unfocused, focused, foreign])
  assert.deepEqual(rows.map(r => [r.id, r.running, r.active, r.unread, r.context, r.toplevel]), [
    ['work', true, true, 5, 'Standup', 'two'],
    ['personal', false, false, null, '', null],
  ])
  assert.equal(rows[0].definition, definitions[0])
  const [only] = M.accountsForWindows(definitions, [unfocused])
  assert.deepEqual([only.active, only.unread, only.context, only.toplevel], [false, 5, 'Chat', 'one'])
  assert.deepEqual(M.summary(rows), { totalUnread: 5, runningCount: 1, unknownCount: 1, accountCount: 2 })
})

test('a disabled account gives no row', () => {
  assert.equal(M.accountsForWindows([{ ...definitions[0], enabled: false }], [unfocused]).length, 0)
})

const row = (id, unread, running, active = false) => ({ id, unread, running, active })

test('middle-click picks the preferred account, else the most unread, then focused, then running', () => {
  const rows = [
    ['a preferred account wins over more unread', [row('more', 5, true), row('pref', 1, true)], 'pref', 'pref'],
    ['an unknown preferred id gives the most unread', [row('less', 1, true), row('more', 5, true)], 'deleted', 'more'],
    ['no preferred id gives the most unread', [row('less', 1, true), row('more', 5, true)], '', 'more'],
    ['at equal unread a focused account beats a running one', [row('running', 2, true), row('focused', 2, true, true)], '', 'focused'],
    ['at equal unread a running account beats a closed one', [row('closed', null, false), row('running', 0, true)], '', 'running'],
  ]
  for (const [name, accounts, preferred, expected] of rows) assert.equal(M.primaryAccount(accounts, preferred).id, expected, name)
  assert.equal(M.primaryAccount([], ''), null)
})

test('the popup lists closed accounts on request and puts unread accounts first on request', () => {
  const rows = [row('a', 1, true), row('b', 5, true), row('c', null, false), row('d', 2, true)]
  assert.deepEqual(ids(M.displayedAccounts(rows, true, false)), ['a', 'b', 'c', 'd'])
  assert.deepEqual(ids(M.displayedAccounts(rows, false, false)), ['a', 'b', 'd'])
  assert.deepEqual(ids(M.displayedAccounts(rows, true, true)), ['b', 'd', 'a', 'c'])
  assert.deepEqual(ids(rows), ['a', 'b', 'c', 'd'], 'the input order is not changed')
})

test('the window picker lists Teams windows once per application ID and never shows a title', () => {
  const windows = [
    { appId: 'teams-work', title: '(2) Private chat | Microsoft Teams' },
    { appId: 'TEAMS-WORK', title: 'Other' },
    { appId: 'chromium', title: 'Chat | Microsoft Teams' },
    { appId: 'kitty', title: 'notes' },
    { appId: '', title: 'Microsoft Teams' },
  ]
  assert.deepEqual(M.candidates(windows), [{ value: 'teams-work', label: 'teams-work' }, { value: 'chromium', label: 'chromium' }])
})

test('the launch argv follows the browser, the profile and the advanced command', () => {
  assert.deepEqual(M.launchArguments(definitions[0]), ['omarchy-launch-webapp', 'https://teams.microsoft.com', '--profile-directory=Work'])
  assert.deepEqual(M.launchArguments({ ...definitions[0], browser: 'chromium', profile: '' }), ['chromium', '--app=https://teams.microsoft.com'])
  assert.deepEqual(M.launchArguments({ ...definitions[0], command: ['client', '$(touch nope)'] }), ['client', '$(touch nope)'])
})

test('only configured, enabled application IDs are tracked (lower case, unique)', () => {
  assert.deepEqual(M.trackedAppIds([...definitions, { ...account('off', 'Other'), enabled: false }, account('dup', 'TEAMS-WORK')]), ['teams-personal', 'teams-work'])
  assert.equal(M.tracked(['teams-work'], 'Teams-Work'), true)
  assert.equal(M.tracked(['teams-work'], 'kitty'), false)
})

test('the settled publish compares titles and focus only, so an unchanged snapshot is not published again', () => {
  assert.equal(M.signature([unfocused]), M.signature([{ ...unfocused, toplevel: 'other' }]))
  assert.notEqual(M.signature([unfocused]), M.signature([{ ...unfocused, title: '(6) Chat | Microsoft Teams' }]))
  assert.notEqual(M.signature([unfocused]), M.signature([{ ...unfocused, activated: true }]))
})

test('window context is off until the user turns it on (screen sharing)', () => {
  assert.equal(Prefs.value(F, {}, 'showContext'), false)
})

test('the manifest defaults and schema agree with the settings fields', () => {
  for (const field of F) assert.equal(JSON.stringify(manifest.barWidget.defaults[field.key]), JSON.stringify(field.defaultValue), field.key)
  assert.deepEqual(Object.keys(manifest.barWidget.defaults).sort(), F.map(f => f.key).sort(), 'no default without a field')
  // The schema has every setting but the accounts list, which its field types
  // (boolean, enum, integer, string…) can't describe.
  assert.deepEqual(manifest.barWidget.schema.map(e => e.key), F.filter(f => f.type !== 'array').map(f => f.key))
  for (const entry of manifest.barWidget.schema) {
    const field = F.find(f => f.key === entry.key)
    for (const key of ['type', 'maxLength', 'defaultValue']) assert.equal(entry[key], field[key], entry.key + '.' + key)
  }
})

test('the avatar initial is one whole code point: an emoji surrogate pair stays together', () => {
  for (const [name, initial] of [['work', 'W'], ['\u{1F600} Fun', '\u{1F600}'], ['école', 'É'], ['', ''], [null, '']])
    assert.equal(M.initial(name), initial, JSON.stringify(name))
})
