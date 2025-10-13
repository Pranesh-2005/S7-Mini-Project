"use client";

import { useEffect, useState } from "react";

import { useCopilotChat, useCopilotAction, CatchAllActionRenderProps } from "@copilotkit/react-core";
import { CopilotChat, CopilotKitCSSProperties, useCopilotChatSuggestions } from "@copilotkit/react-ui";
import { MCPEndpointConfig } from "@copilotkit/runtime";
import { DefaultToolRender } from "@/components/default-tool-render";

const themeColor = "#6366f1";

export default function Home() {
  return (
    <main style={{ "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties}>
      <YourMainContent />
      <CopilotChat
        // clickOutsideToClose={false}
        // defaultOpen={true}
        labels={{
          title: "MCP Client",
          initial: "👋 Hi! I'm a MCP client like Claude Desktop and Cursor, I can assist you by calling MCP tools available.\n\n**Available tools:**\n- 'List Databases'\n- 'List Tables'\n- 'Database Schema'\n- 'Table Schema'\n- 'Execute Query'\nWhat can I help you with?"
        }}
      />
    </main>
  );
}

function YourMainContent() {
  const { mcpServers, setMcpServers } = useCopilotChat();
  const [newMcpServer, setNewMcpServer] = useState("");

  useEffect(() => {
    setMcpServers([
      {
        endpoint: "https://miniprojectmcp.onrender.com/sse"  // Change this to your local MCP server
      }
    ]);
  }, []);

  const removeMcpServer = (url: string) => {
    setMcpServers(mcpServers.filter((server) => server.endpoint !== url));
  }

  const addMcpServer = (server: MCPEndpointConfig) => {
    setMcpServers([...mcpServers, server]);
  }

  useCopilotChatSuggestions({
    maxSuggestions: 3,
    instructions: "Give the user a short and concise suggestion based on the conversation and your available tools. Focus on PostgreSQL mine is connected to a PostgreSQL database. Suggest actions like 'List Databases', 'List Tables', 'Database Schema', 'Table Schema', 'Execute Query'.",
  })

  useCopilotAction({
    name: "*",
    render: ({ name, status, args, result }: CatchAllActionRenderProps<[]>) => (
      <DefaultToolRender status={status} name={name} args={args} result={result} />
    ),
  });
  return null;
}