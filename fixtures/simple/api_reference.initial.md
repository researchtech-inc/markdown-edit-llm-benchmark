# API Reference Guide

## Introduction

This document provides a comprehensive reference for the DataSync API. All endpoints follow REST conventions and return JSON responses.

## Authentication

All API requests require authentication using Bearer tokens.

### Obtaining a Token

Send a POST request to /auth/token with your credentials:

```
POST /auth/token
Content-Type: application/json

{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret"
}
```

### Token Lifetime

Access tokens expire after 24 hours. Refresh tokens are valid for 30 days.

## Base URL

All API endpoints are relative to:

```
https://api.datasync.example.com/v1
```

## Rate Limiting

API requests are limited to 100 requests per minute per client. Exceeding this limit returns a 429 status code.

## Endpoints

### Users

#### GET /users

Retrieves a list of all users in the organization.

Parameters:
- page (optional): Page number for pagination
- limit (optional): Number of results per page (default: 20)
- status (optional): Filter by user status

Response:
```
{
  "users": [...],
  "total": 150,
  "page": 1
}
```

#### GET /users/{id}

Retrieves a specific user by ID.

Parameters:
- id (required): The unique user identifier

Response:
```
{
  "id": "usr_123",
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### POST /users

Creates a new user account.

Request Body:
```
{
  "email": "newuser@example.com",
  "name": "Jane Smith",
  "role": "member"
}
```

#### DELETE /users/{id}

Removes a user from the organization.

### Projects

#### GET /projects

Lists all projects accessible to the authenticated user.

Parameters:
- status (optional): Filter by project status
- owner (optional): Filter by owner ID

#### GET /projects/{id}

Retrieves detailed information about a specific project.

#### POST /projects

Creates a new project.

Request Body:
```
{
  "name": "Project Name",
  "description": "Project description",
  "visibility": "private"
}
```

#### PUT /projects/{id}

Updates an existing project.

#### DELETE /projects/{id}

Deletes a project and all associated data.

### Files

#### GET /files

Lists files in a project.

Parameters:
- project_id (required): The project identifier
- path (optional): Directory path to list

#### POST /files/upload

Uploads a new file.

Request: multipart/form-data with file content.

#### GET /files/{id}/download

Downloads a file by its ID.

## Error Handling

### Error Response Format

All errors return a consistent JSON structure:

```
{
  "error": {
    "code": "invalid_request",
    "message": "Detailed error message",
    "details": {}
  }
}
```

### Common Error Codes

- 400: Bad Request - Invalid parameters
- 401: Unauthorized - Invalid or expired token
- 403: Forbidden - Insufficient permissions
- 404: Not Found - Resource does not exist
- 429: Too Many Requests - Rate limit exceeded
- 500: Internal Server Error - Server-side issue

## Webhooks

Configure webhooks to receive real-time notifications.

### Supported Events

- user.created
- user.deleted
- project.created
- project.updated
- file.uploaded

### Webhook Payload

```
{
  "event": "user.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {...}
}
```

## SDK Support

Official SDKs are available for:

- Python
- JavaScript
- Ruby
- Go

## Changelog

### Version 1.2 (Current)

- Added file upload endpoint
- Improved rate limiting
- Bug fixes

### Version 1.1

- Added webhook support
- New project visibility options

### Version 1.0

- Initial release
