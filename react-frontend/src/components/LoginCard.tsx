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
    const [isStartingLogin, setIsStartingLogin] = useState(false);
    const [isCompletingLogin, setIsCompletingLogin] = useState(false);

    const startLogin = async () => {
        setIsStartingLogin(true);
        try {
            const res = await api.post("/start-login", { client_id: CLIENT_ID });
            const url = res.data.oauth_url;
            window.open(url, "_blank");
            setAwaitingCode(true);
        } catch (err: any) {
            setLoginResult({ status: "failure", message: err.message });
        } finally {
            setIsStartingLogin(false);
        }
    };

    const completeLogin = async () => {
        setIsCompletingLogin(true);
        try {
            const res = await api.post("/complete-login", {
                client_id: CLIENT_ID,
                code: approvalCode,
            });
            setLoginResult(res.data);
            if (res.data.status === "success") {
                const fullName = res.data.full_name || "User";
                onLoginSuccess(fullName);
            }
        } catch (err: any) {
            setLoginResult({ status: "failure", message: err.message });
        } finally {
            setIsCompletingLogin(false);
        }
    };

    return (
        <div className="bg-white shadow-xl rounded-xl p-6 max-w-lg mx-auto mt-8 relative">
            {/* Loading Overlay */}
            {(isStartingLogin || isCompletingLogin) && (
                <div className="absolute inset-0 bg-white bg-opacity-90 flex items-center justify-center rounded-xl z-10">
                    <div className="text-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                        <p className="text-lg font-medium text-gray-700">
                            {isStartingLogin ? "Initializing Login..." : "Completing Login..."}
                        </p>
                        <p className="text-sm text-gray-500">Please wait</p>
                    </div>
                </div>
            )}

            <h2 className="text-lg font-semibold mb-4 text-gray-800">🔐 ArcGIS Login</h2>

            {!awaitingCode ? (
                <button
                    onClick={startLogin}
                    disabled={isStartingLogin}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors"
                >
                    {isStartingLogin ? "Starting..." : "Start Login"}
                </button>
            ) : (
                <>
                    <label className="block font-medium mt-4 mb-1">Approval Code:</label>
                    <input
                        type="text"
                        className="w-full px-3 py-2 border rounded mb-4"
                        value={approvalCode}
                        onChange={(e) => setApprovalCode(e.target.value)}
                        disabled={isCompletingLogin}
                    />
                    <button
                        onClick={completeLogin}
                        disabled={isCompletingLogin}
                        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:bg-green-400 disabled:cursor-not-allowed transition-colors"
                    >
                        {isCompletingLogin ? "Submitting..." : "Submit Code"}
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
