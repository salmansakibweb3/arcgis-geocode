import { useState } from "react";
import LoginCard from "./components/LoginCard";
import GeocodeCard from "./components/GeocodeCard";
import CoordsCard from "./components/CoordsCard";
import PrepareDataCard from "./components/PrepareDataCard";
import UpdateLayerCard from "./components/UpdateLayerCard";
import WorkflowOptionsCard from "./components/WorkflowOptionsCard";
import AdultControlCard from "./components/AdultControlCard";

type Workflow = "home" | "geocode" | "update-surveillance" | "update-disease" | "adult-control";

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [workflow, setWorkflow] = useState<Workflow>("home");
  const [username, setUsername] = useState<string | null>(null);

  const handleLoginSuccess = (user: string) => {
    setIsLoggedIn(true);
    setUsername(user);
    setWorkflow("home");
  };


  const handleHomeClick = () => {
    setWorkflow("home");
  };

  return (
    <main className="bg-gray-100 min-h-screen p-6">
      <header className="flex justify-between items-center mb-6 max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-blue-800">
          🛰️ CMAD Pioneer (v.0.0.1)
            <h2 className="text-sm font-normal text-gray-500 mt-1">Developed by Salman Sakib</h2>
        </h1>
        {isLoggedIn && (
          <button
            onClick={handleHomeClick}
            className="bg-green-400 hover:bg-green-600 text-gray-800 px-4 py-2 rounded-md shadow-sm transition"
          >
            🏠 Home
          </button>
        )}
      </header>

      {!isLoggedIn && <LoginCard onLoginSuccess={handleLoginSuccess} />}

      {isLoggedIn && workflow === "home" && (
        <WorkflowOptionsCard
          username={username || "User"}
          onSelectWorkflow={setWorkflow}
        />
      )}

      {workflow === "geocode" && (
        <>
          <GeocodeCard />
          <CoordsCard />
        </>
      )}

      {workflow === "update-surveillance" && (
        <>
          <PrepareDataCard />
          <UpdateLayerCard layerType="surveillance" />
        </>
      )}

      {workflow === "update-disease" && (
        <>
          <UpdateLayerCard layerType="disease" />
        </>
      )}

      {workflow === "adult-control" && (
        <>
          <AdultControlCard />
        </>
      )}
    </main>
  );
}

export default App;
