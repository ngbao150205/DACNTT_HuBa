# Sentiment AI System

## Description

Sentiment AI System is an AI-based application for analyzing customer sentiment from e-commerce reviews.

The system collects customer feedback from e-commerce platforms, processes Vietnamese text data, applies artificial intelligence models to classify customer sentiment, and provides visualization dashboards to support business decision-making.

The main goal of this project is to help online sellers automatically understand customer opinions, detect negative feedback, identify potential issues, and improve customer satisfaction.

---

# System Architecture

The project consists of multiple modules:

## Frontend

User interface dashboard developed with:

- React
- TypeScript
- Vite
- Tailwind CSS

Responsibilities:

- Display analysis results.
- Visualize customer sentiment statistics.
- Provide product analysis interface.
- Manage user interactions.


## Backend

API service developed with:

- FastAPI
- SQLAlchemy

Responsibilities:

- Handle frontend requests.
- Manage business logic.
- Communicate with database.
- Connect AI model services.


## AI Service

Sentiment analysis module.

Responsibilities:

- Process customer reviews.
- Classify sentiment:
  - Positive
  - Negative
  - Neutral
- Analyze customer feedback patterns.


## Crawler

Data collection module.

Responsibilities:

- Collect product information.
- Collect customer reviews from e-commerce platforms.
- Prepare raw data for analysis.


## Database

Data storage system using:

- PostgreSQL

Stores:

- Product information.
- Customer reviews.
- Sentiment analysis results.
- Issue classification results.

---

# Features

## 1. Customer Sentiment Classification

Automatically classify customer reviews into three sentiment groups:

- Positive
- Negative
- Neutral


## 2. Negative Feedback Analysis

Analyze negative customer feedback and identify possible causes:

- Product quality problems.
- Packaging issues.
- Shipping delays.
- Customer service problems.


## 3. Risk Review Detection

Automatically detect high-risk reviews containing keywords related to:

- Fake products.
- Fraud.
- Safety problems.
- Serious complaints.


## 4. Competitor Analysis

Analyze public customer reviews from competitor products to:

- Understand customer opinions.
- Identify product weaknesses.
- Support business strategy.


---

# Project Structure

# Create file:
- backend/.env

Add:

DATABASE_URL=postgresql://username:password@localhost:5432/sentiment_ai

