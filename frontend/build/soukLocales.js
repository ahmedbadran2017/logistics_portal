// The souk bundle imported the whole portal dictionary (en+fr+ar, ~600 KB —
// a third of the buyer's download) for the ~15 namespaces its screens use.
// For the souk pass only, this keeps the top-level namespaces that some file
// the souk app can reach names in a key ("nav.soukBuy", t(`lb.${x}`)), and
// drops the rest. Over-keeping is harmless; a missing namespace would show
// the raw key — the scan follows the real import graph from souk/main.js.
import fs from "fs";
import path from "path";

// The files the souk app can actually reach: follow static and dynamic
// imports from its entry (the `@/` alias and relative paths; packages skipped).
function graph(src, entry) {
  const seen = new Set();
  const stack = [entry];
  const resolve = (from, spec) => {
    let base;
    if (spec.startsWith("@/")) base = path.join(src, spec.slice(2));
    else if (spec.startsWith(".")) base = path.resolve(path.dirname(from), spec);
    else return null;
    for (const c of [base, base + ".js", base + ".vue", path.join(base, "index.js")])
      if (fs.existsSync(c) && fs.statSync(c).isFile()) return c;
    return null;
  };
  while (stack.length) {
    const f = stack.pop();
    if (seen.has(f)) continue;
    seen.add(f);
    const code = fs.readFileSync(f, "utf8");
    for (const m of code.matchAll(/(?:\bfrom\s*|\bimport\s*\(\s*|\bimport\s+)["']([^"']+)["']/g)) {
      const r = resolve(f, m[1]);
      if (r && !seen.has(r)) stack.push(r);
    }
  }
  return [...seen];
}

function namespacesUsed(src) {
  const keep = new Set(["brand", "souk"]);
  for (const f of graph(src, path.join(src, "souk", "main.js"))) {
    if (/[\\/]locales[\\/]/.test(f)) continue;
    const code = fs.readFileSync(f, "utf8");
    for (const m of code.matchAll(/["'`]([a-zA-Z][a-zA-Z0-9_]*)\.(?:[a-zA-Z0-9_$]|\$\{)/g)) keep.add(m[1]);
  }
  return keep;
}

export default function soukLocales(src) {
  let keep = null;
  return {
    name: "souk-locales",
    enforce: "pre",
    buildStart() { keep = namespacesUsed(src); },
    transform(code, id) {
      if (!/[\\/]src[\\/]locales[\\/](en|fr|ar)\.js$/.test(id)) return null;
      const ast = this.parse(code);
      const decl = ast.body.find((n) => n.type === "ExportDefaultDeclaration");
      if (!decl || decl.declaration.type !== "ObjectExpression") return null;
      const props = decl.declaration.properties.filter((p) => {
        const k = p.key && (p.key.name || p.key.value);
        return k && keep.has(k);
      });
      const body = props.map((p) => code.slice(p.start, p.end)).join(",\n");
      return { code: `export default {\n${body}\n};\n`, map: null };
    },
  };
}
