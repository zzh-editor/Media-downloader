import { type Plugin, tool } from "@opencode-ai/plugin"
import { spawn } from "child_process"

export default (async ({ directory }) => {
  return {
    tool: {
      bash_stream: tool({
        description:
          "执行 shell 命令并实时显示进度动画。" +
          "适用：yt-dlp/gallery-dl 下载、ffmpeg 转码等长时间任务。" +
          "短命令请用 Bash。",
        args: {
          command: tool.schema.string().describe("要执行的 shell 命令"),
          description: tool.schema.string().optional()
            .describe("描述，帮助用户理解命令意图"),
          timeout: tool.schema.number().optional()
            .describe("超时（毫秒），超时后终止进程"),
          workdir: tool.schema.string().optional()
            .describe("工作目录，默认当前项目目录"),
        },
        async execute(args, ctx) {
          const cwd = args.workdir || directory || "."
          const cmd = args.command

          const child = spawn("bash", ["-c", cmd], { cwd, stdio: ["pipe", "pipe", "pipe"] })

          if (args.timeout) {
            const timer = setTimeout(() => {
              if (!ctx.abort.aborted) child.kill(9)
            }, args.timeout)
            ctx.abort.addEventListener("abort", () => {
              clearTimeout(timer)
              child.kill(9)
            })
          }

          const pctRegex = /(\d+(?:\.\d+)?)%/g
          let stdoutResult = ""

          child.stderr.on("data", (chunk: Buffer) => {
            const text = chunk.toString()
            const matches = [...text.matchAll(pctRegex)]
            if (matches.length > 0) {
              ctx.metadata({
                metadata: {
                  pct: matches[matches.length - 1][1],
                },
              })
            }
          })

          child.stdout.on("data", (chunk: Buffer) => {
            stdoutResult += chunk.toString()
          })

          await new Promise<void>((resolve) => {
            child.on("exit", () => resolve())
            child.on("error", () => resolve())
          })

          return stdoutResult || "(command completed)"
        },
      }),
    },

    "tool.definition": async (input, output) => {
      if (input.toolID === "Bash") {
        output.description =
          "执行 shell 命令并返回输出。" +
          "对于 yt-dlp/gallery-dl 下载、ffmpeg 转码等长时间任务，" +
          "建议使用 bash_stream 以实时显示进度。"
      }
    },
  }
}) satisfies Plugin
