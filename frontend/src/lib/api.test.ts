import { afterEach, describe, expect, it, vi } from "vitest";
import { streamRagAsk } from "./api";

describe("streamRagAsk", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("在 SSE 不可用时回退到普通 POST", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ answer: "fallback" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const events: unknown[] = [];

    await streamRagAsk("找项目", undefined, new AbortController().signal, (event) => events.push(event));

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/v1/rag/ask/stream", "/v1/rag/ask"]);
    expect(events).toEqual([{ event: "final", data: { answer: "fallback" } }]);
  });

  it("在 EOF 时解析未以空行结束的尾帧", async () => {
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('event: final\ndata: {"answer":"tail"}'));
        controller.close();
      },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(stream, { status: 200 })));
    const events: unknown[] = [];

    await streamRagAsk("找项目", undefined, new AbortController().signal, (event) => events.push(event));

    expect(events).toEqual([{ event: "final", data: { answer: "tail" } }]);
  });
});
