# Capstone Project Submission Guidelines

Follow the steps below to submit your Capstone Project.

### 1. Fork the Repository

Click the **Fork** button at the top-right of this repository, or use the following link:

```text
https://github.com/mulearngectcr/ai_ig_final_projects
```

This creates a copy of the submission repository under your personal GitHub account.

### 2. Clone Your Fork

Clone your forked repository to your local machine:

```Bash
git clone [https://github.com/<your-username>/ai_ig_final_projects.git
cd ai_ig_final_projects
```

### 3. Create a Folder with Your Name / Team Name
Inside the repository root, create a single directory named with your full name in kebab-case. Place your complete project files inside this directory.

Example structure:

```Plaintext
ai_ig_final_projects/
├── john-doe/
   ├── backend/
   │   ├── main.py
   │   └── requirements.txt
   ├── frontend/
   │   └── app.py
   ├── .env.example
   └── README.md
```

Your project folder must include:

- Complete frontend and backend source code

- ```requirements.txt``` or ```Dockerfile```

- ```.env.example``` (documenting required environment variables without actual secrets)

- A dedicated ```README.md``` inside your folder containing:

- Project Title & Problem Statement

- Architecture & Concept Breakdown

- Live Deployed Frontend URL

- Live Deployed Backend API URL

### 4. Commit Your Changes
Stage your folder and commit your changes:

```Bash
git add john-doe/
git commit -m "Add capstone submission - John Doe"
```

### 5. Push to Your Fork
Push the changes to your remote fork:

```Bash
git push origin main
```

### 6. Create a Pull Request (PR)

1. Open your forked repository on GitHub.
2. Click Contribute → Open Pull Request.
3. Ensure the base repository is ```mulearngectcr/ai_ig_final_projects``` and base branch is ```main```.
4. Fill in the Pull Request details.

#### Pull Request Title Format
```Plaintext
Capstone Submission - <Your Name>
```
Example:

```Plaintext
Capstone Submission - John Doe
```

Pull Request Description Template
```
Project Overview

- Project Name: CampusPrep AI
- Author: John Doe

Live URLs

- Frontend: [https://your-frontend.streamlit.app]
- Backend API: [https://your-backend.onrender.com/docs]
```

### Important Rules & Checklist

- Strict Namespace Isolation: Create only one directory with your name. Do not place files outside your directory.
- Do Not Touch Peer Submissions: Never edit, move, or delete files belonging to other participants.
- Never Commit Secrets: Do not commit actual API keys or .env files. Use .env.example instead.
- Deployment is Mandatory: Both the frontend and backend must be live and accessible via public URLs when the PR is submitted.
- Verify Execution: Confirm your hosted apps are responsive before submitting your Pull Request.
