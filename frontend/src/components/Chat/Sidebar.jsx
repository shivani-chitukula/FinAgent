
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupAction,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuAction,
  SidebarFooter,
  SidebarTrigger
} from "@/components/ui/sidebar";
import { PlusCircle, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useState, useEffect } from "react";
import { fetchSessions, createSession, deleteSession } from "../../utils";
import { Button } from "../ui/button";

export function AppSidebar({ activeSessionId, onSessionSelect }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();


  const load = async () => {
    setLoading(true);
    const token = localStorage.getItem("token");
    const data = await fetchSessions(token);
    setSessions(data);
    setLoading(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('session_id');
    navigate('/');
  };

  useEffect(() => { load(); }, []);

  return (
    <Sidebar side="left" variant="sidebar" collapsible="offcanvas">
      <SidebarHeader>Chats</SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Sessions</SidebarGroupLabel>
          <SidebarGroupAction onClick={async () => {
            onSessionSelect(null, true);
            load();
          }}>
            <PlusCircle className="cursor-pointer  text-black" />
          </SidebarGroupAction>

          <SidebarGroupContent>
            <SidebarMenu>
              {loading ? (
                <SidebarMenuItem><SidebarMenuAction /></SidebarMenuItem>
              ) : (
                sessions.map((s) => (
                  <SidebarMenuItem key={s.session_id}>
                    <SidebarMenuButton
                      asChild
                      isActive={s.session_id === activeSessionId}
                      onClick={() => onSessionSelect(s.session_id)}
                      className="cursor-pointer bg-blue-500 text-white px-4 py-2 rounded"
                    >
                      <a>
                        {new Date(s.started_at).toLocaleTimeString()}
                      </a>
                    </SidebarMenuButton>
                    <SidebarMenuAction
                      className="cursor-pointer bg-blue text-white hover:bg-blue hover:text-black transition-colors"
                      onClick={() => {
                        deleteSession(s.session_id, localStorage.getItem("token"))
                          .then(load)
                          .then(() => {
                            if (s.session_id === activeSessionId)
                              onSessionSelect(null, true);
                          });
                      }}
                    >
                      <Trash2 />
                    </SidebarMenuAction>
                  </SidebarMenuItem>
                ))
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <Button className="cursor-pointer bg-blue-500 text-white px-4 py-2 rounded" onClick={handleLogout}>Logout</Button>
      </SidebarFooter>
    </Sidebar>
  );
}
