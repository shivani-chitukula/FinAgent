import { Routes, Route } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Chat from "./pages/Chat";
import { SidebarProvider } from "@/components/ui/sidebar";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/chat"
        element={
          <SidebarProvider>
            <Chat />
          </SidebarProvider>
        }
      />
    </Routes>
  );
}

export default App;