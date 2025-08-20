import { useState } from "react";
import api from "../api";

interface PositiveSample {
    objectId: number;
    agency_pool_num?: string;
    x: number;
    y: number;
    subgrid_label?: string;
    collection_date: string;
    add_date: string;
    wnv_positive: boolean;
    slev_positive: boolean;
    weev_positive: boolean;
    diseases: string[];
}

interface MapGenerationResult {
    status: "success" | "failure";
    message: string;
    total_samples?: number;
    positive_samples?: number;
    samples?: PositiveSample[];
    date_range?: {
        start_date: string;
        end_date: string;
    };
    layer_info?: {
        title: string;
        feature_count: number;
        fields: string[];
    };
}

export default function DiseaseMapGenerationCard() {
    const [startDate, setStartDate] = useState<string>("");
    const [endDate, setEndDate] = useState<string>("");
    const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
    const [result, setResult] = useState<MapGenerationResult | null>(null);

    // Set default date range to current week
    const getCurrentWeekRange = () => {
        const now = new Date();
        const startOfWeek = new Date(now);
        const dayOfWeek = now.getDay();
        const daysToSubtract = dayOfWeek === 0 ? 6 : dayOfWeek - 1; // Monday start
        
        startOfWeek.setDate(now.getDate() - daysToSubtract);
        startOfWeek.setHours(0, 0, 0, 0);
        
        const endOfWeek = new Date(startOfWeek);
        endOfWeek.setDate(startOfWeek.getDate() + 6);
        endOfWeek.setHours(23, 59, 59, 999);
        
        return {
            start: startOfWeek.toISOString().split('T')[0],
            end: endOfWeek.toISOString().split('T')[0]
        };
    };

    // Initialize with current week if dates are empty
    const initializeCurrentWeek = () => {
        const weekRange = getCurrentWeekRange();
        setStartDate(weekRange.start);
        setEndDate(weekRange.end);
    };

    const handleAnalyzePositives = async () => {
        if (!startDate || !endDate) {
            setResult({
                status: "failure",
                message: "Please select both start and end dates"
            });
            return;
        }

        setIsAnalyzing(true);
        setResult(null);

        try {
            const response = await api.post("/analyze-disease-positives", {
                start_date: startDate,
                end_date: endDate
            });

            setResult(response.data);
        } catch (err: any) {
            const msg = err.response?.data || { 
                status: "failure", 
                message: err.message || "Unknown error occurred" 
            };
            setResult(msg);
        } finally {
            setIsAnalyzing(false);
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString();
    };

    const getDiseaseIcon = (diseases: string[]) => {
        if (diseases.includes("WNV")) return "🦟";
        if (diseases.includes("SLEV")) return "🔴";
        if (diseases.includes("WEEV")) return "🟡";
        return "❓";
    };

    const hasPositiveSamples = result?.status === "success" && result?.positive_samples && result.positive_samples > 0;

    const handleDownloadShapefile = async (type: 'points' | 'polygons') => {
        if (!result?.samples || result.samples.length === 0) {
            alert('No positive samples available for export');
            return;
        }

        try {
            setIsAnalyzing(true); // Reuse the loading state
            
            const response = await api.post(`/export-${type}-shapefile`, {
                start_date: startDate,
                end_date: endDate,
                samples: result.samples
            }, {
                responseType: 'blob'
            });

            // Create download link
            const blob = new Blob([response.data], { type: 'application/zip' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            
            // Generate filename with date range
            const startFormatted = startDate.replace(/-/g, '');
            const endFormatted = endDate.replace(/-/g, '');
            const fileType = type === 'points' ? 'PositiveSamples' : 'AssociatedSubgrids';
            link.download = `${fileType}_${startFormatted}_${endFormatted}.zip`;
            
            link.click();
            window.URL.revokeObjectURL(url);
            
        } catch (error: any) {
            console.error(`Error downloading ${type} shapefile:`, error);
            alert(`Failed to download ${type} shapefile. Please try again.`);
        } finally {
            setIsAnalyzing(false);
        }
    };

    return (
        <div className="bg-white shadow-xl rounded-xl p-6 max-w-4xl mx-auto mt-10 relative">
            {/* Loading Overlay */}
            {isAnalyzing && (
                <div className="absolute inset-0 bg-white bg-opacity-90 flex items-center justify-center rounded-xl z-10">
                    <div className="text-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto mb-4"></div>
                        <p className="text-lg font-medium text-gray-700">Analyzing Disease Positives...</p>
                        <p className="text-sm text-gray-500">Reading pools layer and filtering by date range</p>
                    </div>
                </div>
            )}

            <div className="mb-6">
                <h2 className="text-2xl font-semibold mb-2 text-gray-800">
                    🗺️ Disease Map Generation
                </h2>
                <p className="text-sm text-gray-600 mb-4">
                    Step 1: Identify disease positive samples from pools layer within specified date range.
                    This will analyze WNV, SLEV, and WEEV positive results and extract their coordinates for automated map creation.
                </p>
            </div>

            {/* Input Section */}
            <div className="space-y-4 mb-6">
                {/* Date Range */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Start Date
                        </label>
                        <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                        />
                    </div>
                    
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            End Date
                        </label>
                        <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                        />
                    </div>

                    <div className="flex flex-col justify-end">
                        <button
                            onClick={initializeCurrentWeek}
                            className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-md transition-colors text-sm"
                        >
                            📅 This Week
                        </button>
                    </div>
                </div>
            </div>

            {/* Action Button */}
            <button
                onClick={handleAnalyzePositives}
                disabled={isAnalyzing}
                className="w-full bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white px-4 py-3 rounded-lg transition-colors disabled:cursor-not-allowed font-medium"
            >
                {isAnalyzing ? "Analyzing..." : "🔍 Analyze Disease Positives"}
            </button>

            {/* Results Section */}
            {result && (
                <div className="mt-6">
                    <h3 className="font-medium mb-3 text-lg">Analysis Results:</h3>
                    <div className={`p-4 rounded-lg text-sm border ${
                        result.status === "success" 
                            ? hasPositiveSamples 
                                ? "bg-red-50 border-red-200" 
                                : "bg-green-50 border-green-200"
                            : "bg-red-50 border-red-200"
                    }`}>
                        {result.status === "success" ? (
                            <div>
                                {/* Layer Info */}
                                {result.layer_info && (
                                    <div className="mb-4 p-3 bg-gray-50 border border-gray-200 rounded">
                                        <p className="font-medium text-gray-800">📊 Layer Information</p>
                                        <div className="mt-2 text-gray-700">
                                            <p><strong>Title:</strong> {result.layer_info.title}</p>
                                            <p><strong>Total Features:</strong> {result.layer_info.feature_count}</p>
                                            <p><strong>Fields:</strong> {result.layer_info.fields.join(", ")}</p>
                                        </div>
                                    </div>
                                )}

                                {/* Summary Stats */}
                                <div className="mb-4">
                                    <p className="font-medium text-gray-800">
                                        📈 Analysis Summary ({formatDate(result.date_range?.start_date || startDate)} - {formatDate(result.date_range?.end_date || endDate)})
                                    </p>
                                    <div className="mt-2 grid grid-cols-2 gap-4">
                                        <div className="bg-blue-50 p-3 rounded border border-blue-200">
                                            <p className="text-sm text-blue-600">Total Samples</p>
                                            <p className="text-2xl font-bold text-blue-800">{result.total_samples || 0}</p>
                                        </div>
                                        <div className={`p-3 rounded border ${
                                            hasPositiveSamples 
                                                ? "bg-red-100 border-red-300" 
                                                : "bg-green-100 border-green-300"
                                        }`}>
                                            <p className={`text-sm ${hasPositiveSamples ? "text-red-600" : "text-green-600"}`}>
                                                Disease Positives
                                            </p>
                                            <p className={`text-2xl font-bold ${hasPositiveSamples ? "text-red-800" : "text-green-800"}`}>
                                                {result.positive_samples || 0}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {/* Positive Samples Detail */}
                                {hasPositiveSamples && result.samples && (
                                    <div>
                                        <p className="font-medium text-red-700 mb-2">
                                            🚨 Positive Samples Found - Ready for Map Generation
                                        </p>
                                        <div className="max-h-64 overflow-y-auto">
                                            <table className="w-full text-xs">
                                                <thead className="bg-gray-100 sticky top-0">
                                                    <tr>
                                                        <th className="px-2 py-1 text-left">Pool ID</th>
                                                        <th className="px-2 py-1 text-left">Subgrid</th>
                                                        <th className="px-2 py-1 text-left">Coordinates</th>
                                                        <th className="px-2 py-1 text-left">Collection Date</th>
                                                        <th className="px-2 py-1 text-left">Diseases</th>
                                                        <th className="px-2 py-1 text-left">Action</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {result.samples.map((sample, index) => (
                                                        <tr key={index} className="border-t">
                                                            <td className="px-2 py-1">{sample.agency_pool_num || sample.objectId}</td>
                                                            <td className="px-2 py-1 font-semibold text-blue-700">
                                                                {sample.subgrid_label || 'Unknown'}
                                                            </td>
                                                            <td className="px-2 py-1 font-mono">
                                                                {sample.x?.toFixed(6)}, {sample.y?.toFixed(6)}
                                                            </td>
                                                            <td className="px-2 py-1">{formatDate(sample.collection_date)}</td>
                                                            <td className="px-2 py-1">
                                                                {getDiseaseIcon(sample.diseases)} {sample.diseases.join(", ")}
                                                            </td>
                                                            <td className="px-2 py-1">
                                                                <button 
                                                                    onClick={() => alert(`Generate map for Pool ${sample.agency_pool_num || sample.objectId}`)}
                                                                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition-colors"
                                                                >
                                                                    📍 Generate Map
                                                                </button>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                        
                                        {/* Next Steps */}
                                        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                                            <p className="font-medium text-yellow-800">🎯 Export Shapefiles for ArcGIS Pro</p>
                                            <p className="text-sm text-yellow-700 mt-1 mb-3">
                                                Download shapefiles to import directly into ArcGIS Pro for fast layout generation.
                                            </p>
                                            <div className="flex gap-3">
                                                <button 
                                                    onClick={() => handleDownloadShapefile('points')}
                                                    className="bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-2 rounded transition-colors flex items-center gap-2"
                                                >
                                                    📍 Positive Samples Shapefile
                                                </button>
                                                <button 
                                                    onClick={() => handleDownloadShapefile('polygons')}
                                                    className="bg-purple-600 hover:bg-purple-700 text-white text-sm px-4 py-2 rounded transition-colors flex items-center gap-2"
                                                >
                                                    🔲 Associated Subgrids Shapefile
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* No Positives Found */}
                                {!hasPositiveSamples && (
                                    <div className="text-green-700">
                                        <p className="font-medium">✅ No Disease Positives Found</p>
                                        <p className="mt-1">
                                            No WNV, SLEV, or WEEV positive samples were found in the selected date range.
                                            {result.total_samples && result.total_samples > 0 && (
                                                <span> All {result.total_samples} samples tested negative.</span>
                                            )}
                                        </p>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="text-red-700">
                                <p className="font-medium">❌ Analysis Failed</p>
                                <p className="mt-1">{result.message}</p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Instructions */}
            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h3 className="font-medium text-blue-800 mb-2">💡 Instructions</h3>
                <div className="text-sm text-blue-700 space-y-1">
                    <p>1. <strong>Enter Pools Layer ID:</strong> The ArcGIS Online layer containing your disease monitoring data</p>
                    <p>2. <strong>Select Date Range:</strong> Choose the period to analyze (use "This Week" for current week)</p>
                    <p>3. <strong>Analyze:</strong> The system will read the layer structure and identify positive samples</p>
                    <p>4. <strong>Next:</strong> Once positives are found, proceed to automated map generation</p>
                </div>
            </div>
        </div>
    );
}
