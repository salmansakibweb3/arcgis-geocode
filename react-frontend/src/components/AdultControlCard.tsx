import { useState } from "react";

interface Step {
    id: number;
    title: string;
    description: string;
    completed: boolean;
    priority: "critical" | "important" | "normal";
}

export default function AdultControlCard() {
    const [steps, setSteps] = useState<Step[]>([
        {
            id: 1,
            title: "Map Positive Pools",
            description: "Verify data accuracy, check comments for discrepancies, export mosquito pool data from CalSurv/VectorSurv",
            completed: false,
            priority: "critical"
        },
        {
            id: 2,
            title: "Generate Preliminary Treatment Areas",
            description: "Create 0.25-mile polygon buffer around positive sites, submit draft maps to Chris for review",
            completed: false,
            priority: "critical"
        },
        {
            id: 3,
            title: "Finalize Treatment Areas",
            description: "Revise treatment polygons per feedback, add treatment date and approximate times",
            completed: false,
            priority: "critical"
        },
        {
            id: 4,
            title: "Produce Community Notice Maps",
            description: "Generate community-facing notice maps using finalized treatment areas",
            completed: false,
            priority: "critical"
        },
        {
            id: 5,
            title: "Pull Spray Notification List",
            description: "Ensure restricted layout is current, residents can be added any day",
            completed: false,
            priority: "critical"
        },
        {
            id: 6,
            title: "Update Website – Spray Map",
            description: "Update 'Scheduled Treatment Areas for Adult Mosquitoes' page BEFORE Kathy sends notifications",
            completed: false,
            priority: "critical"
        },
        {
            id: 7,
            title: "Send Notifications",
            description: "Email spray notifications and community maps to Kathy, send community maps to Annie",
            completed: false,
            priority: "critical"
        },
        {
            id: 8,
            title: "Update Website – Disease Monitoring",
            description: "Ensure all public-facing messaging remains consistent and aligned",
            completed: false,
            priority: "important"
        },
        {
            id: 9,
            title: "Prepare ULV Devices",
            description: "Ensure devices are charged and ready for Chris's deployment (Thursday 3pm)",
            completed: false,
            priority: "important"
        },
        {
            id: 10,
            title: "Verify Treatment Completion",
            description: "Next day: verify all areas were treated, update website to show no areas scheduled",
            completed: false,
            priority: "important"
        },
        {
            id: 11,
            title: "Update Surveillance Dashboard",
            description: "Indicate areas treated to aid in future pooling decisions",
            completed: false,
            priority: "important"
        },
        {
            id: 12,
            title: "Sync Mesa Device",
            description: "Verify spray records are present",
            completed: false,
            priority: "normal"
        }
    ]);

    const toggleStep = (id: number) => {
        setSteps(steps.map(step => 
            step.id === id ? { ...step, completed: !step.completed } : step
        ));
    };

    const resetWorkflow = () => {
        setSteps(steps.map(step => ({ ...step, completed: false })));
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case "critical": return "border-red-500 bg-red-50";
            case "important": return "border-orange-500 bg-orange-50";
            default: return "border-gray-300 bg-gray-50";
        }
    };

    const getPriorityIcon = (priority: string) => {
        switch (priority) {
            case "critical": return "🚨";
            case "important": return "⚠️";
            default: return "📋";
        }
    };

    const completedSteps = steps.filter(step => step.completed).length;
    const progressPercent = Math.round((completedSteps / steps.length) * 100);

    return (
        <div className="bg-white shadow-xl rounded-xl p-6 max-w-4xl mx-auto mt-10">
            <div className="mb-6">
                <h2 className="text-2xl font-semibold mb-2 text-gray-800">
                    🚁 Adult Mosquito Control Workflow
                </h2>
                <p className="text-sm text-gray-600 mb-4">
                    Triggered by positive mosquito pool detection. Complete steps in order for optimal resident communication and treatment effectiveness.
                </p>
                
                {/* Progress Bar */}
                <div className="mb-4">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>Progress: {completedSteps}/{steps.length} steps</span>
                        <span>{progressPercent}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                        <div 
                            className="bg-purple-600 h-3 rounded-full transition-all duration-300"
                            style={{ width: `${progressPercent}%` }}
                        ></div>
                    </div>
                </div>

                <div className="flex gap-2">
                    <button
                        onClick={resetWorkflow}
                        className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded text-sm transition-colors"
                    >
                        🔄 Reset Workflow
                    </button>
                </div>
            </div>

            {/* Critical Notice */}
            <div className="bg-red-100 border-l-4 border-red-500 p-4 mb-6">
                <div className="flex">
                    <div className="flex-shrink-0">
                        <span className="text-red-500 text-lg">⚠️</span>
                    </div>
                    <div className="ml-3">
                        <p className="text-sm text-red-700">
                            <strong>Priority Notice:</strong> If you cannot begin immediately or follow through, 
                            notify Jodi who can complete the entire process to avoid delays.
                        </p>
                    </div>
                </div>
            </div>

            {/* Steps List */}
            <div className="space-y-4">
                {steps.map((step) => (
                    <div
                        key={step.id}
                        className={`border rounded-lg p-4 transition-all ${
                            step.completed 
                                ? "bg-green-50 border-green-500" 
                                : getPriorityColor(step.priority)
                        }`}
                    >
                        <div className="flex items-start">
                            <button
                                onClick={() => toggleStep(step.id)}
                                className={`flex-shrink-0 mr-3 w-6 h-6 rounded border-2 flex items-center justify-center ${
                                    step.completed
                                        ? "bg-green-500 border-green-500 text-white"
                                        : "border-gray-300 hover:border-purple-500"
                                }`}
                            >
                                {step.completed ? "✓" : step.id}
                            </button>
                            
                            <div className="flex-grow">
                                <div className="flex items-center justify-between mb-2">
                                    <h3 className={`font-semibold ${
                                        step.completed ? "text-green-700 line-through" : "text-gray-800"
                                    }`}>
                                        Step {step.id}: {step.title}
                                    </h3>
                                    <span className="text-lg">
                                        {getPriorityIcon(step.priority)}
                                    </span>
                                </div>
                                <p className={`text-sm ${
                                    step.completed ? "text-green-600" : "text-gray-600"
                                }`}>
                                    {step.description}
                                </p>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Key Contacts */}
            <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h3 className="font-semibold text-blue-800 mb-2">📞 Key Contacts</h3>
                <div className="text-sm text-blue-700 space-y-1">
                    <div><strong>Map Review:</strong> Chris (primary), Jodi (backup)</div>
                    <div><strong>Notifications:</strong> Kathy (spray notifications), Annie (community maps)</div>
                    <div><strong>ULV Deployment:</strong> Chris (Thursday 3pm)</div>
                    <div><strong>Emergency Contact:</strong> Jodi (can complete entire process)</div>
                </div>
            </div>

            {/* Website Links */}
            <div className="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                <h3 className="font-semibold text-gray-800 mb-2">🌐 Website Updates Required</h3>
                <div className="text-sm text-gray-700 space-y-1">
                    <div>• <strong>Scheduled Treatment Areas:</strong> https://www.mosquitobuzz.net/scheduled-treatment-areas-for-adult-mosquitoes</div>
                    <div>• <strong>Disease Monitoring Dashboard:</strong> Update surveillance data</div>
                    <div>• <strong>NextDoor:</strong> Post in affected neighborhood groups</div>
                </div>
            </div>
        </div>
    );
}
