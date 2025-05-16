import { useState } from "react";
import api from "../api";

export default function PrepareDataCard() {
    const [file, setFile] = useState<File | null>(null);
    const [prepareResult, setPrepareResult] = useState<any>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) {
            setPrepareResult({ error: "Please upload a CSV file first." });
            return;
        }

        const formData = new FormData();
        formData.append("csv_prepare", file);

        try {
            const response = await api.post("/prepare-data", formData, {
                headers: { "Content-Type": "multipart/form-data" },
                responseType: "blob",
            });

            const blob = new Blob([response.data], { type: "text/csv" });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = "prepared.csv";
            link.click();

            setPrepareResult({ status: "success", message: "Prepared CSV downloaded." });
        } catch (err: any) {
            setPrepareResult({ status: "failure", message: err.message });
        }
    };

    return (
        <div className="bg-white shadow-xl rounded-xl p-6 max-w-lg mx-auto mt-10">
            <h2 className="text-lg font-semibold mb-4 text-gray-800">🧮 Modify Vectorsurv Data</h2>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="block font-medium mb-1">Upload CSV:</label>
                    <input
                        type="file"
                        accept=".csv"
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                        className="w-full border px-3 py-2 rounded"
                    />
                </div>

                <button
                    type="submit"
                    className="bg-teal-600 text-white px-4 py-2 rounded hover:bg-teal-700"
                >
                    Add total_abundance column
                </button>
            </form>

            {prepareResult && (
                <pre className="mt-4 bg-gray-100 p-4 rounded text-sm overflow-x-auto">
                    {JSON.stringify(prepareResult, null, 2)}
                </pre>
            )}
        </div>
    );
}
