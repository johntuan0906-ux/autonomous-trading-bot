/*
 * Copilot LM Bridge — extension nho de bot Python dung duoc GitHub Copilot
 * (`vscode.lm`) qua localhost, KHONG can API key rieng.
 *
 * Vi sao phai la extension: tai lieu VS Code chi mo Language Model API cho
 * extension chay trong extension host (`vscode.lm.selectChatModels`), khong co
 * endpoint HTTP cong khai. Python (agents.py, provider `vscode_lm`) chi POST JSON
 * toi 127.0.0.1:<port>/complete.
 *
 * An toan:
 *  - Chi listen 127.0.0.1 (khong ra mang ngoai).
 *  - Token tuy chon (Authorization: Bearer ...).
 *  - Khong bao gio tra ve loi ra ngoai kieu lam treo client: luon co HTTP status.
 *  - Nguon du lieu gui di chi la prompt cua bot (chi so thi truong), khong co key.
 */
const vscode = require("vscode");
const http = require("http");

let server = null;

function getCfg() {
    const c = vscode.workspace.getConfiguration("copilotLmBridge");
    return { port: c.get("port", 8765), token: c.get("token", ""), model: c.get("model", "") };
}

async function askCopilot(system, prompt, modelHint) {
    const selector = modelHint ? { vendor: "copilot", id: modelHint } : { vendor: "copilot" };
    let models = await vscode.lm.selectChatModels(selector);
    if (!models.length) models = await vscode.lm.selectChatModels({});
    if (!models.length) throw new Error("khong co model Copilot nao (da dang nhap Copilot?)");
    const model = models[0];
    const messages = [
        vscode.LanguageModelChatMessage.User(system + "\n\n" + prompt)
    ];
    const res = await model.sendRequest(messages, {}, new vscode.CancellationTokenSource().token);
    let out = "";
    for await (const part of res.stream) {
        if (part && typeof part.value === "string") out += part.value;
    }
    return { text: out.trim(), model: model.id || model.name || "copilot" };
}

function start() {
    if (server) return;
    const { port, token, model } = getCfg();
    server = http.createServer((req, res) => {
        const json = (code, obj) => {
            const body = JSON.stringify(obj);
            res.writeHead(code, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) });
            res.end(body);
        };
        if (req.method !== "POST" || !req.url.startsWith("/complete")) return json(404, { error: "not found" });
        if (token && (req.headers.authorization || "") !== "Bearer " + token) return json(401, { error: "bad token" });
        let raw = "";
        req.on("data", (d) => { raw += d; if (raw.length > 200000) req.destroy(); });
        req.on("end", async () => {
            try {
                const body = JSON.parse(raw || "{}");
                const out = await askCopilot(body.system || "", body.prompt || "", body.model || model);
                json(200, { text: out.text, model: out.model });
            } catch (e) {
                json(500, { error: String(e && e.message ? e.message : e).slice(0, 300) });
            }
        });
    });
    server.listen(port, "127.0.0.1", () => {
        vscode.window.showInformationMessage(`Copilot LM Bridge dang chay: http://127.0.0.1:${port}/complete`);
    });
}

function stop() {
    if (!server) return;
    server.close();
    server = null;
}

function activate(context) {
    context.subscriptions.push(
        vscode.commands.registerCommand("copilotLmBridge.start", start),
        vscode.commands.registerCommand("copilotLmBridge.stop", stop),
        { dispose: stop }
    );
}

module.exports = { activate, deactivate: stop };
