import { useState } from "react";
import api from "../api";

const CLIENT_ID = "htgaziNM2Tfszvnx"; // 🔐 Hardcoded client ID

export default function LoginCard({
    onLoginSuccess
}: {
    onLoginSuccess: (username: string) => void;
}) {
    const [approvalCode, setApprovalCode] = useState("");
    const [awaitingCode, setAwaitingCode] = useState(false);
    const [loginResult, setLoginResult] = useState<any>(null);

    const startLogin = async () => {
        try {
            const res = await api.post("/start-login", { client_id: CLIENT_ID });
            const url = res.data.oauth_url;
            window.open(url, "_blank");
            setAwaitingCode(true);
        } catch (err: any) {
            setLoginResult({ status: "failure", message: err.message });
        }
    };

    const completeLogin = async () => {
        try {
            const res = await api.post("/complete-login", {
                client_id: CLIENT_ID,
                code: approvalCode,
            });
            setLoginResult(res.data);
            if (res.data.status === "success") {
                const message = res.data.message || "";
                const match = message.match(/Logged in as (\w+)/i);
                const fullName = res.data.full_name || "User";
                onLoginSuccess(fullName);
            }
        } catch (err: any) {
            setLoginResult({ status: "failure", message: err.message });
        }
    };

    return (
        <div className="bg-white shadow-xl rounded-xl p-6 max-w-lg mx-auto mt-8">
            <h2 className="text-lg font-semibold mb-4 text-gray-800">🔐 ArcGIS Login</h2>

            {!awaitingCode ? (
                <button
                    onClick={startLogin}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                >
                    Start Login
                </button>
            ) : (
                <>
                    <label className="block font-medium mt-4 mb-1">Approval Code:</label>
                    <input
                        type="text"
                        className="w-full px-3 py-2 border rounded mb-4"
                        value={approvalCode}
                        onChange={(e) => setApprovalCode(e.target.value)}
                    />
                    <button
                        onClick={completeLogin}
                        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                    >
                        Submit Code
                    </button>
                </>
            )}

            {loginResult && (
                <pre className="mt-4 bg-gray-100 text-sm p-4 rounded overflow-x-auto">
                    {JSON.stringify(loginResult, null, 2)}
                </pre>
            )}
        </div>
    );
}
