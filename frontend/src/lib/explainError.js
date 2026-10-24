/**
 * Server errors, explained to the floor — in French, whatever the UI language.
 *
 * The server speaks English ("None of the selected orders has full stock
 * coverage: #266941 — insufficient stock (45779757236478)") and the floor is
 * Moroccan: the message was forwarded to a manager even when the fix was one
 * move away (that one: 0 free on the pick faces, 1,051 in SLOW ZONE).
 * Ahmed, 2026-10-24: French only.
 *
 * Each rule reads the raw message and returns what happened, what to do, and
 * where to do it. A message no rule knows still gets a French popup, with
 * the original kept for the manager. Add rules here as new messages show up;
 * the server text is the contract, so match on its stable words only.
 */

const ORDER = /(#\d{5,7}(?:-\d)?|J-\d{5,7}(?:-\d)?|SAL-ORD-\d{4}-\d{4,6})/;

function first(re, s) {
  const m = re.exec(s || "");
  return m ? m[1] : "";
}

const RULES = [
  {
    // picking._allocate_and_insert — the screenshot case.
    test: /insufficient stock \(([^)]+)\)|full stock coverage/i,
    build: (raw) => {
      const item = first(/insufficient stock \(([^)]+)\)/i, raw);
      const order = first(ORDER, raw);
      const others = (raw.match(new RegExp(ORDER.source, "g")) || []).filter((o) => o !== order);
      return {
        icon: "package", tone: "warn", stock: item || "",
        title: "Pick list pas créée — stock insuffisant au picking",
        what: (order ? `La commande ${order} ` : "La commande ")
          + "a besoin d'un article qui n'est pas libre sur les étagères de picking."
          + (others.length ? ` Même chose pour : ${[...new Set(others)].join(", ")}.` : ""),
        steps: [
          "Regarde ci-dessous où se trouve l'article.",
          "S'il est en réserve (SLOW, PLT…), ramène quelques pièces vers une étagère avec « Déplacer le stock ».",
          "Puis refais la pick list.",
        ],
      };
    },
  },
  {
    test: /None of the selected orders can be picked|Couldn't pick any of the selected orders/i,
    build: (raw) => ({
      icon: "list-checks", tone: "warn",
      title: "Aucune commande ne peut entrer en pick list",
      what: "Les commandes choisies sont déjà sur une pick list, déjà prélevées, ou n'ont plus rien à prélever.",
      steps: ["Actualise la page : la liste a peut-être changé.", "Choisis d'autres commandes."],
    }),
  },
  {
    test: /Only (\d+) (?:of (\S+) )?in (.+?)(?: — |\.|$)/i,
    build: (raw) => {
      const m = /Only (\d+) (?:of (\S+) )?in (.+?)(?: — |\.|$)/i.exec(raw);
      return {
        icon: "move", tone: "warn", stock: m && m[2] ? m[2] : "",
        title: "Pas assez de pièces dans cet emplacement",
        what: `Le système ne voit que ${m ? m[1] : "peu de"} pièce(s) dans ${m ? m[3].replace(" - JM", "") : "cet emplacement"}.`,
        steps: ["Vérifie l'emplacement de départ choisi.", "Déplace moins de pièces, ou prends-les d'un autre emplacement.",
                "Si les pièces sont bien là, il faut un comptage de cet emplacement."],
        action: { label: "Comptage", route: { name: "CycleCount" } },
      };
    },
  },
  {
    test: /reserved for a sales order/i,
    build: () => ({
      icon: "shield-alert", tone: "warn",
      title: "Pièces réservées à une commande",
      what: "Toutes les pièces restantes ici sont réservées pour des commandes clients.",
      steps: ["Ne les déplace pas : elles attendent leur commande.", "Si la réservation est fausse, demande au manager de la libérer."],
    }),
  },
  {
    test: /Insufficient Stock|units? of Item .*? (?:needed|not available)|Negative Stock|not available in Warehouse/i,
    build: (raw) => ({
      icon: "package", tone: "warn", stock: first(/Item\s+(?:<[^>]+>)?\s*([0-9A-Za-z][\w./-]{3,})/i, raw),
      title: "Le stock du système ne suffit pas",
      what: "Le système ne voit pas assez de pièces de cet article dans l'emplacement demandé.",
      steps: ["Regarde ci-dessous où le système voit l'article.",
              "Si la pièce est physiquement là, il faut un comptage de l'emplacement.",
              "Sinon, déplace des pièces depuis la réserve."],
    }),
  },
  {
    test: /Sales Order (\S+) is (Closed|On Hold)/i,
    build: (raw) => ({
      icon: "shield-alert", tone: "warn",
      title: "Commande fermée dans le système",
      what: `La commande ${first(/Sales Order (\S+)/i, raw)} est fermée (Closed / On Hold) : on ne peut ni la préparer ni l'expédier.`,
      steps: ["Demande à la confirmation de la rouvrir.", "Puis recommence."],
    }),
  },
  {
    test: /has been modified after you opened it|TimestampMismatch|Document has been modified/i,
    build: () => ({
      icon: "refresh-cw", tone: "info",
      title: "Quelqu'un d'autre vient de modifier ce document",
      what: "Un collègue (ou le système) a changé ce document pendant que tu travaillais dessus.",
      steps: ["Actualise la page.", "Refais ton action — tes scans déjà enregistrés sont gardés."],
    }),
  },
  {
    test: /Total Picked Quantity .* more than ordered|more than ordered qty/i,
    build: () => ({
      icon: "minus", tone: "warn",
      title: "Plus de pièces prélevées que commandées",
      what: "La commande a été réduite après la création de la pick list.",
      steps: ["Remets la pièce en trop sur son étagère.", "Actualise et soumets à nouveau."],
    }),
  },
  {
    test: /will get truncated|max characters allowed|CharacterLengthExceeded/i,
    build: () => ({
      icon: "file-text", tone: "warn",
      title: "Nom de produit trop long",
      what: "Le nom d'un produit dépasse la limite du système et bloque l'opération.",
      steps: ["Envoie ce message au manager (bouton « Copier » en bas)."],
    }),
  },
  {
    test: /Not authorized|not permitted|PermissionError|Only a manager|managers? only|Warehouse management only/i,
    build: () => ({
      icon: "shield-alert", tone: "info",
      title: "Action réservée",
      what: "Ton compte n'a pas le droit de faire cette action.",
      steps: ["Demande au manager de la faire, ou de te donner l'accès."],
    }),
  },
  {
    test: /not the (?:assigned )?picker/i,
    build: () => ({
      icon: "user", tone: "info",
      title: "Cette pick list est à un autre préparateur",
      what: "Seul le préparateur assigné (ou un manager) peut faire ça sur cette liste.",
      steps: ["Vérifie que tu as ouvert la bonne pick list.", "Sinon, demande au manager de te l'assigner."],
    }),
  },
  {
    test: /already submitted|already cancelled|is cancelled\.|Already processed/i,
    build: () => ({
      icon: "check", tone: "info",
      title: "Déjà fait",
      what: "Ce document est déjà soumis ou annulé — l'action a déjà été faite.",
      steps: ["Actualise la page pour voir l'état réel."],
    }),
  },
  {
    test: /order is cancelled|was cancelled|it gets no label/i,
    build: (raw) => ({
      icon: "package-x", tone: "warn",
      title: "Commande annulée",
      what: `${first(ORDER, raw) || "Cette commande"} a été annulée par le client.`,
      steps: ["Ne l'emballe pas et ne lui imprime pas d'étiquette.", "Mets la pièce dans le bac des annulations (stop)."],
    }),
  },
  {
    test: /parcel was delivered|process it as a return/i,
    build: () => ({
      icon: "undo-2", tone: "info",
      title: "Colis déjà livré",
      what: "Ce colis a déjà été livré au client.",
      steps: ["Traite-le comme un retour, dans l'écran des retours."],
    }),
  },
  {
    test: /Already handed to the carrier on (\S+)/i,
    build: (raw) => ({
      icon: "truck", tone: "info",
      title: "Déjà remis au transporteur",
      what: `Ce colis est déjà sur le manifeste ${first(/carrier on (\S+)/i, raw)}.`,
      steps: ["Ne le rescanne pas : il est déjà parti ou part avec ce manifeste."],
    }),
  },
  {
    test: /is not a (?:movable|valid|countable|valid target|valid receiving)[\w ]* bin/i,
    build: (raw) => ({
      icon: "map-pin", tone: "warn",
      title: "Emplacement non autorisé ici",
      what: `${(first(/^(.+?) is not a/i, raw) || "Cet emplacement").replace(" - JM", "")} ne peut pas être utilisé pour cette opération (transit, défectueux, conteneur…).`,
      steps: ["Choisis une étagère ou une zone du plateau (SLOW, Réception…)."],
    }),
  },
  {
    test: /holds one consignment supplier's goods only/i,
    build: () => ({
      icon: "building", tone: "warn",
      title: "Section d'un fournisseur en dépôt",
      what: "Cette section ne reçoit que les produits de son fournisseur.",
      steps: ["Range la pièce dans la section de son propre fournisseur (CN - …)."],
    }),
  },
  {
    test: /Unknown (?:order|item|parcel|pick list|receipt|shipment)|Unknown item:/i,
    build: () => ({
      icon: "scan-barcode", tone: "info",
      title: "Code non reconnu",
      what: "Le code scanné ou tapé ne correspond à rien dans le système.",
      steps: ["Rescanne le code, ou tape-le à la main.", "Vérifie que c'est bien l'étiquette de cette pièce / ce colis."],
    }),
  },
  {
    test: /Too many/i,
    build: () => ({
      icon: "layers", tone: "info",
      title: "Trop d'éléments en une fois",
      what: "L'opération dépasse le maximum autorisé en un seul coup.",
      steps: ["Fais-la en plusieurs fois, par petits groupes."],
    }),
  },
  {
    test: /only \d+ expected|not on this PO|beyond its pending|Nothing to receive|no longer waiting for its supplier/i,
    build: () => ({
      icon: "truck", tone: "warn",
      title: "Plus de pièces que prévu",
      what: "Tu réceptionnes plus de pièces que la commande fournisseur n'en attend.",
      steps: ["Recompte les pièces.", "Les pièces en trop retournent au fournisseur, ou demande au manager."],
    }),
  },
  {
    test: /delivery ID|Cathedis|import des livraisons|AWB/i,
    build: () => ({
      icon: "truck", tone: "warn",
      title: "Le transporteur a refusé l'étiquette",
      what: "Cathedis n'a pas accepté la création du colis.",
      steps: ["Vérifie la ville et l'adresse du client, puis réessaie.",
              "Si ça refuse encore avec une ville correcte, envoie ce message au manager."],
    }),
  },
  {
    test: /rate must be above zero|valuation rate/i,
    build: () => ({
      icon: "dollar-sign", tone: "warn",
      title: "Prix d'achat manquant",
      what: "L'article n'a pas de prix d'achat : le système ne peut pas l'enregistrer.",
      steps: ["Demande aux achats de mettre le prix, puis recommence."],
    }),
  },
  {
    test: /batch|Serial and Batch/i,
    build: () => ({
      icon: "scan-barcode", tone: "warn",
      title: "Problème de lot (batch)",
      what: "Cet article est suivi par lot et le lot ne correspond pas au stock.",
      steps: ["Envoie ce message au manager (bouton « Copier » en bas)."],
    }),
  },
];

/** The French explanation for a raw server message — always returns one. */
export function explainError(raw) {
  const s = String(raw || "");
  for (const r of RULES) {
    if (r.test.test(s)) return { known: true, ...r.build(s) };
  }
  return {
    known: false, icon: "alert-triangle", tone: "warn",
    title: "L'opération n'a pas abouti",
    what: "Le système a refusé cette action. Le message technique est en bas.",
    steps: ["Réessaie une fois.", "Si ça bloque encore, copie le message (bouton en bas) et envoie-le au manager."],
  };
}
