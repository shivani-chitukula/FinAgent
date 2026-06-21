import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import MessageList from '../components/Chat/MessageList';
import MessageInput from '../components/Chat/MessageInput';
import { getResponse, createSession, sessionHistory } from '../utils';
import { AppSidebar } from "../components/Chat/Sidebar";
import { SidebarTrigger } from "@/components/ui/sidebar";


function Chat() {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState(localStorage.getItem('session_id') || null);
  const [messages, setMessages] = useState([
    { role: 'bot', text: 'Hello! How can I help you today?' }
  ]);
  const [input, setInput] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/');
    }
  }, [navigate]);


  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const token = localStorage.getItem('token');
    let currentSessionId = sessionId;

    if (!currentSessionId) {
      try {
        const newSession = await createSession(token);
        currentSessionId = newSession.session_id;
        setSessionId(currentSessionId);
        localStorage.setItem('session_id', currentSessionId);
      } catch (err) {
        console.error('Failed to create session:', err);
        setMessages(prev => [...prev, { role: 'bot', text: 'Could not create session. Please try again later.' }]);
        return;
      }
    }

    const userMessage = { role: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');

    try {
      const botReply = await getResponse({ query: input }, token);
      const botMessage = { role: 'bot', text: botReply };
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'bot', text: `Error: ${error.message}` }]);
    }

    
  };


  const handleSessionSelect = async (id, skipHistory = false) => {
    setSessionId(id);
    localStorage.setItem('session_id', id);

    if (skipHistory) {
      setMessages([{ role: 'bot', text: 'New session started. Ask me something!' }]);
      return;
    }

    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      const history = await sessionHistory(id, token);

      setMessages(
        history.length > 0
        ? history
        : [{ role: 'bot', text: 'This session has no messages yet.' }]
      );

      setSessionId(id);
      localStorage.setItem('session_id', id);
    } catch (err) {
      console.error('Failed to fetch session messages:', err);
      setMessages([{ role: 'bot', text: 'Error loading session history.' }]);
    }
      };

  return (
  <div className="flex h-screen w-screen overflow-hidden">
    <AppSidebar activeSessionId={sessionId} onSessionSelect={handleSessionSelect} />

    <div className="flex flex-1 justify-center items-center p-4 bg-gray-100">
    <div className="flex flex-col w-full max-w-3xl h-full bg-white rounded-2xl shadow-md overflow-hidden">
      <header className="flex justify-between items-center p-4 border-b">
        <SidebarTrigger />
        <h2 className="text-xl font-semibold">Chat</h2>
      </header>

      <div className="flex flex-col flex-1 overflow-auto">
        <MessageList messages={messages} className="flex-1 overflow-auto px-4 py-2" />
        <MessageInput input={input} setInput={setInput} onSend={handleSend} />
      </div>
    </div>
  </div>
  </div>
);
}

export default Chat;
