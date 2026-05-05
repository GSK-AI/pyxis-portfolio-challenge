import 'dotenv/config';
import axios from 'axios';
import fs from 'fs/promises';

/**
 * Non-interactive authentication for CI environments
 * This uses client credentials flow or a pre-generated token
 */

const clientID = process.env.CLIENT_ID;
const clientSecret = process.env.CLIENT_SECRET;
const tokenURI =
  process.env.TOKEN_URI ||
  'https://login.microsoftonline.com/63982aff-fb6c-4c22-973b-70e4acfb63e6/oauth2/token';

async function authenticateForCI() {
  try {
    console.log('Starting non-interactive authentication for CI...');

    // Method 1: Use pre-configured token (recommended for CI)
    if (process.env.E2E_ID_TOKEN) {
      console.log('Using pre-configured E2E token from environment');

      // Validate token format (basic check for JWT structure)
      const token = process.env.E2E_ID_TOKEN.trim();
      if (!token.includes('.') || token.split('.').length !== 3) {
        console.error(
          '❌ Invalid token format. Expected JWT format (xxx.yyy.zzz)'
        );
        process.exit(1);
      }

      const sessionData = {
        id_token: token,
        token_type: 'Bearer',
        expires_in: 3600,
        scope: 'openid profile email',
      };

      await fs.writeFile(
        '../fixtures/session.json',
        JSON.stringify(sessionData, null, 2),
        'utf-8'
      );

      console.log(
        '✅ Session file created successfully with pre-configured token'
      );
      console.log(`Token length: ${token.length} characters`);
      return;
    }

    // Method 2: Client Credentials Flow (if supported)
    if (clientID && clientSecret) {
      console.log('Attempting client credentials flow...');

      const tokenResponse = await axios.post(
        tokenURI,
        new URLSearchParams({
          grant_type: 'client_credentials',
          client_id: clientID,
          client_secret: clientSecret,
          scope: 'https://graph.microsoft.com/.default',
        }),
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        }
      );

      const sessionData = {
        id_token: tokenResponse.data.access_token,
        token_type: tokenResponse.data.token_type || 'Bearer',
        expires_in: tokenResponse.data.expires_in || 3600,
        scope: tokenResponse.data.scope || 'openid profile email',
      };

      await fs.writeFile(
        '../fixtures/session.json',
        JSON.stringify(sessionData, null, 2),
        'utf-8'
      );

      console.log(
        '✅ Session file created successfully with client credentials'
      );
      return;
    }

    // Method 3: Fallback - create a dummy session for testing
    console.log(
      '⚠️  No authentication method available, creating dummy session...'
    );
    console.log(
      'Note: This may cause E2E tests to fail if real authentication is required'
    );

    const dummySession = {
      id_token: 'dummy_token_for_testing',
      token_type: 'Bearer',
      expires_in: 3600,
      scope: 'openid profile email',
      note: 'This is a dummy token for testing purposes',
    };

    await fs.writeFile(
      '../fixtures/session.json',
      JSON.stringify(dummySession, null, 2),
      'utf-8'
    );

    console.log('⚠️  Dummy session file created');
  } catch (error) {
    console.error('❌ Authentication failed:', error.message);

    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }

    process.exit(1);
  }
}

// Run authentication
authenticateForCI();
