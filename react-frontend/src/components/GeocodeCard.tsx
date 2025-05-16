import { useState } from "react";
import api from "../api";

export default function GeocodeCard() {
  const [file, setFile] = useState<File | null>(null);
  const [addressCol, setAddressCol] = useState("");
  const [cityCol, setCityCol] = useState("");
  const [geocodeResult, setGeocodeResult] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !addressCol || !cityCol) {
      setGeocodeResult({ error: "Please fill in all fields." });
      return;
    }

    const formData = new FormData();
    formData.append("csv", file);
    formData.append("address_col", addressCol);
    formData.append("city_col", cityCol);

    try {
      const response = await api.post("/geocode", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        responseType: "blob",
      });

      const blob = new Blob([response.data], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "geocoded.csv";
      link.click();

      setGeocodeResult({ status: "success", message: "CSV downloaded." });
    } catch (err: any) {
      setGeocodeResult({ status: "failure", message: err.message });
    }
  };

  return (
    <div className="bg-white shadow-xl rounded-xl p-6 max-w-lg mx-auto mt-10">
      <h2 className="text-lg font-semibold mb-4 text-gray-800">📍 Geocode CSV</h2>

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

        <div>
          <label className="block font-medium mb-1">Address Column:</label>
          <input
            type="text"
            value={addressCol}
            onChange={(e) => setAddressCol(e.target.value)}
            className="w-full border px-3 py-2 rounded"
            placeholder="e.g. Address"
          />
        </div>

        <div>
          <label className="block font-medium mb-1">City Column:</label>
          <input
            type="text"
            value={cityCol}
            onChange={(e) => setCityCol(e.target.value)}
            className="w-full border px-3 py-2 rounded"
            placeholder="e.g. City"
          />
        </div>

        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Submit for Geocoding
        </button>
      </form>

      {geocodeResult && (
        <pre className="mt-4 bg-gray-100 p-4 rounded text-sm overflow-x-auto">
          {JSON.stringify(geocodeResult, null, 2)}
        </pre>
      )}
    </div>
  );
}
