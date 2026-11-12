// Accounts are supplied by the user's widget settings, never public defaults.
function text(value) { return typeof value === "string" ? value : "" }
function titleState(title) {
  var raw = text(title).trim()
  var count = raw.match(/^\(([0-9]+)\)\s*/)
  var known = /Microsoft Teams/i.test(raw) && !/sign[ -]?in|log[ -]?in/i.test(raw)
  var unread = count && known ? Number(count[1]) : known ? 0 : null
  if (unread !== null && (!isFinite(unread) || unread > 9007199254740991)) unread = null
  // raw is trimmed and the result is trimmed again, so the suffix pattern
  // needs no \s* around it; a leading \s* backtracks quadratically on a long
  // run of spaces in a page-controlled title.
  return { unread: unread, context: raw.replace(/^\([0-9]+\)\s*/, "").replace(/\|\s*Microsoft Teams$/i, "").trim() }
}
function accountsForWindows(definitions, windows) {
  return definitions.filter(function(d) { return d.enabled }).map(function(d) {
    var matches = windows.filter(function(w) { return text(w.appId).toLowerCase() === d.appId.toLowerCase() })
    var focused = matches.find(function(w) { return w.activated }) || matches[0]
    var counts = matches.map(function(w) { return titleState(w.title).unread }).filter(function(n) { return n !== null })
    // Multiple windows can repeat one account's count; adding them would double count.
    var unread = counts.length ? Math.max.apply(null, counts) : null
    return { id:d.id, name:d.name, definition:d, running:matches.length > 0, active:matches.some(function(w) { return w.activated }), unread:unread,
      context:focused ? titleState(focused.title).context : "", toplevel:focused ? focused.toplevel : null }
  })
}
function summary(accounts) {
  return accounts.reduce(function(s,a) {
    if (a.running) s.runningCount++
    if (a.unread === null) s.unknownCount++
    else s.totalUnread += a.unread
    return s
  }, {totalUnread:0,runningCount:0,unknownCount:0,accountCount:accounts.length})
}
function primaryAccount(accounts, preferred) {
  var chosen = accounts.find(function(a) { return a.id === preferred })
  if (chosen) return chosen
  return accounts.slice().sort(function(a,b) {
    return (b.unread || 0) - (a.unread || 0) || Number(b.active)-Number(a.active) || Number(b.running)-Number(a.running)
  })[0] || null
}
function displayedAccounts(accounts, showClosed, unreadFirst) {
  var result=accounts.filter(function(a) { return showClosed || a.running })
  // Keep configured order for equal counts, including unknown counts.
  if (unreadFirst) result.sort(function(a,b) { return (b.unread || 0)-(a.unread || 0) })
  return result
}
function candidates(windows) {
  var seen={}
  return windows.filter(function(w) {
    var id=text(w.appId), key=id.toLowerCase()
    if (!id || (!/teams/i.test(id) && !/Microsoft Teams/i.test(text(w.title))) || seen[key]) return false
    seen[key]=true
    return true
  }).map(function(w) { return {value:w.appId,label:w.appId} })
}
// Lower-case application IDs of the enabled accounts: the only windows whose
// titles the widget reads.
function trackedAppIds(definitions) {
  var seen={}
  return (definitions || []).filter(function(d) { return d && d.enabled && text(d.appId) }).map(function(d) { return d.appId.toLowerCase() })
    .filter(function(id) { if (seen[id]) return false; seen[id]=true; return true }).sort()
}
function tracked(appIds, appId) { return (appIds || []).indexOf(text(appId).toLowerCase()) >= 0 }
// Comparable form of a window snapshot (identity is compared separately).
function signature(windows) {
  return JSON.stringify((windows || []).map(function(w) { return [text(w.appId), text(w.title), w.activated === true] }))
}
// The avatar letter: the name's first code point, upper-cased, so a name that
// starts with an emoji (a surrogate pair) never shows half of it.
function initial(name) {
  var first = text(name).codePointAt(0)
  return first === undefined ? "" : String.fromCodePoint(first).toUpperCase()
}
function launchArguments(account) {
  if (account.command.length) return account.command.slice()
  var args=account.browser === "omarchy-launch-webapp" ? [account.browser,account.url] : [account.browser,"--app="+account.url]
  if (account.profile) args.push("--profile-directory="+account.profile)
  return args
}
// The launch argv runs without a shell parsing it: sh only checks that the
// executable resolves (exit 127 otherwise, so the panel can report it), and
// setsid -f starts it in its own session with no inherited input or output, so
// the client outlives the popup and the shell.
var LAUNCH_SCRIPT = 'command -v -- "$1" >/dev/null 2>&1 || exit 127; exec setsid -f -- "$@" </dev/null >/dev/null 2>&1'
function launchCommand(args) {
  if (!Array.isArray(args) || !args.length || typeof args[0] !== "string" || !args[0].trim()) return null
  for (var i = 0; i < args.length; i++) if (typeof args[i] !== "string" || args[i].indexOf("\0") !== -1) return null
  return ["sh", "-c", LAUNCH_SCRIPT, "foamy-teams"].concat(args)
}
if (typeof module !== "undefined") module.exports={titleState:titleState,accountsForWindows:accountsForWindows,summary:summary,primaryAccount:primaryAccount,displayedAccounts:displayedAccounts,candidates:candidates,trackedAppIds:trackedAppIds,tracked:tracked,signature:signature,initial:initial,launchArguments:launchArguments,launchCommand:launchCommand}
