# Thyrocare B2B Doctor Portal (Full-Stack Enterprise Solution)

An enterprise-ready, medical-grade B2B distribution software portal for Thyrocare doctor partners. Includes real-time authentication, passcode verification with `bcrypt` and JWT session tracking, dynamic rate catalog search, custom panel financial estimator, and client-side file data extraction engine (Excel `.xlsx` and PDF `.pdf`).

---

## 🌟 Key Features & Specifications

### 1. Dynamic Authentication & Passcode Security
* **Lock Screen Overlay**: High-contrast modal modal upon load blocking dashboard access.
* **REST API & Passcode Hashing**: Auth via `POST /api/v1/auth/verify-passcode` with server-side `bcrypt` hashing and 8-hour JWT token issuance.
* **Database Entity Schema (`doctors`)**:
  * `doctor_id` (String, Primary Key)
  * `passcode_hash` (String, Hashed via Bcrypt)
  * `doctor_name` (String, e.g. "Dr. A. Sharma, MD")
  * `clinic_name` (String)
  * `is_active` (Boolean)
  * `created_at` (Timestamp)
* **Real-time Session Revocation**: Immediate verification on window `focus` and 15-second background interval polling calling `GET /api/v1/auth/verify-session`. If suspended (`is_active = false`), token is purged and user is locked out immediately.
* **Header & Logout**: Displays metadata and "Lock Portal" button.

### 2. Clinical File Parsing Engine
* **Drag-and-Drop Dropzone**: Supports Excel (`.xlsx`, `.xls`) and PDF (`.pdf`).
* **Excel Parsing (SheetJS)**: Interactive searchable HTML table render from uploaded spreadsheets.
* **PDF Parsing (PDF.js)**: Page-by-page text extraction into a monospace preview block with line dividers and "Copy to Clipboard" trigger.
* **Micro-interactions**: Parsing spinners, error toast alerts, and reset button.

### 3. B2B Rate Catalog & Live Search
* **Thyrocare Diagnostic Offerings**: Pre-populated catalog (Thyroid Profile Total, Lipid Profile Extended, HbA1c, Vitamin D/B12, Liver Function Test, Renal Function Test, CBC, Cardiac Risk Panel).
* **Fields**: Test Code, Test Name, Specimen Type, Standard MRP (₹), B2B Partner Rate (₹), Doctor Margin Savings (₹ & %).
* **Instant Filtering**: Real-time search across Test Code, Name, or Specimen.

### 4. Custom Package Builder & Financial Estimator
* **Panel Creation**: Checkbox selection from catalog to assemble custom patient groups.
* **Live Calculations**: Total Retail MRP, Total B2B Cost, Total Doctor Savings.
* **Export Engine**: Export quote formatted in **CSV** or clinical **TXT Summary**.

---

## 🚀 Quick Start Guide

### Prerequisites
- Node.js (v16+ recommended)
- npm

### 1. Install Dependencies
```bash
cd /Users/pushkarverma/.gemini/antigravity/scratch/thyrocare-b2b-portal
npm install
```

### 2. Start Server
```bash
npm start
```
The server will start at `http://localhost:3000`.

---

## 🔑 Demo Doctor Credentials

| Doctor ID | Passcode | Account Status | Notes |
| :--- | :--- | :--- | :--- |
| `DOC1001` | `thyrocare123` | **Active** | Primary test account |
| `DOC1002` | `clinic456` | **Active** | Secondary doctor account |
| `DOC1003` | `locked789` | **Suspended** | Test real-time lock-out |

---

## 🔌 API Endpoints Summary

- `POST /api/v1/auth/verify-passcode` - Authenticates Doctor ID & Passcode, returns JWT token.
- `GET /api/v1/auth/verify-session` - Validates JWT header & returns live account active status.
- `GET /api/v1/catalog` - Returns diagnostic test catalog dataset.
- `POST /api/v1/admin/toggle-status` - Utility endpoint to test live session revocation (`{ doctor_id, is_active }`).
