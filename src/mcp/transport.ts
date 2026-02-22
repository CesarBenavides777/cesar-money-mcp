import type { Transport } from "@modelcontextprotocol/sdk/shared/transport.js";
import type { JSONRPCMessage } from "@modelcontextprotocol/sdk/types.js";

/**
 * A lightweight HTTP transport for MCP that works with Hono/Bun.
 *
 * Bridges individual HTTP requests to the MCP Server's transport interface.
 * Each JSON-RPC request gets a response via a Promise-based dispatch.
 */
export class HttpTransport implements Transport {
  private pendingResponses = new Map<
    string | number,
    (response: JSONRPCMessage) => void
  >();

  onmessage?: (message: JSONRPCMessage) => void;
  onclose?: () => void;
  onerror?: (error: Error) => void;

  async start(): Promise<void> {
    // No-op — HTTP transport is request-driven
  }

  async close(): Promise<void> {
    // Reject any pending responses
    for (const [id, resolve] of this.pendingResponses) {
      resolve({
        jsonrpc: "2.0",
        id: id as string | number,
        error: { code: -32000, message: "Transport closed" },
      } as JSONRPCMessage);
    }
    this.pendingResponses.clear();
    this.onclose?.();
  }

  async send(message: JSONRPCMessage): Promise<void> {
    // The MCP server sends a response — route it to the waiting HTTP request
    if ("id" in message && message.id !== undefined && message.id !== null) {
      const resolver = this.pendingResponses.get(message.id);
      if (resolver) {
        resolver(message);
        this.pendingResponses.delete(message.id);
      }
    }
    // Notifications (no id) are ignored in HTTP mode
  }

  /**
   * Handle an incoming JSON-RPC request from an HTTP POST.
   * Returns the JSON-RPC response to send back to the client.
   */
  async handleJsonRpc(body: JSONRPCMessage): Promise<JSONRPCMessage> {
    if (!("id" in body) || body.id === undefined) {
      // Notification — no response expected
      this.onmessage?.(body);
      return {
        jsonrpc: "2.0",
        id: null,
        result: {},
      } as unknown as JSONRPCMessage;
    }

    return new Promise<JSONRPCMessage>((resolve) => {
      // Set up response handler BEFORE dispatching the message
      this.pendingResponses.set(body.id as string | number, resolve);

      // Dispatch to MCP server
      this.onmessage?.(body);

      // Safety timeout — don't hang forever
      setTimeout(() => {
        if (this.pendingResponses.has(body.id as string | number)) {
          this.pendingResponses.delete(body.id as string | number);
          resolve({
            jsonrpc: "2.0",
            id: body.id,
            error: { code: -32000, message: "Request timed out" },
          } as unknown as JSONRPCMessage);
        }
      }, 60_000);
    });
  }
}
