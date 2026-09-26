// Accounts are supplied by the user's widget settings, never public defaults.
function text(value) { return typeof value === "string" ? value : "" }
function titleState(title) {
  var raw = text(title).trim()
  var count = raw.match(/^\(([0-9]+)\)\s*/)
  var known = /Microsoft Teams/i.test(raw) && !/sign[ -]?in|log[ -]?in/i.test(raw)
  var unread = count && known ? Number(count[1]) : known ? 0 : null
  if (unread !== null && (!isFinite(unread) || unread > 9007199254740991)) unread = null
  return { unread: unread, context: raw.replace(/^\([0-9]+\)\s*/, "").replace(/\s*\|\s*Microsoft Teams\s*$/i, "").trim() }
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
function launchArguments(account) {
  if (account.command.length) return account.command.slice()
  var args=account.browser === "omarchy-launch-webapp" ? [account.browser,account.url] : [account.browser,"--app="+account.url]
  if (account.profile) args.push("--profile-directory="+account.profile)
  return args
}
if (typeof module !== "undefined") module.exports={titleState:titleState,accountsForWindows:accountsForWindows,summary:summary,primaryAccount:primaryAccount,displayedAccounts:displayedAccounts,candidates:candidates,launchArguments:launchArguments}
