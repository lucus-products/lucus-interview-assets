/**
 * generate_random 工具：生成指定范围内的随机整数。
 */

// 工具定义（MCP tools/list 时返回）
export const RANDOM_TOOL = {
  name: "generate_random",
  description: "生成一个指定范围内的随机整数",
  inputSchema: {
    type: "object",
    properties: {
      min: { type: "number", description: "最小值" },
      max: { type: "number", description: "最大值" },
    },
    required: ["min", "max"],
  },
};

// 工具执行逻辑（CallTool 时触发）
export function handleRandom(
  args: Record<string, unknown> | undefined,
): { content: { type: string; text: string }[] } {
  const min = args?.min as number;
  const max = args?.max as number;
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    throw new Error("min / max 必须为数字");
  }

  const lo = Math.min(min, max);
  const hi = Math.max(min, max);
  const random = Math.floor(Math.random() * (hi - lo + 1)) + lo;
  return {
    content: [{ type: "text", text: `Your random number is: ${random}` }],
  };
}
