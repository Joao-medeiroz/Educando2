/**
 * Gera backend/data/oportunidades.json a partir de assets/js/dados-oportunidades.js.
 *
 * Fonte da verdade: assets/js/dados-oportunidades.js (edite só este arquivo).
 * Uso (na raiz do projeto):
 *   node backend/scripts/exportar_oportunidades.js           -> gera o JSON
 *   node backend/scripts/exportar_oportunidades.js --verificar -> falha se o JSON estiver desatualizado
 */
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..", "..");
const origem = path.join(raiz, "assets", "js", "dados-oportunidades.js");
const destino = path.join(raiz, "backend", "data", "oportunidades.json");

const codigo = fs.readFileSync(origem, "utf8");
const janela = {};
new Function("window", codigo)(janela);

if (!janela.OPORTUNIDADES) {
  console.error("Erro: window.OPORTUNIDADES não foi definido em dados-oportunidades.js");
  process.exit(1);
}

const conteudo = JSON.stringify(janela.OPORTUNIDADES, null, 2) + "\n";

if (process.argv.includes("--verificar")) {
  const atual = fs.existsSync(destino) ? fs.readFileSync(destino, "utf8") : "";
  if (atual !== conteudo) {
    console.error("JSON desatualizado. Rode: node backend/scripts/exportar_oportunidades.js");
    process.exit(1);
  }
  console.log("JSON sincronizado com dados-oportunidades.js");
} else {
  fs.writeFileSync(destino, conteudo, "utf8");
  console.log("Gerado:", path.relative(raiz, destino));
}
