// 1. Import required modules
const axios = require("axios");
const fs = require("fs");

// 2. Set your VectorSurv Gateway username and password
const username = "ssakib"; // <-- Your username
const password = "cmad5598961085"; // <-- Your password

// 3. Authentication URL
const authUrl = "https://api.vectorsurv.org/login";

// 4. Authenticate and save full response
async function authenticateAndSaveFullResponse() {
  try {
    const response = await axios.post(authUrl, {
      username,
      password,
    });

    // Save the entire response.data to a file
    fs.writeFileSync("../coding/vectorsurv/response.txt", JSON.stringify(response.data, null, 2));

    console.log("✅ Full authentication response saved to response.txt");
  } catch (error) {
    console.error("❌ Authentication failed:", error.message);
  }
}

// 5. Run the function
authenticateAndSaveFullResponse();

