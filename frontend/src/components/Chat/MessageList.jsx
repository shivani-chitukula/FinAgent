function MessageList({ messages }) {
  return (
    <div className="flex flex-col gap-2 p-4 overflow-y-auto flex-1">
      {messages.map((msg, index) => (
        <div
          key={index}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`px-4 py-2 max-w-[70%] rounded-2xl text-sm whitespace-pre-wrap break-words
              ${msg.role === 'user'
                ? 'bg-blue-600 text-white rounded-br-none'
                : 'bg-gray-200 text-black rounded-bl-none'
              }`}
          >
            {msg.text}
          </div>
        </div>
      ))}
    </div>
  );
}

export default MessageList;
