import { Send, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useState } from "react";

function MessageInput({ input, setInput, onSend }) {
  const [isSending, setIsSending] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isSending) return;
    setIsSending(true);
    try {
      await onSend(e);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      handleSend(e);
    }
  };

  return (
    <form
      onSubmit={handleSend}
      className="flex items-end gap-2 w-full p-2 border-t"
    >
      <Textarea
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type your message..."
        className="flex-1 resize-none min-h-[40px] max-h-[160px] overflow-auto"
        disabled={isSending}
      />
      <Button
        type="submit"
        size="icon"
        className="cursor-pointer bg-blue-500 text-white px-4 py-2 rounded shrink-0"
        disabled={isSending}
      >
        {isSending ? (
          <LoaderCircle className="w-4 h-4 animate-spin" />
        ) : (
          <Send className="w-4 h-4" />
        )}
      </Button>
    </form>
  );
}


export default MessageInput;
