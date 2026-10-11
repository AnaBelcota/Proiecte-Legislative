# Summer Internship Project

## Overview & Functionality

This project automates data scraping from the official portals of the Romanian Parliament: **Chamber of Deputies (CDEP)** and the **Senate (Senat)**.

- **Data Extraction Flow:**
  - Navigates through the target platforms (CDEP / Senat).
  - Collects the registration number and title for each legislative proposal.
  - Opens each individual project page to extract detailed metadata.
- **Data Storage:**
   - Saves the final structured output into a **JSON** format (migrated from an initial PostgreSQL schema for improved portability and easier downstream access).

## Technical Implementation

- **Senat:** Built using **Selenium** to handle dynamic client-side rendering and navigation that prevented direct static scraping.
- **CDEP:** Implemented using **BeautifulSoup** (alongside `requests`) for efficient static HTML parsing.
