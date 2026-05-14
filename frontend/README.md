# AutoClean Frontend

Modern React frontend for the AutoClean data cleaning system.

## Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000

## Features

- **Dashboard**: View all uploaded datasets
- **Upload**: Upload datasets with purpose (rule extraction or cleaning) and modality selection
- **Dataset Detail**: View dataset info, profile data, and extract rules
- **Rules**: Review, approve, and provide feedback on extracted rules
- **Cleaning**: Apply approved rules to clean datasets

## API Connection

The frontend connects to the backend API at `http://127.0.0.1:8000`. Make sure the backend server is running.

## Build for Production

```bash
npm run build
```

The built files will be in the `dist` directory.










