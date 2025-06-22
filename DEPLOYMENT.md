# Deploying to Streamlit Cloud

This guide will walk you through the process of deploying your Government Tender AI Agent to Streamlit Cloud.

## Prerequisites

1. A GitHub account
2. Your project pushed to a GitHub repository
3. A Streamlit Cloud account (sign up at [share.streamlit.io](https://share.streamlit.io/))
4. An OpenRouter API key

## Deployment Steps

### 1. Push your code to GitHub

First, create a new GitHub repository and push your code:

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### 2. Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io/)
2. Log in with your GitHub account
3. Click "New app"
4. Select your repository, branch, and the `streamlit_app.py` file
5. Click "Deploy!"

### 3. Choose the right version for deployment

For deployment on Streamlit Cloud, you have two options:

#### Option A: Deploy full version (with web scraping)
- Use `streamlit_app.py` as the main file
- This version requires Playwright to be properly installed in the cloud
- Note that web scraping may be less reliable in cloud environments

#### Option B: Deploy cloud-friendly version (recommended)
- Use `cloud_app.py` as the main file
- This version uses sample data instead of live web scraping
- More reliable in cloud environments with fewer dependencies

### 4. Set up secrets

Your app needs access to the OpenRouter API key. To set it up:

1. Once your app is deployed, go to the app settings
2. In the sidebar, click on "Secrets"
3. Add your API key:

```toml
# .streamlit/secrets.toml
OPENROUTER_API_KEY = "your_api_key_here"
```

### 4. Advanced configuration (optional)

If you need to modify your app's behavior in the cloud:

1. In your app settings, go to "Advanced settings"
2. You can customize:
   - Python version
   - Package dependencies
   - Resource allocation

### 5. Playwright setup

If you're using Playwright for web scraping, you'll need to set up a custom build command:

1. In your app settings, go to "Advanced settings"
2. In the "Advanced" section, add a custom build command:
```
pip install playwright && playwright install --with-deps chromium
```

## Troubleshooting

- **ImportError**: Make sure all required packages are in your `requirements.txt` file
- **API errors**: Verify that your secrets are correctly set up
- **Playwright errors**: Some cloud environments have limitations with browser automation. If you encounter issues with the full version, switch to the cloud-friendly version (`cloud_app.py`)
- **Memory errors**: If your app exceeds memory limits, try setting `memory=2GB` in the advanced settings

## Using the Cloud-Friendly Version

For reliable deployment without web scraping dependencies, use the cloud-friendly version:

1. In the "Deploy" section of Streamlit Cloud, specify `cloud_app.py` as the main file
2. This version uses pre-defined tender templates and focuses on the LLM's analysis and summaries
3. You won't need to install Playwright browsers, simplifying the deployment process

## Resources

- [Streamlit Cloud Documentation](https://docs.streamlit.io/streamlit-cloud)
- [GitHub Documentation](https://docs.github.com/en)
- [Playwright Documentation](https://playwright.dev/python/)
