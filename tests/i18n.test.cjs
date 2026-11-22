const assert = require('node:assert/strict')
const test = require('node:test')
const fs = require('node:fs')
const path = require('node:path')
const root = path.join(__dirname, '..')
const en = require('../i18n/en.json')
const no = require('../i18n/no.json')
const tokens = s => [...s.matchAll(/%[1-9][0-9]*|\{\w+\}/g)].map(m => m[0]).sort()
const text = s => typeof s === 'string' && s !== ''

test('each English key has its own text and a Norwegian entry with the same placeholders', () => {
  for (const [key, value] of Object.entries(en)) {
    assert.ok(Object.hasOwn(no, key), `Norwegian entry for ${key}`)
    if (typeof value === 'object') {
      assert.equal(value.other, key, `English plural source key: ${key}`)
      assert.ok(text(value.one), `English "one" form of ${key}`)
      assert.deepEqual(tokens(value.one), tokens(key), `English "one" placeholders of ${key}`)
      assert.ok(no[key] !== null && typeof no[key] === 'object', `Norwegian plural for ${key}`)
      for (const form of ['one', 'other']) {
        assert.ok(text(no[key][form]), `Norwegian "${form}" form of ${key}`)
        assert.deepEqual(tokens(no[key][form]), tokens(key), `Norwegian "${form}" placeholders of ${key}`)
      }
      continue
    }
    assert.equal(value, key, `English source key: ${key}`)
    assert.ok(text(no[key]), `Norwegian text for ${key}`)
    assert.deepEqual(tokens(no[key]), tokens(value), `Norwegian placeholders of ${key}`)
  }
})

// The first argument of the call whose "(" is at `open`: the source up to the
// "," or ")" at depth 0, skipping string literals.
function firstArgument(source, open) {
  let depth = 0
  for (let i = open + 1; i < source.length; i++) {
    const c = source[i]
    if (c === '"' || c === "'") {
      for (i++; i < source.length && source[i] !== c; i++) if (source[i] === '\\') i++
    } else if ('([{'.includes(c)) depth++
    else if (')]}'.includes(c)) {
      if (depth === 0) return source.slice(open + 1, i)
      depth--
    } else if (c === ',' && depth === 0) return source.slice(open + 1, i)
  }
  return ''
}

// A static scan of the plugin's QML and JavaScript: the catalogs are the
// thing checked. It finds
// - every literal in the first argument of tr(, FoamyI18n.t( or
//   FoamyI18n.tn(, also each branch of a choice such as
//   tr(enabled ? "Enabled" : "Disabled");
// - a literal after `label:` (toggle models translated later);
// - every message: a double-quoted literal that starts with a capital letter
//   and ends with "." or "…". Messages often reach tr() through a variable
//   (Preferences.accountError, TeamsService.launchError), which the first
//   rule cannot see.
function shownStrings() {
  const found = new Set()
  const literals = /"((?:[^"\\\n]|\\.)*)"/g
  for (const file of fs.readdirSync(root).filter(f => /\.(qml|js)$/.test(f))) {
    const source = fs.readFileSync(path.join(root, file), 'utf8').split('\n').filter(line => !/^\s*\/\//.test(line)).join('\n')
    for (const m of source.matchAll(/(?:\btr|FoamyI18n\.tn?)\(/g))
      for (const literal of firstArgument(source, m.index + m[0].length - 1).matchAll(literals)) found.add(JSON.parse(`"${literal[1]}"`))
    for (const m of source.matchAll(/\blabel:\s*"((?:[^"\\]|\\.)*)"/g)) found.add(JSON.parse(`"${m[1]}"`))
    // Filter the raw text first, so an escape such as "\0" never reaches JSON.parse.
    for (const m of source.matchAll(literals)) if (/^[A-Z].*[.…]$/s.test(m[1])) found.add(JSON.parse(`"${m[1]}"`))
  }
  return found
}

test('every string the plugin can show has an English and a Norwegian entry', () => {
  const shown = [...shownStrings()]
  assert.deepEqual(shown.filter(key => !Object.hasOwn(en, key)), [], 'shown strings without an English entry')
  assert.deepEqual(shown.filter(key => !Object.hasOwn(no, key)), [], 'shown strings without a Norwegian entry')
})
