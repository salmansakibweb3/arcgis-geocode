import { useState, useEffect } from "react";
import api from "../api";

export default function SprayNotificationsCard() {
    const [selectedSubgrids, setSelectedSubgrids] = useState<string>("");
    const [bufferDistance, setBufferDistance] = useState<number>(300);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [isTesting, setIsTesting] = useState<boolean>(false);
    const [isGettingLayerInfo, setIsGettingLayerInfo] = useState<boolean>(false);
    const [result, setResult] = useState<any>(null);
    const [testResult, setTestResult] = useState<any>(null);
    const [layerInfo, setLayerInfo] = useState<any>(null);

    // Check for URL parameters and localStorage data on component mount
    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const autoFill = urlParams.get('auto_fill');
        
        if (autoFill === 'true') {
            // Try to get data from localStorage
            const sprayDataJson = localStorage.getItem('spray_notifications_prefill');
            if (sprayDataJson) {
                try {
                    const sprayData = JSON.parse(sprayDataJson);
                    
                    // Check if data is not too old (within 10 minutes)
                    const dataAge = Date.now() - sprayData.timestamp;
                    if (dataAge < 10 * 60 * 1000) { // 10 minutes
                        // Auto-fill the subgrids field
                        setSelectedSubgrids(sprayData.subgrids);
                        
                        // Show notification that subgrids were auto-filled
                        setTimeout(() => {
                            alert(`Subgrids auto-filled from disease positive analysis:\n${sprayData.subgrids}`);
                        }, 500);
                        
                        // Clear the localStorage data after use
                        localStorage.removeItem('spray_notifications_prefill');
                    } else {
                        // Data is too old, clear it
                        localStorage.removeItem('spray_notifications_prefill');
                    }
                } catch (error) {
                    console.error('Error parsing spray notifications data:', error);
                    localStorage.removeItem('spray_notifications_prefill');
                }
            } else {
                // Fallback to URL parameters (for backwards compatibility)
                const subgridsParam = urlParams.get('subgrids');
                if (subgridsParam) {
                    setSelectedSubgrids(decodeURIComponent(subgridsParam));
                    setTimeout(() => {
                        alert(`Subgrids auto-filled from disease positive analysis:\n${decodeURIComponent(subgridsParam)}`);
                    }, 500);
                }
            }
            
            // Clear the URL parameters to clean up the URL
            const newUrl = window.location.pathname + window.location.hash;
            window.history.replaceState({}, document.title, newUrl);
        }
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!selectedSubgrids.trim()) {
            setResult({ error: "Please enter subgrid numbers." });
            return;
        }

        setIsLoading(true);
        setResult(null);

        try {
            // Parse subgrid numbers from comma-separated string
            const subgridArray = selectedSubgrids
                .split(',')
                .map(s => s.trim())
                .filter(s => s.length > 0);

            // Validate GridLabel format (TRS-Quadrant, e.g., "172024-1")
            const gridLabelPattern = /^\d+-\d+$/;
            const invalidLabels = subgridArray.filter(sg => !gridLabelPattern.test(sg));
            
            if (invalidLabels.length > 0) {
                throw new Error(`Invalid GridLabel format: ${invalidLabels.join(', ')}. Expected format: 'TRS-Quadrant' (e.g., '172024-1')`);
            }

            const requestData = {
                selected_subgrids: subgridArray,
                buffer_distance: bufferDistance
            };

            const response = await api.post("/generate-spray-notifications", requestData, {
                responseType: "blob", // Important for file download
            });

            // Create download link
            const blob = new Blob([response.data], { type: "text/csv" });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            
            // Generate filename with today's date
            const today = new Date().toLocaleDateString('en-US', {
                month: '2-digit',
                day: '2-digit',
                year: 'numeric'
            }).replace(/\//g, '');
            link.download = `Spray_Notifications_${today}.csv`;
            
            link.click();
            window.URL.revokeObjectURL(url);

            setResult({ 
                status: "success", 
                message: "Spray notifications CSV generated and downloaded successfully!",
                subgrids_processed: subgridArray.length,
                buffer_distance: bufferDistance
            });

        } catch (err: any) {
            const msg = err.response?.data ? 
                (err.response.data.message || "Unknown error occurred") : 
                err.message;
            setResult({ status: "failure", message: msg });
        } finally {
            setIsLoading(false);
        }
    };

    const testLayers = async () => {
        setIsTesting(true);
        setTestResult(null);

        try {
            const response = await api.post("/test-spray-layers", {});
            setTestResult(response.data);
        } catch (err: any) {
            const msg = err.response?.data ? 
                (err.response.data.message || "Test failed") : 
                err.message;
            setTestResult({ status: "failure", message: msg });
        } finally {
            setIsTesting(false);
        }
    };

    const getLayerInfo = async (layerId: string) => {
        setIsGettingLayerInfo(true);
        
        try {
            const response = await api.post("/get-layer-info", { layer_id: layerId });
            return response.data.layer_info;
        } catch (err: any) {
            console.error("Error getting layer info:", err);
            return null;
        } finally {
            setIsGettingLayerInfo(false);
        }
    };

    const showLayerInfo = async () => {
        const subgridInfo = await getLayerInfo("e8656893998e497fa8161f87d053a725");
        const residentInfo = await getLayerInfo("cd84fc9ddca2406f85c185a5841be65b"); // New hosted feature layer
        
        setLayerInfo({
            subgrid: subgridInfo,
            resident: residentInfo
        });
    };

    const handleSubgridChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        // Allow TRS-Quadrant format: numbers, hyphens, commas, and spaces
        const value = e.target.value.replace(/[^0-9,\s-]/g, '');
        setSelectedSubgrids(value);
    };

    // Parse subgrids for preview
    const subgridPreview = selectedSubgrids
        .split(',')
        .map(s => s.trim())
        .filter(s => s.length > 0);

    return (
        <div className="bg-white shadow-xl rounded-xl p-6 max-w-lg mx-auto mt-10 relative">
            {/* Loading Overlay */}
            {(isLoading || isTesting) && (
                <div className="absolute inset-0 bg-white bg-opacity-90 flex items-center justify-center rounded-xl z-10">
                    <div className="text-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
                        <p className="text-lg font-medium text-gray-700">
                            {isTesting ? "Testing Layer Access..." : "Generating Notifications List..."}
                        </p>
                        <p className="text-sm text-gray-500">
                            {isTesting ? "Verifying AGOL connectivity" : "Processing subgrids and resident data"}
                        </p>
                    </div>
                </div>
            )}

            <h2 className="text-lg font-semibold mb-2 text-gray-800">📧 Generate Spray Notifications</h2>
            <p className="text-sm text-gray-600 mb-4">
                Select subgrids by GridLabel (TRS-Quadrant format) and generate CSV list of residents to notify.
            </p>

            {/* Test Section */}
            <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <h3 className="font-semibold text-yellow-800 mb-2">🔧 Layer Connectivity Test</h3>
                <p className="text-sm text-yellow-700 mb-3">
                    Test AGOL layer access before generating notifications
                </p>
                <div className="flex gap-2">
                    <button
                        onClick={testLayers}
                        disabled={isTesting || isGettingLayerInfo}
                        className="bg-yellow-600 hover:bg-yellow-700 disabled:bg-yellow-400 text-white px-4 py-2 rounded text-sm transition-colors disabled:cursor-not-allowed"
                    >
                        {isTesting ? "Testing..." : "Test Layer Access"}
                    </button>
                    <button
                        onClick={showLayerInfo}
                        disabled={isTesting || isGettingLayerInfo}
                        className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded text-sm transition-colors disabled:cursor-not-allowed"
                    >
                        {isGettingLayerInfo ? "Loading..." : "Get Layer Names"}
                    </button>
                </div>
            </div>

            {/* Layer Info Display */}
            {layerInfo && (
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h3 className="font-semibold text-blue-800 mb-3">📋 Layer Information</h3>
                    
                    {layerInfo.subgrid && (
                        <div className="mb-3">
                            <h4 className="font-medium text-blue-700">🗺️ Subgrid Layer:</h4>
                            <p className="text-sm text-blue-600">
                                <strong>{layerInfo.subgrid.title}</strong> ({layerInfo.subgrid.type})
                                <br />
                                <span className="text-xs text-gray-500">
                                    Owner: {layerInfo.subgrid.owner} | Modified: {layerInfo.subgrid.modified}
                                </span>
                            </p>
                        </div>
                    )}
                    
                    {layerInfo.resident && (
                        <div>
                            <h4 className="font-medium text-blue-700">🏠 Resident Notices Layer:</h4>
                            <p className="text-sm text-blue-600">
                                <strong>{layerInfo.resident.title}</strong> ({layerInfo.resident.type})
                                <br />
                                <span className="text-xs text-gray-500">
                                    Owner: {layerInfo.resident.owner} | Modified: {layerInfo.resident.modified}
                                </span>
                            </p>
                        </div>
                    )}
                </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="block font-medium mb-1">
                        Subgrid GridLabels:
                        <span className="text-red-500">*</span>
                    </label>
                    <input
                        type="text"
                        value={selectedSubgrids}
                        onChange={handleSubgridChange}
                        placeholder="e.g. 172024-1, 122136-1, 132201-2"
                        className="w-full border px-3 py-2 rounded focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                        disabled={isLoading}
                        required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                        Enter GridLabel values (TRS-Quadrant format) separated by commas
                    </p>
                    
                    {/* Preview selected subgrids */}
                    {subgridPreview.length > 0 && (
                        <div className="mt-2 p-2 bg-gray-50 rounded text-sm">
                            <strong>Selected:</strong> {subgridPreview.join(", ")} 
                            <span className="text-gray-500 ml-1">
                                ({subgridPreview.length} subgrid{subgridPreview.length !== 1 ? 's' : ''})
                            </span>
                        </div>
                    )}
                </div>

                <div>
                    <label className="block font-medium mb-1">
                        Buffer Distance (feet):
                    </label>
                    <input
                        type="number"
                        value={bufferDistance}
                        onChange={(e) => setBufferDistance(Number(e.target.value))}
                        min="1"
                        max="5000"
                        step="1"
                        className="w-full border px-3 py-2 rounded focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                        disabled={isLoading}
                        required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                        Distance around treatment area to notify residents (default: 300 ft)
                    </p>
                </div>

                <button
                    type="submit"
                    disabled={isLoading || !selectedSubgrids.trim()}
                    className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white px-4 py-2 rounded transition-colors disabled:cursor-not-allowed"
                >
                    {isLoading ? "Generating..." : "Generate Notifications List"}
                </button>
            </form>

            {result && (
                <div className="mt-4">
                    <h3 className="font-medium mb-2">Result:</h3>
                    <div className={`p-4 rounded text-sm ${
                        result.status === "success" 
                            ? "bg-green-50 border border-green-200" 
                            : "bg-red-50 border border-red-200"
                    }`}>
                        {result.status === "success" ? (
                            <div className="text-green-700">
                                <p className="font-medium">✅ {result.message}</p>
                                {result.subgrids_processed && (
                                    <p className="mt-1">
                                        Processed {result.subgrids_processed} subgrid{result.subgrids_processed !== 1 ? 's' : ''} 
                                        with {result.buffer_distance}ft buffer
                                    </p>
                                )}
                            </div>
                        ) : (
                            <div className="text-red-700">
                                <p className="font-medium">❌ Error</p>
                                <p className="mt-1">{result.message}</p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Test Results */}
            {testResult && (
                <div className="mt-4">
                    <h3 className="font-medium mb-2">Test Results:</h3>
                    <div className={`p-4 rounded text-sm max-h-96 overflow-y-auto ${
                        testResult.status === "success" 
                            ? "bg-blue-50 border border-blue-200" 
                            : "bg-red-50 border border-red-200"
                    }`}>
                        {testResult.status === "success" ? (
                            <div className="text-blue-700">
                                <div className="space-y-3">
                                    {/* Subgrid Layer Test */}
                                    {testResult.tests?.subgrid_layer && (
                                        <div>
                                            <h4 className="font-medium">📍 Subgrid Layer:</h4>
                                            {testResult.tests.subgrid_layer.accessible ? (
                                                <div className="ml-4 text-sm">
                                                    <p>✅ <strong>Accessible</strong> - {testResult.tests.subgrid_layer.title}</p>
                                                    <p>📊 Features: {testResult.tests.subgrid_layer.feature_count}</p>
                                                    <p>🏷️ GridLabel field: {testResult.tests.subgrid_layer.has_gridlabel ? '✅ Found' : '❌ Missing'}</p>
                                                    {testResult.tests.subgrid_layer.sample_gridlabels?.length > 0 && (
                                                        <p>🔍 Sample GridLabels: {testResult.tests.subgrid_layer.sample_gridlabels.join(', ')}</p>
                                                    )}
                                                </div>
                                            ) : (
                                                <p className="ml-4 text-red-600">❌ Error: {testResult.tests.subgrid_layer.error}</p>
                                            )}
                                        </div>
                                    )}

                                    {/* Resident Notices Test */}
                                    {testResult.tests?.resident_notices_layer && (
                                        <div>
                                            <h4 className="font-medium">🏠 Resident Notices Layer:</h4>
                                            {testResult.tests.resident_notices_layer.accessible ? (
                                                <div className="ml-4 text-sm">
                                                    <p>✅ <strong>Accessible</strong> - {testResult.tests.resident_notices_layer.title}</p>
                                                    <p>📊 Features: {testResult.tests.resident_notices_layer.feature_count}</p>
                                                    <p>🔢 Sublayer: {testResult.tests.resident_notices_layer.sublayer_index}</p>
                                                </div>
                                            ) : (
                                                <p className="ml-4 text-red-600">❌ Error: {testResult.tests.resident_notices_layer.error}</p>
                                            )}
                                        </div>
                                    )}

                                    {/* GridLabel Query Test */}
                                    {testResult.tests?.gridlabel_query && (
                                        <div>
                                            <h4 className="font-medium">🔍 GridLabel Query Test:</h4>
                                            {testResult.tests.gridlabel_query.success ? (
                                                <div className="ml-4 text-sm">
                                                    <p>✅ Query successful for: {testResult.tests.gridlabel_query.test_gridlabel}</p>
                                                    <p>🎯 Features found: {testResult.tests.gridlabel_query.features_found}</p>
                                                    <p>🗺️ Has geometry: {testResult.tests.gridlabel_query.has_geometry ? '✅' : '❌'}</p>
                                                </div>
                                            ) : (
                                                <p className="ml-4 text-red-600">❌ Error: {testResult.tests.gridlabel_query.error}</p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ) : (
                            <div className="text-red-700">
                                <p className="font-medium">❌ Test Failed</p>
                                <p className="mt-1">{testResult.message}</p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Information Panel */}
            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h3 className="font-semibold text-blue-800 mb-2">ℹ️ Information</h3>
                <div className="text-sm text-blue-700 space-y-1">
                    <div>• <strong>Data Source:</strong> Live AGOL hosted layers</div>
                    <div>• <strong>Processing:</strong> Subgrids → Buffer → Intersect → Deduplicate</div>
                    <div>• <strong>Output:</strong> CSV file with resident notification details</div>
                    <div>• <strong>Next Step:</strong> Send generated CSV to Kathy for notifications</div>
                </div>
            </div>
        </div>
    );
}
