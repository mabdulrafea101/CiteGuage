# CiteGauge: Citation Prediction Platform

CiteGauge is a web application designed for researchers to track their academic work and get predictions on future citation counts. It integrates with the Web of Science (WOS) API to search for papers and uses machine learning models to forecast their impact.

## Machine Learning Models

At the heart of CiteGauge are two predictive models. We experimented with both to see which would provide the most accurate citation forecasts.

### LightGBM (The Winning Model)

**LightGBM (Light Gradient Boosting Machine)** proved to be the more effective model for our needs, achieving **71% accuracy**.

- **Why it works better:** LightGBM is a tree-based learning algorithm. It excels at handling complex, non-linear relationships in data, which is very common in citation patterns. It can understand the intricate "decisions" and factors (like keywords, publication year, journal type) that influence a paper's future citations.

### Ridge Regression

We also implemented Ridge Regression as an alternative model.

- **Performance:** While Ridge Regression was very fast, its accuracy was lower. As a linear model, it struggled to capture the complex, decision-based nature of the data. It's great for simpler problems but wasn't the best fit for predicting something as nuanced as academic citations.

---

## Core Functionalities

The application is built with a range of features to support a researcher's workflow. Based on the project's URL structure, here are the key capabilities:

#### 1. User Authentication & Profiles
*   **Signup, Login, Logout:** Standard user account management.
*   **Researcher Profiles:** Users can create, view, and update their professional profiles, including details like their institution and research interests.

#### 2. Web of Science (WOS) Paper Search
*   Users can search the extensive Web of Science database for academic papers directly from our application.
*   Search results from WOS are automatically saved as JSON files for record-keeping and future analysis.

#### 3. Citation Prediction
*   **For Searched Papers:** The application uses the high-performing **LightGBM model** to predict the future citation count for papers found through the WOS search.
*   **For Uploaded Documents:** Users can upload their own papers, and the system will provide citation predictions for them as well.

#### 4. JSON Data Management
*   **File Listing:** A dedicated page lists all the JSON files generated from previous WOS searches in a clean, searchable table.
*   **File Viewing:** Users can inspect the content of any JSON file in two ways:
    *   **Raw View:** See the complete, pretty-printed JSON data.
    *   **Table View:** View the key information (Title, UID, etc.) from the papers within the JSON file in a structured table.

#### 5. Paper Collection Management
*   **Import from JSON:** Users can easily import papers from their saved JSON files into their personal "My Research" collection.
*   **Upload Your Own:** Researchers can upload their own papers directly to build their collection and get predictions.

---

## How It Works: A Typical User Flow

1.  A researcher **signs up** for an account and sets up their profile.
2.  They use the **WOS Search** feature to find relevant papers (e.g., by topic, author, or title).
3.  The search results are saved as a **JSON file**.
4.  The researcher navigates to the **"My WOS Searched"** page to see a list of their saved JSON files.
5.  From there, they can choose to **"View as Table"** to quickly scan the papers or **"View Data"** to see the raw JSON.
6.  They can then click an **"Import"** button to add all the papers from a specific JSON file to their personal collection.
7.  For any paper in their collection (or from a new search), they can trigger a **citation prediction**, which uses the LightGBM model to forecast its future impact.

This combination of features makes CiteGauge a powerful tool for researchers to manage and analyze academic literature.

---

## Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

You will need the following software installed on your system:
*   Python 3.8+
*   pip
*   Redis (for Celery task queue, as configured in `core/settings.py`)

### Installation

1.  **Clone the repository:**
    ```sh
    git clone https://your-repository-url/CiteGuage.git
    cd CiteGuage/UI design/project
    ```

2.  **Create and activate a virtual environment:**
    ```sh
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3.  **Install the dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

4.  **Set up the database:**
    ```sh
    python manage.py migrate
    ```

5.  **Run the development server:**
    ```sh
    python manage.py runserver
    ```
    The application will be available at `http://12.0.0.1:8000`.

---

## Configuration

The application requires an API key for the Web of Science.

*   Open `core/settings.py`.
*   Find the `WOS_API_KEY` variable and replace the placeholder value with your actual API key.

```python
# core/settings.py

# ...
# Add your API key here
WOS_API_KEY = "YOUR_WOS_API_KEY_HERE"
```
