var defaults={language:"system",accounts:[],showCount:true,hideWhenClosed:false,showContext:true,showClosed:true,unreadFirst:false,defaultAccount:""}
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
function valid(key,v) {
  if (key==="accounts") return accountError(v)===""
  if (key==="language") return ["system","en","nb"].indexOf(v)>=0
  if (key==="defaultAccount") return typeof v==="string" && v.length<=80
  return Object.prototype.hasOwnProperty.call(defaults,key) && typeof defaults[key]==="boolean" && typeof v==="boolean"
}
function value(settings,key) { return settings && valid(key,settings[key]) ? settings[key] : defaults[key] }
function configurationError(settings) { return settings && settings.accounts!==undefined ? accountError(settings.accounts) : "" }
function language(mode,locale) { return mode==="en" || mode==="nb" ? mode : /^(nb|nn|no)(_|-|$)/i.test(locale || "") ? "nb" : "en" }
var norwegian={
"All read":"Alt er lest",
"%1 unread message":"%1 ulest melding","1 unread":"1 ulest",
"Settings":"Innstillinger","Back":"Tilbake","Accounts":"Kontoer","Add account":"Legg til konto","Edit account":"Rediger konto","New account":"Ny konto","Save":"Lagre","Cancel":"Avbryt","Remove":"Fjern","Move up":"Flytt opp","Move down":"Flytt ned","Edit":"Rediger","Enabled":"Aktivert","Disabled":"Deaktivert","Name":"Navn","Open Teams window":"Åpent Teams-vindu","Manual application ID":"Manuell applikasjons-ID","Application ID":"Applikasjons-ID","Browser executable":"Nettleserprogram","Browser profile":"Nettleserprofil","Teams URL":"Teams-adresse","Advanced launch arguments (JSON array)":"Avanserte startargumenter (JSON-liste)","Language":"Språk","System":"System","Show unread count in the bar":"Vis antall uleste i panelet","Hide when all accounts are closed":"Skjul når alle kontoer er lukket","Show window context":"Vis vinduskontekst","Show closed accounts":"Vis lukkede kontoer","Put unread accounts first":"Vis kontoer med uleste først","Middle-click account":"Konto ved midtklikk","Most relevant account":"Mest relevant konto","No accounts configured":"Ingen kontoer konfigurert","Add your Teams accounts in Settings":"Legg til Teams-kontoene dine i innstillingene","All accounts are disabled":"Alle kontoer er deaktivert","Enable an account in Settings":"Aktiver en konto i innstillingene","Teams is not running":"Teams kjører ikke","Launch an account to see its unread count":"Start en konto for å se antall uleste","All caught up":"Alt er lest","No unread messages in open accounts":"Ingen uleste meldinger i åpne kontoer","Unread count unavailable":"Antall uleste er utilgjengelig","No unread in open accounts":"Ingen uleste i åpne kontoer","%1 unread":"%1 uleste","%1 unread messages":"%1 uleste meldinger","Across %1 open accounts":"I %1 åpne kontoer","%1 accounts · %2 open":"%1 kontoer · %2 åpne","Some account counts are unavailable":"Antall uleste er utilgjengelig for noen kontoer","Not running":"Kjører ikke","Unread unknown":"Ukjent antall uleste","No unread":"Ingen uleste","Focus":"Vis","Launch":"Start","Launching…":"Starter…","Current window":"Aktivt vindu","No visible accounts":"Ingen synlige kontoer","Show closed accounts in Settings":"Vis lukkede kontoer i innstillingene","Saving…":"Lagrer…","Invalid setting.":"Ugyldig innstilling.","Could not save settings. Try again.":"Kunne ikke lagre innstillingene. Prøv igjen.","Settings changed elsewhere. Reopen the account editor.":"Innstillingene ble endret et annet sted. Åpne kontoredigeringen på nytt.","Could not launch the account. Check its browser or launch arguments.":"Kunne ikke starte kontoen. Kontroller nettleser eller startargumenter.","No matching window appeared. Check the account application ID or sign in to Teams.":"Fant ikke et samsvarende vindu. Kontroller kontoens applikasjons-ID eller logg inn i Teams.","↑↓ Choose · Enter Open":"↑↓ Velg · Enter Åpne","Open Teams in a separate browser profile, then select its window here.":"Åpne Teams i en egen nettleserprofil, og velg vinduet her.","Leave advanced arguments as [] to use the browser settings.":"La avanserte argumenter stå som [] for å bruke nettleserinnstillingene.","No matching window yet":"Fant ikke vinduet ennå",
"Use at most 32 accounts.":"Bruk maksimalt 32 kontoer.","Invalid account.":"Ugyldig konto.","Account IDs must be unique.":"Konto-ID-er må være unike.","Enter an account name.":"Skriv inn et kontonavn.","Choose a window or enter its application ID.":"Velg et vindu eller skriv inn applikasjons-ID-en.","This application ID is already assigned to an account.":"Denne applikasjons-ID-en tilhører allerede en konto.","Enter a valid browser profile.":"Skriv inn en gyldig nettleserprofil.","Enter a browser executable without arguments.":"Skriv inn et nettleserprogram uten argumenter.","Enter an HTTPS Teams URL.":"Skriv inn en HTTPS-adresse til Teams.","Enter a JSON array of command arguments, or [].":"Skriv inn en JSON-liste med startargumenter, eller []."
}
function text(label,lang,values) {
  var result=lang==="nb" && Object.prototype.hasOwnProperty.call(norwegian,label) ? norwegian[label] : label
  return result.replace(/%([1-9][0-9]*)/g,function(token,i) { return values && Number(i)<=values.length ? String(values[Number(i)-1]) : token })
}
if (typeof module!=="undefined") module.exports={defaults:defaults,accountError:accountError,valid:valid,value:value,configurationError:configurationError,language:language,text:text}
