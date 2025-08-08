import { useState } from "react";
import api from "../api";

interface Props {
    layerType: "surveillance" | "disease";
}

export default function UpdateLayerCard({ layerType }: Props) {
    const [file, setFile] = useState<File | null>(null);
    const [updateResult, setUpdateResult] = useState<any>(null);
    const [isLoading, setIsLoading] = useState<boolean>(false);

    const layerConfig = {
        surveillance: {
            title: "🦟 Update Surveillance Dashboard",
            description: "Upload prepared CSV with total_abundance column to update surveillance dashboard",
            color: "orange"
        },
        disease: {
            title: "🧬 Update Disease Monitoring Dashboard", 
            description: "Upload latest Pools CSV from Vectorsurv directly to update disease monitoring dashboard",
            color: "red"
        }
    };

    const config = layerConfig[layerType];

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) {
            setUpdateResult({ error: "Please upload a CSV file first." });
            return;
        }

        setIsLoading(true);
        setUpdateResult(null); // Clear previous results

        const formData = new FormData();
        formData.append("csv_update", file);
        formData.append("layer_type", layerType);

        try {
            const response = await api.post("/update-layer", formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });

            setUpdateResult({ status: "success", ...response.data });
        } catch (err: any) {
            const msg = err.response?.data || { status: "failure", message: err.message };
            setUpdateResult(msg);
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
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                        <p className="text-lg font-medium text-gray-700">Updating AGOL Layer...</p>
                        <p className="text-sm text-gray-500">Please wait, this may take a few moments</p>
                    </div>
                </div>
            )}

            <h2 className="text-lg font-semibold mb-2 text-gray-800">{config.title}</h2>
            <p className="text-sm text-gray-600 mb-4">{config.description}</p>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="block font-medium mb-1">Upload Final CSV:</label>
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
                    className={`w-full px-4 py-2 rounded transition-colors ${
                        layerType === "surveillance" 
                            ? "bg-orange-600 hover:bg-orange-700 disabled:bg-orange-400" 
                            : "bg-red-600 hover:bg-red-700 disabled:bg-red-400"
                    } text-white disabled:cursor-not-allowed`}
                >
                    {isLoading ? "Updating..." : "Push to Dashboard Backend"}
                </button>
            </form>

            {updateResult && (
                <div className="mt-4">
                    <h3 className="font-medium mb-2">Update Result:</h3>
                    <pre className="bg-gray-100 p-4 rounded text-sm overflow-x-auto">
                        {JSON.stringify(updateResult, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    );
}
