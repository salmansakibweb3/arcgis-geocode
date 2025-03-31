const express = require('express');
const axios = require('axios');
const path = require('path');
const multer = require('multer');
const upload = multer({ dest: 'uploads/' });

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

const PYTHON_BACKEND = 'http://localhost:5000';

// Render main page with defaults for all variables
app.get('/', (req, res) => {
  res.render('index', { 
    loginResult: null, 
    oauthUrl: null,
    awaitingCode: false,
    client_id: '',
    geocodeResult: null, 
    coordsResult: null 
  });
});

app.post('/login', async (req, res) => {
  const { client_id, code } = req.body;
  if (!code) {
    try {
      const startResp = await axios.post(`${PYTHON_BACKEND}/start-login`, { client_id });
      const oauthUrl = startResp.data.oauth_url;
      res.render('index', {
        loginResult: null,
        oauthUrl: oauthUrl,
        awaitingCode: true,
        client_id: client_id,
        geocodeResult: null,
        coordsResult: null
      });
    } catch (error) {
      res.render('index', {
        loginResult: { error: error.message },
        oauthUrl: null,
        awaitingCode: false,
        client_id: client_id,
        geocodeResult: null,
        coordsResult: null
      });
    }
  } else {
    try {
      const completeResp = await axios.post(`${PYTHON_BACKEND}/complete-login`, { client_id, code });
      res.render('index', {
        loginResult: completeResp.data,
        oauthUrl: null,
        awaitingCode: false,
        client_id: client_id,
        geocodeResult: null,
        coordsResult: null
      });
    } catch (error) {
      res.render('index', {
        loginResult: { error: error.message },
        oauthUrl: null,
        awaitingCode: true,
        client_id: client_id,
        geocodeResult: null,
        coordsResult: null
      });
    }
  }
});

// Handle CSV geocoding using file upload
app.post('/geocode', upload.single('csv'), async (req, res) => {
  const { address_col, city_col } = req.body;
  const csvPath = req.file.path;
  try {
    const response = await axios.post(`${PYTHON_BACKEND}/geocode`, { csvPath, address_col, city_col });
    res.render('index', { 
      loginResult: null,
      oauthUrl: null,
      awaitingCode: false,
      client_id: '',
      geocodeResult: response.data,
      coordsResult: null
    });
  } catch (error) {
    res.render('index', { 
      loginResult: null,
      oauthUrl: null,
      awaitingCode: false,
      client_id: '',
      geocodeResult: { error: error.message },
      coordsResult: null
    });
  }
});

// Handle generating coordinates using file upload
app.post('/generate-coords', upload.single('input_csv'), async (req, res) => {
  const input_csv = req.file.path;
  try {
    const response = await axios.post(`${PYTHON_BACKEND}/generate-coords`, { input_csv });
    res.render('index', { 
      loginResult: null,
      oauthUrl: null,
      awaitingCode: false,
      client_id: '',
      geocodeResult: null,
      coordsResult: response.data
    });
  } catch (error) {
    res.render('index', { 
      loginResult: null,
      oauthUrl: null,
      awaitingCode: false,
      client_id: '',
      geocodeResult: null,
      coordsResult: { error: error.message }
    });
  }
});

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Node.js frontend listening on port ${PORT}`);
});
