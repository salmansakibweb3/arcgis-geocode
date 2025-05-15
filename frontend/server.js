// server.js
const express = require('express');
const axios = require('axios');
const path = require('path');
const multer = require('multer');
const fs = require('fs');
const FormData = require('form-data');

const upload = multer({ dest: 'uploads/' });
const app = express();

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));

const PYTHON_BACKEND = process.env.PYTHON_BACKEND || 'http://localhost:5000';

// Render main page
app.get('/', (req, res) => {
  res.render('index', {
    loginResult: null,
    oauthUrl: null,
    awaitingCode: false,
    client_id: '',
    geocodeResult: null,
    coordsResult: null,
    prepareResult: null,
    updateResult: null
  });
});

// OAuth routes
app.post('/login', async (req, res) => {
  const { client_id, code } = req.body;
  if (!code) {
    try {
      const startResp = await axios.post(`${PYTHON_BACKEND}/start-login`, { client_id });
      res.render('index', {
        loginResult: null,
        oauthUrl: startResp.data.oauth_url,
        awaitingCode: true,
        client_id,
        geocodeResult: null,
        coordsResult: null,
        prepareResult: null,
        updateResult: null
      });
    } catch (error) {
      res.render('index', {
        loginResult: { error: error.message },
        oauthUrl: null,
        awaitingCode: false,
        client_id,
        geocodeResult: null,
        coordsResult: null,
        prepareResult: null,
        updateResult: null
      });
    }
  } else {
    try {
      const completeResp = await axios.post(`${PYTHON_BACKEND}/complete-login`, { client_id, code });
      res.render('index', {
        loginResult: completeResp.data,
        oauthUrl: null,
        awaitingCode: false,
        client_id,
        geocodeResult: null,
        coordsResult: null,
        prepareResult: null,
        updateResult: null
      });
    } catch (error) {
      res.render('index', {
        loginResult: { error: error.message },
        oauthUrl: null,
        awaitingCode: true,
        client_id,
        geocodeResult: null,
        coordsResult: null,
        prepareResult: null,
        updateResult: null
      });
    }
  }
});

// Geocode CSV
app.post('/geocode', upload.single('csv'), async (req, res) => {
  const { address_col, city_col } = req.body;
  const csvPath = req.file.path;
  const form = new FormData();
  form.append('csv', fs.createReadStream(csvPath), req.file.originalname);
  form.append('address_col', address_col);
  form.append('city_col', city_col);

  try {
    const backendRes = await axios.post(
      `${PYTHON_BACKEND}/geocode`,
      form,
      { headers: form.getHeaders(), responseType: 'stream' }
    );
    res.setHeader('Content-Disposition', backendRes.headers['content-disposition']);
    res.setHeader('Content-Type', backendRes.headers['content-type']);
    backendRes.data.pipe(res);
  } catch (error) {
    res.render('index', {
      loginResult: null,
      oauthUrl: null,
      awaitingCode: false,
      client_id: '',
      geocodeResult: { error: error.message },
      coordsResult: null,
      prepareResult: null,
      updateResult: null
    });
  }
});

// Generate Coordinates
app.post('/generate-coords', upload.single('input_csv'), async (req, res) => {
  const csvPath = req.file.path;
  const form = new FormData();
  form.append('input_csv', fs.createReadStream(csvPath), req.file.originalname);

  try {
    const backendRes = await axios.post(
      `${PYTHON_BACKEND}/generate-coords`,
      form,
      { headers: form.getHeaders(), responseType: 'stream' }
    );
    res.setHeader('Content-Disposition', backendRes.headers['content-disposition']);
    res.setHeader('Content-Type', backendRes.headers['content-type']);
    backendRes.data.pipe(res);
  } catch (error) {
    res.render('index', {
      loginResult: null,
      oauthUrl: null,
      awaitingCode: false,
      client_id: '',
      geocodeResult: null,
      coordsResult: { error: error.message },
      prepareResult: null,
      updateResult: null
    });
  }
});

// Prepare Data: sum last 3 columns into 'total_abundance'
app.post('/prepare-data', upload.single('csv_prepare'), async (req, res) => {
  const csvPath      = req.file.path;
  const originalName = req.file.originalname;
  const form         = new FormData();

  // Preserve original client filename
  form.append('csv_prepare', fs.createReadStream(csvPath), originalName);

  try {
    const backendRes = await axios.post(
      `${PYTHON_BACKEND}/prepare-data`,
      form,
      {
        headers: form.getHeaders(),
        responseType: 'stream'
      }
    );
    // Forward headers so browser auto-downloads
    res.setHeader(
      'Content-Disposition',
      backendRes.headers['content-disposition']
    );
    res.setHeader('Content-Type', backendRes.headers['content-type']);
    backendRes.data.pipe(res);
  } catch (error) {
    const errMsg = error.response?.data || { error: error.message };
    res.render('index', {
      loginResult:   null,
      oauthUrl:      null,
      awaitingCode:  false,
      client_id:     '',
      geocodeResult: null,
      coordsResult:  null,
      prepareResult: errMsg,
      updateResult:  null
    });
  }
});

// Update Dashboard Layer: Overwrite hosted feature layer
app.post('/update-layer', upload.single('csv_update'), async (req, res) => {
  const csvPath      = req.file.path;
  const SOURCE_FILENAME = req.file.originalname;  // Preserve original filename
  console.log(`[DEBUG] Using source filename for upload: ${SOURCE_FILENAME}`);

  const form = new FormData();
  form.append('csv_update', fs.createReadStream(csvPath), SOURCE_FILENAME);

  try {
    const backendRes = await axios.post(
      `${PYTHON_BACKEND}/update-layer`,
      form,
      { headers: form.getHeaders() }
    );
    res.render('index', {
      loginResult:   null,
      oauthUrl:      null,
      awaitingCode:  false,
      client_id:     '',
      geocodeResult: null,
      coordsResult:  null,
      prepareResult: null,
      updateResult:  backendRes.data
    });
  } catch (error) {
    const errMsg = error.response?.data || { error: error.message };
    res.render('index', {
      loginResult:   null,
      oauthUrl:      null,
      awaitingCode:  false,
      client_id:     '',
      geocodeResult: null,
      coordsResult:  null,
      prepareResult: null,
      updateResult:  errMsg
    });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Node.js frontend listening on port ${PORT}`));
