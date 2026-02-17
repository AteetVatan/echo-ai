import type { Metadata } from "next";
import { ChatContainer } from "@/components/chat/ChatContainer";

export const metadata: Metadata = {
    title: "Chat — EchoAI",
    description: "Chat with Ateet's AI clone, powered by RAG and real career data.",
};

export default function ChatPage() {
    return <ChatContainer />;
}
