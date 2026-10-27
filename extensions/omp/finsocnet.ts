import { execFile } from "child_process";
import { promisify } from "util";

const execFileAsync = promisify(execFile);

interface ExtensionCommandContext {
  ui?: {
    notify?: (message: string, level?: "info" | "warning" | "error") => void;
  };
  session?: {
    sendUserMessage?: (message: string) => void;
  };
  reply?: (message: string) => void;
  send?: (msg: { role: string; content: string }) => void;
}

interface CommandOptions {
  description: string;
  handler: (args: string, ctx: ExtensionCommandContext) => Promise<void>;
}

interface PiAPI {
  registerCommand?: (name: string, options: CommandOptions) => void;
}

export default function (pi: unknown): void {
  if (!pi || typeof pi !== "object" || !("registerCommand" in pi)) return;
  const api = pi as PiAPI;
  if (typeof api.registerCommand !== "function") return;

  api.registerCommand("finsocnet", {
    description:
      "Explore creator trading hypotheses (e.g. /finsocnet search 'breakout', /finsocnet view 2, /finsocnet stats)",
    handler: async (args: string, ctx: ExtensionCommandContext): Promise<void> => {
      const raw = (args || "").trim();
      let cmdArgs: string[] = [];

      if (raw.length === 0) {
        cmdArgs = ["stats"];
      } else {
        const match = raw.match(/(?:[^\s"']+|"[^"]*"|'[^']*')+/g);
        if (match) {
          cmdArgs = match.map((s) => s.replace(/^['"]|['"]$/g, ""));
        } else {
          cmdArgs = raw.split(/\s+/);
        }
      }

      try {
        const { stdout, stderr } = await execFileAsync("finsocnet", cmdArgs, {
          timeout: 45000,
        });
        const output = (stdout || stderr || "").trim();

        if (ctx.ui?.notify) {
          ctx.ui.notify("FinSocNet executed successfully", "info");
        }

        if (typeof ctx.session?.sendUserMessage === "function") {
          ctx.session.sendUserMessage(`[FinSocNet]\n\`\`\`\n${output}\n\`\`\``);
        } else if (typeof ctx.reply === "function") {
          ctx.reply(`[FinSocNet]\n\`\`\`\n${output}\n\`\`\``);
        } else if (typeof ctx.send === "function") {
          ctx.send({
            role: "user",
            content: `[FinSocNet]\n\`\`\`\n${output}\n\`\`\``,
          });
        }
      } catch (err: unknown) {
        let msg = "Unknown error occurred";
        if (err instanceof Error) {
          if ("stderr" in err && typeof err.stderr === "string" && err.stderr.length > 0) {
            msg = err.stderr;
          } else {
            msg = err.message;
          }
        } else if (typeof err === "string") {
          msg = err;
        }

        if (ctx.ui?.notify) {
          ctx.ui.notify(`FinSocNet error: ${msg}`, "error");
        }
      }
    },
  });
}
