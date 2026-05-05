import 'dotenv/config';
import http from 'http';
import axios from 'axios';
import querystring from 'querystring';
import open from 'open';
import fs from 'fs/promises';
import { EncryptJWT, calculateJwkThumbprint, base64url } from 'jose';
import { hkdf } from '@panva/hkdf';
import crypto from 'crypto';

const PORT = 3001;
const clientID = process.env.CLIENT_ID;
const clientSecret = process.env.CLIENT_SECRET;
const redirectURI = process.env.REDIRECT_URI;
const authURI =
  'https://login.microsoftonline.com/63982aff-fb6c-4c22-973b-70e4acfb63e6/oauth2/authorize';
const tokenURI =
  'https://login.microsoftonline.com/63982aff-fb6c-4c22-973b-70e4acfb63e6/oauth2/token';
const scopes = 'openid profile email';

async function getDerivedEncryptionKey(enc, keyMaterial, salt) {
  let length;
  switch (enc) {
    case 'A256CBC-HS512':
      length = 64;
      break;
    case 'A256GCM':
      length = 32;
      break;
    default:
      throw new Error('Unsupported JWT Content Encryption Algorithm');
  }
  return await hkdf(
    'sha256',
    keyMaterial,
    salt,
    `Auth.js Generated Encryption Key (${salt})`,
    length
  );
}

async function createJwe(payload) {
  const alg = 'dir';
  const enc = 'A256CBC-HS512';
  const salt = '__Secure-authjs.session-token';
  const secret = process.env.NEXTAUTH_SECRET;
  const encryptionSecret = await getDerivedEncryptionKey(enc, secret, salt);
  const thumbprint = await calculateJwkThumbprint(
    { kty: 'oct', k: base64url.encode(encryptionSecret) },
    `sha${encryptionSecret.byteLength << 3}`
  );

  const jweToken = await new EncryptJWT(payload)
    .setProtectedHeader({ alg, enc, kid: thumbprint })
    .setIssuedAt()
    .setExpirationTime('2h')
    .setJti(crypto.randomUUID())
    .encrypt(encryptionSecret);

  return jweToken;
}

async function startOAuthFlow(callback) {
  // 01. Creating authorization URL
  const authURL = `${authURI}?${querystring.stringify({
    response_type: 'code',
    client_id: clientID,
    redirect_uri: redirectURI,
    scope: scopes,
  })}`;
  console.log('Opening browser for Microsoft authentication...');

  // 02. Opening the browser to start authorize flow
  await open(authURL);

  // 03. Start a local server to listen for the callback
  const server = http.createServer(async (req, res) => {
    if (req.url.startsWith('/callback')) {
      // Parse the authorization code from the URL
      const queryParams = querystring.parse(req.url.split('?')[1]);
      const authorizationCode = queryParams.code;

      // 04: Exchange authorization code for tokens
      try {
        const tokenResponse = await axios.post(
          tokenURI,
          querystring.stringify({
            grant_type: 'authorization_code',
            code: authorizationCode,
            redirect_uri: redirectURI,
            client_id: clientID,
            client_secret: clientSecret,
          }),
          { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
        );

        const result = {
          ...tokenResponse.data,
        };
        // Write the result to a JSON file
        await fs.writeFile(
          '../fixtures/session.json',
          JSON.stringify(result, null, 2),
          'utf-8'
        );
        console.log('Authentication data saved to fixtures/session.json');

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(result, null, 2));
        callback(server);
      } catch (error) {
        console.error(
          'Error during token exchange or user info retrieval:',
          error
        );
        res.writeHead(500, { 'Content-Type': 'text/html' });
        res.end('<h1>Authentication Failed</h1>');
      }
    }
  });

  // 06. Start the server
  server.listen(PORT, () => {
    console.log(
      `Listening for OAuth callback on http://localhost:${PORT}/callback`
    );
  });
}

// Trigger the auth flow
startOAuthFlow((server) => {
  setTimeout(() => {
    server.close(() => {
      console.log('Server closed after token retrieval.');
      process.exit(0);
    });
    process.exit(0);
  }, 1000);
});
