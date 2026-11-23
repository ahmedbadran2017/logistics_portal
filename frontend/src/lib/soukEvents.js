// The product's "what happened" log is the Comment trail the backend writes
// (api/souk.py add_comment) — in English, because the Desk and the accountant
// read the same trail. On the souk screens it is shown in the reader's
// language: each comment is a " · "-separated run of fragments, and every
// fragment the backend writes has a pattern here. A fragment nobody knows
// (a free-text reason, a document name) is shown as written.

const W = {
  fr: {
    bought: "acheté chez {1}", boughtAgain: "racheté chez {1}", pcs: "{1} pièces", trip: "voyage {1}", by: "par {1}",
    draft: "brouillon Shopify {1} créé", vendor: "marque {1}", variants: "{1} variantes",
    waitRecv: "en attente de réception", paid: "{1} + payée {2}", took: "{1} l'a pris ({2})",
    received: "{1} bonnes reçues sur {2}", toStudio: "{1} au studio",
    brokenStall: "{1} cassées chez le marchand", brokenTransport: "{1} cassées au transport", brokenWh: "{1} cassées à l'entrepôt",
    short: "{1} manquantes", nothing: "rien de notre commande n'est arrivé", owes: "le marchand doit {1} MAD", labels: "{1} étiquettes",
    inhouse: "{1} photos internes par {2}", toMarketing: "vers le marketing", sentBackPhotos: "renvoyé aux photos internes par {1}",
    movedBack: "renvoyé de {1} à {2} par {3}", rawStudio: "photo interne {1} pendant le studio par {2}",
    rawContent: "photo interne {1} pendant le contenu par {2}", finalContent: "photo pro {1} pendant le contenu par {2}",
    finalsUpdated: "{1} photos pro mises à jour sur le brouillon Shopify par {2}", removed: "retirée",
    retaken: "reprise", added: "ajoutée",
    finals: "{1} photos finales sur le brouillon Shopify par {2}", toContent: "vers le contenu",
    content: "contenu sur le brouillon Shopify par {1}", arabicMissing: "arabe PAS sur Shopify ({1})", toReview: "vers la relecture",
    reviewBack: "la relecture l'a renvoyé à {1} ({2}×) par {3}",
    dropReturn: "ne sera PAS publié (retour au marchand) par {1}", dropClear: "ne sera PAS publié (liquidation) par {1}",
    live: "EN LIGNE par {1} sur {2}", samplesBack: "{1} échantillon(s) du studio remis en rayon",
    samplesLeft: "échantillons restés au studio (aucun rayon pour cet article) : {1}",
    samplesStuck: "échantillons encore au studio — à déplacer à la main ({1})",
    cash: "espèces", cheque: "chèque", transfer: "virement", credit: "à crédit", due: "échéance",
  },
  ar: {
    bought: "تم الشراء من {1}", boughtAgain: "إعادة الشراء من {1}", pcs: "{1} قطعة", trip: "رحلة الشراء {1}", by: "بواسطة {1}",
    draft: "تم إنشاء مسودة على شوبيفاي {1}", vendor: "العلامة التجارية {1}", variants: "{1} خيار",
    waitRecv: "بانتظار الاستلام", paid: "{1} + فاتورة مدفوعة {2}", took: "تولّاه {1} ({2})",
    received: "تم استلام {1} سليم على {2}", toStudio: "{1} إلى الاستوديو",
    brokenStall: "{1} تالف لدى التاجر", brokenTransport: "{1} تالف أثناء النقل", brokenWh: "{1} تالف في المستودع",
    short: "{1} ناقص", nothing: "لم يصل شيء من طلبيتنا", owes: "مستحق على التاجر {1} MAD", labels: "{1} ملصق",
    inhouse: "{1} صورة داخلية بواسطة {2}", toMarketing: "أُحيل إلى التسويق", sentBackPhotos: "أُعيد إلى التصوير الداخلي بواسطة {1}",
    movedBack: "أُعيد من {1} إلى {2} بواسطة {3}", rawStudio: "صورة داخلية {1} أثناء مرحلة الاستوديو بواسطة {2}",
    rawContent: "صورة داخلية {1} أثناء مرحلة المحتوى بواسطة {2}", finalContent: "صورة احترافية {1} أثناء مرحلة المحتوى بواسطة {2}",
    finalsUpdated: "حُدّثت {1} صورة احترافية على مسودة شوبيفاي بواسطة {2}", removed: "حُذفت",
    retaken: "أُعيد تصويرها", added: "أُضيفت",
    finals: "{1} صورة احترافية على مسودة شوبيفاي بواسطة {2}", toContent: "أُحيل إلى المحتوى",
    content: "كُتب المحتوى على مسودة شوبيفاي بواسطة {1}", arabicMissing: "النص العربي غير موجود على شوبيفاي ({1})", toReview: "أُحيل إلى المراجعة",
    reviewBack: "أعادته المراجعة إلى {1} ({2}×) بواسطة {3}",
    dropReturn: "مستبعد من النشر (إرجاع للتاجر) بواسطة {1}", dropClear: "مستبعد من النشر (تصفية) بواسطة {1}",
    live: "نُشر بواسطة {1} على {2}", samplesBack: "أُعيدت {1} عينة من الاستوديو إلى الرف",
    samplesLeft: "عينات بقيت في الاستوديو (لا يوجد رف لهذا الصنف): {1}",
    samplesStuck: "العينات لا تزال في الاستوديو — يجب نقلها يدويًا ({1})",
    cash: "نقدًا", cheque: "شيك", transfer: "تحويل بنكي", credit: "بالأجل", due: "تاريخ الاستحقاق",
  },
};

// [pattern on one fragment, key]. Groups fill {1}, {2}, {3}.
const P = [
  [/^bought again from (.+)$/, "boughtAgain"],
  [/^bought from (.+)$/, "bought"],
  [/^([\d,.]+) pcs$/, "pcs"],
  [/^trip (.+)$/, "trip"],
  [/^Shopify Draft (\S+) created$/, "draft"],
  [/^vendor (.+)$/, "vendor"],
  [/^(\d+) variants$/, "variants"],
  [/^waiting for receiving$/, "waitRecv"],
  [/^(\S+) \+ paid (\S+)$/, "paid"],
  [/^(.+) took it \((\w+)\)$/, "took"],
  [/^received (\d+) good on (.+?)(?: \((\d+) to the studio\))?$/, "received"],
  [/^(\d+) broken at the stall$/, "brokenStall"],
  [/^(\d+) broken in transport$/, "brokenTransport"],
  [/^(\d+) broken in the warehouse$/, "brokenWh"],
  [/^(\d+) short$/, "short"],
  [/^nothing of ours arrived$/, "nothing"],
  [/^the stall owes ([\d,.]+) MAD(?: \((.+)\))?$/, "owes"],
  [/^(\d+) labels$/, "labels"],
  [/^(\d+) in-house photos by (.+)$/, "inhouse"],
  [/^to marketing$/, "toMarketing"],
  [/^sent back to in-house photos by (.+)$/, "sentBackPhotos"],
  [/^sent back from (\w+) to (\w+) by (.+)$/, "movedBack"],
  [/^in-house photo (retaken|added) during the studio by (.+)$/, "rawStudio"],
  [/^in-house photo (retaken|added) during the content by (.+)$/, "rawContent"],
  [/^final photo (added|removed) during the content by (.+)$/, "finalContent"],
  [/^(\d+) final photos updated on the Shopify Draft by (.+)$/, "finalsUpdated"],
  [/^(\d+) final photos on the Shopify Draft by (.+)$/, "finals"],
  [/^to content$/, "toContent"],
  [/^content on the Shopify Draft by (.+)$/, "content"],
  [/^Arabic NOT on Shopify \((.*)\)$/, "arabicMissing"],
  [/^to review$/, "toReview"],
  [/^review sent it back to (\w+) \((\d+)×\) by (.+)$/, "reviewBack"],
  [/^will NOT be published \(back to the stall\) by (.+)$/, "dropReturn"],
  [/^will NOT be published \(clearance\) by (.+)$/, "dropClear"],
  [/^LIVE by (.+?) on (.+)$/, "live"],
  [/^(\d+) studio sample\(s\) back on the shelf$/, "samplesBack"],
  [/^samples left in the studio \(no shelf holds this item\): (.+)$/, "samplesLeft"],
  [/^samples still in the studio — move them by hand \((.*)\)$/, "samplesStuck"],
  [/^by (.+)$/, "by"],
  // how the stall is paid (api/souk.py _pay_text): method [ref] [due date]
  [/^(cash|cheque|transfer|on credit)(?: (?!due )(\S+))?(?: due (\S+))?$/, "pay"],
];

function fragment(f, words, stageName) {
  const s = f.replace(/\.$/, "");
  for (const [re, key] of P) {
    const m = re.exec(s);
    if (!m) continue;
    if (key === "pay") {
      const meth = words[m[1] === "on credit" ? "credit" : m[1]];
      return [meth, m[2], m[3] ? `${words.due} ${m[3]}` : ""].filter(Boolean).join(" ");
    }
    let out = words[key];
    for (let i = 1; i <= 3; i++) {
      let v = m[i] == null ? "" : m[i];
      if ((key === "took" && i === 2) || (key === "reviewBack" && i === 1) || (key === "movedBack" && i < 3)) v = stageName(v);
      if (["rawStudio", "rawContent", "finalContent"].includes(key) && i === 1) v = words[v] || v;
      out = out.replace(`{${i}}`, v);
    }
    // received … (n to the studio) and owes … (debit note) carry an optional tail.
    if (key === "received" && m[3]) out += ` (${words.toStudio.replace("{1}", m[3])})`;
    if (key === "owes" && m[2]) out += ` (${m[2]})`;
    return out;
  }
  return f;
}

/** The comment in the reader's language; English (or unknown) as written. */
export function eventText(text, locale, stageName = (s) => s) {
  const raw = String(text || "").replace(/^\s*Souk:\s*/, "");
  const words = W[locale];
  if (!words) return raw;
  return raw.split(" · ").map((f) => fragment(f.trim(), words, stageName)).join(" · ");
}
