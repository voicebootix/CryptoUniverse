# Database SSL Configuration

## Overview

CryptoUniverse Enterprise supports secure SSL/TLS connections to PostgreSQL databases with flexible configuration options for different deployment environments.

## Environment Variables

### `DATABASE_SSL_REQUIRE`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Force SSL connection to the database
- **Example**: `DATABASE_SSL_REQUIRE=true`

### `DATABASE_SSL_ROOT_CERT`
- **Type**: String (file path)
- **Default**: None
- **Description**: Path to custom CA certificate file for database SSL verification
- **Example**: `DATABASE_SSL_ROOT_CERT=/app/certs/database-ca.pem`

### `DATABASE_SSL_INSECURE`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Disable SSL certificate verification (⚠️ **Use only for development/testing**)
- **Example**: `DATABASE_SSL_INSECURE=true`

## Configuration Examples

### Production with Valid CA Certificate
```bash
DATABASE_SSL_REQUIRE=true
DATABASE_SSL_ROOT_CERT=/app/certs/ca-certificate.pem
```

### Production with Self-Signed Certificates (Emergency Only)
```bash
DATABASE_SSL_REQUIRE=true
DATABASE_SSL_INSECURE=true
```

### Development/Local
```bash
# No SSL configuration needed for local development
```

## Security Notes

⚠️ **Important**: Setting `DATABASE_SSL_INSECURE=true` disables certificate verification and should **never** be used in production environments unless as a temporary emergency measure. This exposes the connection to man-in-the-middle attacks.

✅ **Recommended**: Always use proper CA certificates in production environments.

## Automatic SSL Detection

The system automatically enables SSL for:
- Supabase database URLs
- When `DATABASE_SSL_REQUIRE=true` is set
- When `DATABASE_SSL_ROOT_CERT` is provided

## Troubleshooting

### Common SSL Issues

1. **Certificate verification failed**: Use `DATABASE_SSL_ROOT_CERT` with the correct CA certificate
2. **Self-signed certificate errors**: Only for development, use `DATABASE_SSL_INSECURE=true`
3. **Connection timeouts**: Check firewall settings and SSL port availability

### Logs

SSL configuration warnings and errors are logged with clear messages:
```
WARNING: DATABASE_SSL_INSECURE=true: disabling certificate and hostname verification
```