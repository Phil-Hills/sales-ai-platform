# Sales AI Platform - Salesforce Native App

This directory contains the Salesforce metadata (Apex, LWC) required to run the Sales AI Platform inside Salesforce.

## Components

### Apex Classes
- `SalesAICallout.cls`: Handles API calls to the Cloud Run backend.
    - **Endpoint**: Defaults to `https://movement-voice-demo-511662304947.us-central1.run.app`. Update this in the class or use Named Credentials for production.
- `SalesAIOrchestrator.cls`: Handles asynchronous lead handoffs to the platform.

### Lightning Web Components (LWC)
- `salesPlatformAgent`: The main chat interface.
    - **Features**: Real-time chat, AI research, Paywall overlay, Premium badge.
    - ** Targets**: `Lead` and `Opportunity` Record Pages.

## Deployment Instructions

1.  **Authorize your Org**:
    ```bash
    sf org login web --alias sales-ai-dev --set-default
    ```

2.  **Deploy Source**:
    ```bash
    sf project deploy start --target-org sales-ai-dev
    ```

3.  **Post-Deployment Setup**:
    - Go to **Setup > Remote Site Settings**.
    - Add a new Remote Site for your Cloud Run URL (e.g., `https://movement-voice-demo-511662304947.us-central1.run.app`).
    - Go to a **Lead Record**.
    - Click **Edit Page**.
    - Drag `Sales AI Platform Agent` onto the page layout.
    - Save and Activate.

## Configuration

To change the backend URL:
1.  Edit `force-app/main/default/classes/SalesAICallout.cls`.
2.  Update the `ENDPOINT` constant.
3.  Redeploy.
