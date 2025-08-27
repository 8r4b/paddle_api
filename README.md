# Email Sentiment Analysis API

This is a FastAPI-based API for analyzing the sentiment and tone of email text.

## Features

*   User registration and authentication
*   Email verification
*   Password reset
*   Sentiment and tone analysis using OpenAI

## Prerequisites

*   Python 3.10+
*   PostgreSQL database
*   OpenAI API key
*   SMTP server for sending emails

## Setup

1.  Clone the repository:

    ```bash
    git clone <repository_url>
    ```

2.  Create a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3.  Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4.  Configure the environment variables:

    *   Create a `.env` file in the root directory of the project.
    *   Add the following environment variables to the `.env` file:

        ```properties
        DATABASE_URL=postgresql://<username>:<password>@<host>:<port>/<database_name>
        OPENAI_API_KEY=<your_openai_api_key>
        SECRET_KEY=<your_secret_key>
        ALGORITHM=HS256
        ACCESS_TOKEN_EXPIRE_MINUTES=30
        SMTP_SERVER=<your_smtp_server>
        SMTP_PORT=<your_smtp_port>
        SMTP_USER=<your_smtp_user>
        SMTP_PASSWORD=<your_smtp_password>
        API_DOMAIN=<your_api_domain>
        ```

        *   Replace the placeholders with your actual values.

5.  Run the database migrations:

    ```bash
    # (If you're using Alembic or a similar migration tool)
    # alembic upgrade head
    ```

6.  Run the application:

    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 10000 --reload
    ```

## API Endpoints

*   `POST /users/register`: Register a new user
*   `GET /users/verify`: Verify a user's email address
*   `POST /users/loging`: Log in an existing user
*   `POST /users/request-password-reset`: Request a password reset
*   `POST /users/reset-password`: Reset a user's password
*   `POST /analyze`: Analyze the sentiment and tone of email text (requires authentication)

## Deployment

1.  Deploy the application to a hosting platform such as Render.
2.  Configure the environment variables in the hosting platform's dashboard.
3.  Set the start command to `uvicorn app.main:app --host 0.0.0.0 --port 10000`.

## Paddle Integration (Optional)

1.  Create a Paddle account.
2.  Set up your product in Paddle.
3.  Implement Paddle webhooks in your API to handle subscription events.

## Contributing

Contributions are welcome! Please submit a pull request with your changes.

##