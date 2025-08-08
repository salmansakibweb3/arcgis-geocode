import { useState } from "react";
import api from "../api";

interface Props {
    layerType: "surveillance" | "disease";
}

export default function UpdateLayerCard({ layerType }: Props) {
    const [file, setFile] = useState<File | null>(null);
    const [updateResult, setUpdateResult] = useState<any>(null);

    const layerConfig = {
        surveillance: {
            title: "🦟 Update Surveillance Dashboard",
            description: "Upload CSV to update the surveillance monitoring layer",
            color: "orange"
        },
        disease: {
            title: "🧬 Update Disease Monitoring Dashboard", 
            description: "Upload CSV to update the disease monitoring layer",
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
        }
    };

    return (
        <div className="bg-white shadow-xl rounded-xl p-6 max-w-lg mx-auto mt-10">
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
                    />
                </div>

                <button
                    type="submit"
                    className={layerType === "surveillance" 
                        ? "bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded w-full"
                        : "bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded w-full"
                    }
                >
                    Push to Dashboard Backend
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
