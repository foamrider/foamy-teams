// Window context (the chat or person name from a Teams title) is off by default:
// it is readable by anyone watching a shared screen while the popup is open.
var defaults={accounts:[],showCount:true,hideWhenClosed:false,showContext:false,showClosed:true,unreadFirst:false,defaultAccount:""}
// foamy-kit FoamyPrefs schema (FoamyPrefsQueue saves and reads through it).
var fields=[
  {key:"accounts",type:"array",maxItems:32,defaultValue:[],validate:function(v) { var e=accountError(v); return e==="" ? true : e }},
  {key:"showCount",type:"boolean",defaultValue:true},
  {key:"hideWhenClosed",type:"boolean",defaultValue:false},
  {key:"showContext",type:"boolean",defaultValue:false},
  {key:"showClosed",type:"boolean",defaultValue:true},
  {key:"unreadFirst",type:"boolean",defaultValue:false},
  {key:"defaultAccount",type:"string",maxLength:80,defaultValue:""}
]
function accountError(accounts) {
  if (!Array.isArray(accounts) || accounts.length>32) return "Use at most 32 accounts."
  var ids={}, appIds={}
  for (var i=0;i<accounts.length;i++) {
    var a=accounts[i]
    if (!a || typeof a!=="object" || Array.isArray(a)) return "Invalid account."
    if (typeof a.id!=="string" || !/^[a-zA-Z0-9_-]{1,80}$/.test(a.id) || ids[a.id]) return "Account IDs must be unique."
    ids[a.id]=true
    if (typeof a.name!=="string" || !a.name.trim() || a.name.length>120) return "Enter an account name."
    if (typeof a.appId!=="string" || !a.appId.trim() || a.appId.length>512 || /[\x00-\x1f]/.test(a.appId)) return "Choose a window or enter its application ID."
    if (appIds[a.appId.toLowerCase()]) return "This application ID is already assigned to an account."
    appIds[a.appId.toLowerCase()]=true
    if (typeof a.enabled!=="boolean") return "Invalid account."
    if (typeof a.profile!=="string" || a.profile.length>256 || /[\x00-\x1f]/.test(a.profile)) return "Enter a valid browser profile."
    if (typeof a.browser!=="string" || !a.browser.trim() || /[\x00-\x20]/.test(a.browser)) return "Enter a browser executable without arguments."
    if (typeof a.url!=="string" || !/^https:\/\/[^\s/]+(?:\/[^\s]*)?$/.test(a.url)) return "Enter an HTTPS Teams URL."
    if (!Array.isArray(a.command) || a.command.length>64 || a.command.some(function(v) { return typeof v!=="string" || v.length>4096 || v.indexOf("\x00")>=0 }) || (a.command.length && !a.command[0].trim())) return "Enter a JSON array of command arguments, or []."
  }
  return ""
}
function configurationError(settings) { return settings && settings.accounts!==undefined ? accountError(settings.accounts) : "" }
if (typeof module!=="undefined") module.exports={defaults:defaults,fields:fields,accountError:accountError,configurationError:configurationError}
