interface Props {
    username: string;
    onSelectWorkflow: (workflow: "geocode" | "update-surveillance" | "update-disease") => void;
}

export default function WorkflowOptionsCard({ username, onSelectWorkflow }: Props) {
    // This component displays the workflow options for the user to select.
    return (
        <div className="bg-white shadow-xl rounded-xl p-6 max-w-lg mx-auto mt-10 text-center">
            <h2 className="text-lg font-semibold mb-4 text-gray-800">
                👋 Hi {username}, what would you like to do?
            </h2>

            <div className="space-y-4">
                <button
                    onClick={() => onSelectWorkflow("geocode")}
                    className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg text-lg hover:bg-blue-700"
                >
                    📍 Geocode Addresses
                </button>

                <button
                    onClick={() => onSelectWorkflow("update-surveillance")}
                    className="w-full bg-orange-600 text-white px-6 py-3 rounded-lg text-lg hover:bg-orange-700"
                >
                    🦟 Update Surveillance Dashboard
                </button>

                <button
                    onClick={() => onSelectWorkflow("update-disease")}
                    className="w-full bg-red-600 text-white px-6 py-3 rounded-lg text-lg hover:bg-red-700"
                >
                    🧬 Update Disease Monitoring Dashboard
                </button>
            </div>
        </div>
    );
}
