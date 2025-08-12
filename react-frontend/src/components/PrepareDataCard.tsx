import { useState } from "react";
import api from "../api";

export default function PrepareDataCard() {
    const [file, setFile] = useState<File | null>(null);
    const [prepareResult, setPrepareResult] = useState<any>(null);
    const [isLoading, setIsLoading] = useState<boolean>(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) {
            setPrepareResult({ error: "Please upload a CSV file first." });
            return;
        }

        setIsLoading(true);
        setPrepareResult(null); // Clear previous results

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
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="bg-white shadow-xl rounded-xl p-6 max-w-lg mx-auto mt-10 relative">
            {/* Loading Overlay */}
            {isLoading && (
                <div className="absolute inset-0 bg-white bg-opacity-90 flex items-center justify-center rounded-xl z-10">
                    <div className="text-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600 mx-auto mb-4"></div>
                        <p className="text-lg font-medium text-gray-700">Processing CSV Data...</p>
                        <p className="text-sm text-gray-500">Adding total_abundance column</p>
                    </div>
                </div>
            )}

            <h2 className="text-lg font-semibold mb-4 text-gray-800">🧮 Modify Vectorsurv Data</h2>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="block font-medium mb-1">Upload CSV:</label>
                    <input
                        type="file"
                        accept=".csv"
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                        className="w-full border px-3 py-2 rounded"
                        disabled={isLoading}
                    />
                </div>

                <button
                    type="submit"
                    disabled={isLoading}
                    className="bg-teal-600 text-white px-4 py-2 rounded hover:bg-teal-700 disabled:bg-teal-400 disabled:cursor-not-allowed w-full transition-colors"
                >
                    {isLoading ? "Processing..." : "Add total_abundance column"}
                </button>
            </form>

            {prepareResult && (
                <div className="mt-4">
                    <h3 className="font-medium mb-2">Processing Result:</h3>
                    <pre className="bg-gray-100 p-4 rounded text-sm overflow-x-auto">
                        {JSON.stringify(prepareResult, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    );
}
