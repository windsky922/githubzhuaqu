import { afterEach, describe, expect, it, vi } from "vitest";
import { assistantTurnBody, projectAssistantState, streamAssistantTurn, streamRagAsk } from "./api";
import type { AssistantState } from "./types";

const state: AssistantState = {
  schema_version: 1, revision: 1, goal: "找 Agent", constraints: [],
  knowledge_context: { topic: "Agent 核心组成", outline: [{ id: "k1", title: "模型" }, { id: "k2", title: "工具" }], focus_id: "k2" },
  candidate_repository_ids: ["owner/agent"], primary_repository_id: "owner/agent",
  last_intent: "project_search", pending_question: "",
  source_identity: { kind: "weekly_snapshot", source_id: "source:1", run_date: "2026-08-09", as_of: "2026-08-09" },
  mode: "hybrid", resumable: true,
};
const dirtyState = {
  ...state,
  knowledge_context: { ...(state.knowledge_context || {}), history: "forbidden-knowledge", focus_id: "missing" },
  constraints: [{ field: "language", operator: "eq", value: "Python", hard: true, evidence: "forbidden-constraint" }],
  source_identity: { ...state.source_identity, prompt_context: "forbidden-source" },
  answer: "forbidden-answer", citations: ["forbidden-citation"], evidence: ["forbidden-evidence"],
} as unknown as AssistantState;

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

describe("streamAssistantTurn", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends only the current question and server assistant state", () => {
    const projected = projectAssistantState(dirtyState);
    const body = assistantTurnBody("刚才哪个更适合", dirtyState);
    expect(body).toEqual({ q: "刚才哪个更适合", state: projected, mode: "hybrid", limit: 3 });
    const raw = JSON.stringify(body);
    for (const forbidden of ["forbidden-answer", "forbidden-citation", "forbidden-evidence", "forbidden-source", "forbidden-constraint", "forbidden-knowledge", "prompt_context", "auto_build"]) expect(raw).not.toContain(forbidden);
    expect(projected?.schema_version).toBe(2);
    expect(projected?.knowledge_context).toEqual({ topic: "Agent 核心组成", outline: [{ id: "k1", title: "模型" }, { id: "k2", title: "工具" }], focus_id: "" });
    expect(projected?.constraints).toEqual([{ field: "language", operator: "eq", value: "Python", hard: true }]);
  });

  it("uses assistant endpoints for stream and fallback with identical state", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ answer: "fallback", assistant_state: state }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const events: unknown[] = [];
    await streamAssistantTurn("继续", dirtyState, new AbortController().signal, (event) => events.push(event));
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/v1/assistant/turn/stream", "/v1/assistant/turn"]);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(assistantTurnBody("继续", dirtyState));
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual(assistantTurnBody("继续", dirtyState));
    expect(fetchMock.mock.calls[0][1].body).not.toContain("forbidden-answer");
    expect(events).toEqual([{ event: "final", data: { answer: "fallback", assistant_state: state } }]);
  });

  it("keeps the authoritative final and parses an EOF tail frame", async () => {
    const stream = new ReadableStream({ start(controller) {
      controller.enqueue(new TextEncoder().encode(`event: final\ndata: ${JSON.stringify({ answer: "tail", assistant_state: state })}`));
      controller.close();
    } });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(stream, { status: 200 })));
    const events: unknown[] = [];
    await streamAssistantTurn("继续", state, new AbortController().signal, (event) => events.push(event));
    expect(events).toEqual([{ event: "final", data: { answer: "tail", assistant_state: state } }]);
  });

  it("recovers a silent EOF with the identical POST body", async () => {
    const stream = new ReadableStream({ start(controller) {
      controller.enqueue(new TextEncoder().encode('event: meta\ndata: {"assistant_mode":"knowledge"}\n\n'));
      controller.close();
    } });
    const fallback = { answer: "recovered", assistant_state: state };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(stream, { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(fallback), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const events: unknown[] = [];

    await streamAssistantTurn("继续", dirtyState, new AbortController().signal, (event) => events.push(event));

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/v1/assistant/turn/stream", "/v1/assistant/turn"]);
    expect(fetchMock.mock.calls[0][1].body).toBe(fetchMock.mock.calls[1][1].body);
    expect(events).toEqual([
      { event: "meta", data: { assistant_mode: "knowledge" } },
      { event: "final", data: fallback },
    ]);
  });

  it("recovers after partial delta EOF without accepting the incomplete turn", async () => {
    const stream = new ReadableStream({ start(controller) {
      controller.enqueue(new TextEncoder().encode(
        'event: meta\ndata: {"assistant_mode":"knowledge"}\n\nevent: delta\ndata: {"text":"partial"}\n\n',
      ));
      controller.close();
    } });
    const fallback = { answer: "complete", assistant_state: state };
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response(stream, { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(fallback), { status: 200 })));
    const events: unknown[] = [];

    await streamAssistantTurn("继续", state, new AbortController().signal, (event) => events.push(event));

    expect(events).toEqual([
      { event: "meta", data: { assistant_mode: "knowledge" } },
      { event: "delta", data: { text: "partial" } },
      { event: "final", data: fallback },
    ]);
  });

  it("rejects duplicate final frames and uses one authoritative POST final", async () => {
    const streamed = { answer: "streamed", assistant_state: state };
    const fallback = { answer: "authoritative", assistant_state: state };
    const stream = new ReadableStream({ start(controller) {
      controller.enqueue(new TextEncoder().encode(
        `event: final\ndata: ${JSON.stringify(streamed)}\n\nevent: final\ndata: ${JSON.stringify(streamed)}\n\n`,
      ));
      controller.close();
    } });
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response(stream, { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(fallback), { status: 200 })));
    const events: unknown[] = [];

    await streamAssistantTurn("继续", state, new AbortController().signal, (event) => events.push(event));

    expect(events).toEqual([{ event: "final", data: fallback }]);
  });

  it("rejects malformed final data and recovers through POST", async () => {
    const stream = new ReadableStream({ start(controller) {
      controller.enqueue(new TextEncoder().encode('event: final\ndata: {"answer":"missing state"}\n\n'));
      controller.close();
    } });
    const fallback = { answer: "valid", assistant_state: state };
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response(stream, { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(fallback), { status: 200 })));
    const events: unknown[] = [];

    await streamAssistantTurn("继续", state, new AbortController().signal, (event) => events.push(event));

    expect(events).toEqual([{ event: "final", data: fallback }]);
  });

  it("does not mark an incomplete stream successful when POST recovery also fails", async () => {
    const stream = new ReadableStream({ start(controller) {
      controller.enqueue(new TextEncoder().encode('event: delta\ndata: {"text":"partial"}\n\n'));
      controller.close();
    } });
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response(stream, { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 503 })));
    const events: Array<{ event: string }> = [];

    await expect(streamAssistantTurn(
      "继续",
      state,
      new AbortController().signal,
      (event) => events.push(event),
    )).rejects.toThrow("HTTP 503");

    expect(events).toEqual([{ event: "delta", data: { text: "partial" } }]);
    expect(events.some((event) => event.event === "final")).toBe(false);
  });
});
