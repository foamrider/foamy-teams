// The plugin catalogs through the kit's FoamyI18nText, the same substitution
// and plural code FoamyI18n runs in the panel, for pure node tests.
const I18nText = require('../kit/node-loader.cjs').load('FoamyI18nText');
const en = require('../i18n/en.json');
const no = require('../i18n/no.json');
const number = (v, d) => (d === undefined ? String(v) : Number(v).toFixed(d));
const translators = { en: I18nText.translator(en, en, number), no: I18nText.translator(no, en, number) };
function scope(language) { return language === 'no' || language === 'nb' ? translators.no : translators.en; }
function text(key, language, values) { return scope(language).t(key, values); }
function plural_text(key, count, language) { return scope(language).tn(key, count); }
module.exports = { text, tn: plural_text, no, en, norwegian: no, nb: no };
