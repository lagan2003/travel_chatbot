# 🗺️ Travel Itinerary Chatbot (Groq-Powered)

An AI-driven travel planning application that generates personalized, realistic, and detailed itineraries using high-performance LLMs via the Groq API.

## 🚀 Overview

This application leverages the speed of Groq and the intelligence of models like Llama 3 to create tailored travel plans. Users can specify their destination, budget, duration, interests, and preferred pace to receive a comprehensive day-by-day itinerary.

## ✨ Features

-   **Personalized Planning**: Tailors itineraries based on budget, interests (food, culture, landmarks, etc.), and travel pace.
-   **Smart Grouping**: Activities are organized by neighborhood to minimize transit time.
-   **Budget Allocation**: Automatically suggests a breakdown for lodging, food, transport, and attractions.
-   **Interactive UI**: Built with Streamlit for a seamless, user-friendly experience.
-   **Professional Exports**: Download your itinerary as a **Markdown** file or a formatted **PDF**.
-   **Real-time Generation**: Powered by Groq for near-instant response times.

## 🛠️ Tech Stack

-   **Frontend**: [Streamlit](https://streamlit.io/)
-   **AI Inference**: [Groq Cloud API](https://console.groq.com/) (Llama 3 models)
-   **Data Validation**: [Pydantic](https://docs.pydantic.dev/)
-   **PDF Generation**: [ReportLab](https://www.reportlab.com/)
-   **Environment Management**: `python-dotenv`

## 📋 Prerequisites

-   Python 3.10+
-   A Groq API Key (Get one at [console.groq.com](https://console.groq.com/))

## ⚙️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/lagan2003/travel_chatbot.git
    cd travel_chatbot
    ```

2.  **Set up a virtual environment**:
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Create a `.env` file in the root directory:
    ```env
    GROQ_API_KEY=your_groq_api_key_here
    DEFAULT_MODEL=llama-3.3-70b-versatile
    APP_TITLE=Travel Itinerary Chatbot
    DEFAULT_CURRENCY=INR
    DEFAULT_TIMEZONE=Asia/Kolkata
    ```

## 🚀 Usage

1.  **Run the application**:
    ```bash
    streamlit run app.py
    ```
2.  Open your browser to `http://localhost:8501`.
3.  Enter your trip details in the sidebar.
4.  Click **"Generate Itinerary"** and wait for the magic to happen!
5.  Download your plan using the **Markdown** or **PDF** buttons.

## 📁 Project Structure

```text
├── app.py                # Main Streamlit UI
├── itinerary_engine.py    # Logic for Groq API interaction
├── schema.py             # Pydantic models for data structure
├── utils.py              # Helper functions (Markdown/PDF conversion)
├── prompts/
│   └── system_prompt.md  # AI behavior instructions
├── requirements.txt      # Project dependencies
└── .env                  # (Hidden) Environment configuration
```

## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request for improvements, bug fixes, or new features.

## 📄 License

This project is open-source and available under the MIT License.
