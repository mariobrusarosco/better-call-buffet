# Postman Collection for Better Call Buffet API

This guide will help you set up and use the Postman collection to test the Better Call Buffet API.

## Files Provided

1. `better-call-buffet-postman-collection.json` - The Postman collection with all API endpoints
2. `postman-environment.json` - Environment variables for the API

## Import Instructions

### Step 1: Install Postman

If you haven't already, download and install Postman from [postman.com](https://www.postman.com/downloads/).

### Step 2: Import the Collection

1. Open Postman
2. Click on **Import** button in the top-left corner
3. Choose **File** > **Upload Files**
4. Select the `better-call-buffet-postman-collection.json` file
5. Click **Import**

### Step 3: Import the Environment

1. Click on **Import** again
2. Choose **File** > **Upload Files**
3. Select the `postman-environment.json` file
4. Click **Import**

### Step 4: Select the Environment

1. In the top-right corner, click on the environment dropdown
2. Select "Better Call Buffet API - Local"

## Using the Collection

### Authentication Flow

The collection is set up with an authentication workflow:

1. First, register a user using the **Register User** request in the Authentication folder
2. Then, log in with the **Login** request - this will automatically save your auth token to the environment variables
3. All other requests will use this token automatically

### Testing Endpoints

The collection is organized by domain:

- **Authentication** - User registration and login
- **Users** - User profile management
- **Accounts** - Financial accounts management
- **Categories** - Transaction categories with hierarchical structure
- **Transactions** - Financial transactions with various types

Each request includes:
- Pre-configured headers
- Example request bodies where needed
- Parameters with descriptions
- Documentation about what each endpoint does

### Testing the API Locally

1. Make sure your Better Call Buffet API is running locally at `http://localhost:8000`
2. If your API is running on a different URL, update the `baseUrl` variable in the environment settings

## Advanced Usage

### Creating an Environment for Production

You can duplicate the environment to create a production version:

1. Click on the eye icon next to the environment dropdown
2. Click on "Duplicate" next to the "Better Call Buffet API - Local" environment
3. Rename it to "Better Call Buffet API - Production" 
4. Update the `baseUrl` to your production URL
5. Click **Save**

### Adding Tests

You can add tests to validate responses:

1. Open any request
2. Go to the "Tests" tab
3. Add JavaScript test code, for example:

```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response contains expected data", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('id');
});
```

### Setting Up a Collection Runner

You can run multiple requests in sequence:

1. Click on the collection name
2. Click on the "Run" button
3. Select the requests you want to run
4. Choose the environment 
5. Click "Run Better Call Buffet API"

## Troubleshooting

### Authentication Issues

If you encounter "Unauthorized" errors:
1. Check that you've successfully run the Login request
2. Verify the `authToken` environment variable has been set (check via the eye icon)
3. Ensure your token hasn't expired (run the Login request again)

### Connection Issues

If you can't connect to the API:
1. Verify the API is running locally
2. Check that the `baseUrl` environment variable is correct
3. Ensure your network allows the connection (no firewall blocking)

### Request Body Errors

If your requests are rejected:
1. Check the response for detailed error messages
2. Ensure your JSON is valid
3. Verify all required fields are included in the request body 