# Google OAuth Setup Guide

## Root Cause Analysis

The "Access blocked: This app's request is invalid" error occurs due to a **redirect URI mismatch** between:

1. **Frontend Request**: Sends `window.location.origin + '/auth/callback'`
2. **Backend Configuration**: Uses `f"{settings.BASE_URL}/api/v1/auth/oauth/callback/google"`
3. **Google Console**: Expects the exact redirect URI configured in your OAuth app

## Step 1: Google Cloud Console Configuration

### 1.1 Create OAuth 2.0 Client ID

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project or create a new one
3. Navigate to **APIs & Services** > **Credentials**
4. Click **+ CREATE CREDENTIALS** > **OAuth client ID**
5. Choose **Web application**

### 1.2 Configure Authorized Redirect URIs

Add these **exact** redirect URIs to your Google OAuth client:

**For Production (Render):**
```
https://cryptouniverse.onrender.com/api/v1/auth/oauth/callback/google
```

**For Development:**
```
http://localhost:8000/api/v1/auth/oauth/callback/google
```

**For Frontend Development (if needed):**
```
http://localhost:5173/auth/callback
```

### 1.3 Configure Authorized JavaScript Origins

Add these origins:

**For Production:**
```
https://cryptouniverse-frontend.onrender.com
https://cryptouniverse.onrender.com
```

**For Development:**
```
http://localhost:5173
http://localhost:8000
```

## Step 2: Environment Variables Setup

### 2.1 Update Your Environment File

Add these variables to your `.env` file:

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-oauth-client-id-from-console
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret-from-console

# Base URL Configuration (CRITICAL)
BASE_URL=https://cryptouniverse.onrender.com  # For production
# BASE_URL=http://localhost:8000  # For development
```

### 2.2 Render Environment Variables

In your Render dashboard, add these environment variables:

1. `GOOGLE_CLIENT_ID` = `your-google-oauth-client-id`
2. `GOOGLE_CLIENT_SECRET` = `your-google-oauth-client-secret`
3. `BASE_URL` = `https://cryptouniverse.onrender.com`

## Step 3: OAuth Consent Screen Configuration

### 3.1 Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Choose **External** (for public users) or **Internal** (for organization only)
3. Fill in required fields:
   - **App name**: CryptoUniverse
   - **User support email**: your-email@domain.com
   - **Developer contact information**: your-email@domain.com

### 3.2 Add Scopes

Add these scopes:
- `openid`
- `email`
- `profile`

### 3.3 Add Test Users (if in testing mode)

Add test email addresses that can access your app during development.

## Step 4: Verification Requirements

### 4.1 App Verification (For Production)

If your app requests sensitive scopes, you may need to verify your app:

1. Complete the OAuth consent screen
2. Add privacy policy URL
3. Add terms of service URL
4. Submit for verification if required

### 4.2 Domain Verification

For production domains, you may need to verify domain ownership:

1. Go to **Google Search Console**
2. Add and verify your domain
3. Link it to your OAuth application

## Step 5: Testing the Flow

### 5.1 Development Testing

1. Start your backend server: `python main.py`
2. Start your frontend server: `npm run dev`
3. Navigate to `http://localhost:5173/auth/login`
4. Click "Sign up with Google"
5. Verify the redirect works correctly

### 5.2 Production Testing

1. Deploy your changes to Render
2. Navigate to your production frontend URL
3. Test the Google OAuth flow
4. Check browser developer tools for any errors

## Step 6: Common Issues and Solutions

### 6.1 "redirect_uri_mismatch" Error

**Cause**: The redirect URI in the request doesn't match what's configured in Google Console.

**Solution**: 
1. Check the exact redirect URI being sent in the OAuth request
2. Ensure it matches exactly what's configured in Google Console
3. Check for trailing slashes, http vs https, etc.

### 6.2 "origin_mismatch" Error

**Cause**: The JavaScript origin doesn't match the configured origins.

**Solution**:
1. Add the exact origin to Authorized JavaScript origins
2. Ensure protocol (http/https) matches
3. Don't include paths, only the origin

### 6.3 "access_blocked" Error

**Cause**: App is not verified or has policy violations.

**Solution**:
1. Complete OAuth consent screen configuration
2. Add required policies (privacy, terms)
3. Submit for verification if needed

## Step 7: Security Best Practices

### 7.1 Environment Security

- Never commit OAuth secrets to version control
- Use different OAuth clients for development/production
- Rotate secrets periodically

### 7.2 Scope Minimization

- Only request necessary scopes
- Use incremental authorization when possible
- Clearly explain why each scope is needed

### 7.3 State Parameter

- Always use and validate the state parameter (already implemented)
- Use cryptographically secure random values
- Validate state on callback

## Step 8: Monitoring and Debugging

### 8.1 Google Cloud Console Monitoring

- Monitor OAuth usage in Google Cloud Console
- Check for error rates and patterns
- Review quota usage

### 8.2 Application Logging

- Log OAuth requests and responses (without secrets)
- Monitor failed authentication attempts
- Track user registration patterns

## Troubleshooting Checklist

- [ ] Google OAuth client ID and secret are correctly set
- [ ] Redirect URIs exactly match in Google Console
- [ ] JavaScript origins are correctly configured
- [ ] BASE_URL environment variable is correct
- [ ] OAuth consent screen is properly configured
- [ ] Test users are added (if in testing mode)
- [ ] App is verified (if required)
- [ ] All environment variables are deployed to Render

## Support

If you continue to experience issues:

1. Check the browser developer console for detailed error messages
2. Review Google Cloud Console audit logs
3. Verify all URLs and configurations match exactly
4. Test with a fresh incognito browser session

The key to resolving OAuth issues is ensuring **exact matches** between your application configuration and Google Console settings.
