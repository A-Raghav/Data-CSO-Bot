# Welcome to StatsEye - Your Data Research Assistant 👩‍🎓🎓

## Simplifying Data Research with Central Statistics Office (CSO) Data

StatsEye is designed to transform how researchers, analysts, and curious minds interact with statistical data available on [Data-CSO website](www.data.cso.ie). No more navigating through endless clicks and downloads – just ask what you need to know.

## What StatsEye Can Do For You 💡

- **Find Relevant Datasets** - Simply describe what you're looking for, and StatsEye will locate the right datasets from the CSO database
- **Analyze Data Instantly** - Get insights, trends, and citations without downloading or processing files yourself
- **Answer Complex Questions** - Ask questions about economic trends, demographic patterns, or statistical relationships
- **Multi-Turn Conversations** - Refine your inquiries and build on previous questions for deeper analysis

## How to Use StatsEye �

1. **Ask a Question** - Start with what you're trying to understand (e.g., "What's the trend in Irish housing prices over the last decade?")
2. **Refine Your Inquiry** - StatsEye may ask clarifying questions to better understand your needs
3. **Get Insights** - Receive analysis, insights, and Data-CSO citations directly in the chat
4. **Build on Results** - Ask follow-up questions based on the information provided

## Behind the Technology ⚙️

StatsEye combines advanced AI capabilities through:

- **Intelligent Agent Framework** - Built with LangGraph to provide reasoning and context-aware responses
- **3-Layer Hybrid Retrieval** - Optimizes search for the most relevant datasets from the CSO database
- **Real-Time Python Analysis** - Performs data analysis on demand using a specialized Python execution agent
- **Thoughtful Review Process** - Validates all analyses through a reviewer agent before presenting results

## Try These Sample Queries 🚀

- "Show me unemployment rates by county for the last 5 years"
- "What's the population growth trend in Dublin compared to other cities?"
- "Analyze the relationship between education levels and income across different regions"
- "How has inflation affected consumer spending in the past year?"

## About StatsEye

StatsEye was developed to address the challenges researchers face when working with statistical data from the CSO website. Our mission is to make data more accessible and insights more discoverable.

*Start your data journey with a simple question above!*

___

# Developer Info
### Building and Uploading Docker image into Google Cloud Artifact Registry
1. Authenticate gcloud: `gcloud auth configure-docker europe-west2-docker.pkg.dev`
2. Run: `docker buildx create --use --name xbuilder || true`
3. Run: `docker buildx build --platform linux/amd64 -t europe-west2-docker.pkg.dev/data-cso-project/quickstart-docker-repo/chainlit_hello_world_app:v0.0.3 --push .` (make sure to change the tag)
4. Verify the manifest includes amd64: `docker buildx imagetools inspect europe-west2-docker.pkg.dev/data-cso-project/quickstart-docker-repo/chainlit_hello_world_app:v0.0.3`

### Dev-Mode
- Make sure the following env variables are correctly configured in `.env` file in root:
    - `GOOGLE_API_KEY`
    - `CHAINLIT_AUTH_SECRET`
    - `OAUTH_GOOGLE_CLIENT_ID`
    - `OAUTH_GOOGLE_CLIENT_SECRET`
    - `REDIS_URL`
- After building the above image (remove the `--push` to build the image without pushing it on GCP), run the docker-image using `docker-compose up` and start the `redis-stack` container, and then test if everything is working fine.
