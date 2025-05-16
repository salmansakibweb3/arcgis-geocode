import { useState } from "react";
import api from "../api";

export default function UpdateLayerCard() {
    const [file, setFile] = useState<File | null>(null);
    const [updateResult, setUpdateResult] = useState<any>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) {
            setUpdateResult({ error: "Please upload a CSV file first." });
            return;
        }

        const formData = new FormData();
        formData.append("csv_update", file);

        try {
            const response = await api.post("/update-layer", formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });

            setUpdateResult({ status: "success", ...response.data });
        } catch (err: any) {
            const msg = err.response?.data || { status: "failure", message: err.message };
            setUpdateResult(msg);
        }
    };

    return (
        <div className="bg-white shadow-xl rounded-xl p-6 max-w-lg mx-auto mt-10">
            <h2 className="text-lg font-semibold mb-4 text-gray-800">🗂️ Update CMAD Dashboard</h2>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="block font-medium mb-1">Upload Final CSV:</label>
                    <input
                        type="file"
                        accept=".csv"
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                        className="w-full border px-3 py-2 rounded"
                    />
                </div>

                <button
                    type="submit"
                    className="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700"
                >
                    Push to Dashboard Backend
                </button>
            </form>

            {updateResult && (
                <pre className="mt-4 bg-gray-100 p-4 rounded text-sm overflow-x-auto">
                    {JSON.stringify(updateResult, null, 2)}
                </pre>
            )}
        </div>
    );
}
