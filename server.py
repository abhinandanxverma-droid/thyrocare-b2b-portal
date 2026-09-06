#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
import sys
import hashlib
import hmac
import base64
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

PORT = 3000
SECRET_KEY = b"thyrocare_b2b_secret_key_2026"
ADMIN_PASSWORD_HASH = hashlib.sha256(b"Abhinandanverma@8811").hexdigest()

def hash_passcode(passcode):
    return hashlib.sha256(passcode.encode('utf-8')).hexdigest()

doctors_db = {
    "DOC1001": {
        "doctor_id": "DOC1001",
        "passcode_hash": hash_passcode("thyrocare123"),
        "doctor_name": "Dr. A. Sharma, MD",
        "clinic_name": "Apex Diagnostic & Healthcare Clinic",
        "is_active": True,
        "created_at": "2025-01-15T08:00:00Z"
    },
    "DOC1002": {
        "doctor_id": "DOC1002",
        "passcode_hash": hash_passcode("clinic456"),
        "doctor_name": "Dr. Priya Nair, MBBS, DNB",
        "clinic_name": "Nair HealthCare & Diagnostics",
        "is_active": True,
        "created_at": "2025-02-01T10:30:00Z"
    },
    "DOC1003": {
        "doctor_id": "DOC1003",
        "passcode_hash": hash_passcode("locked789"),
        "doctor_name": "Dr. Rajesh Verma, MD",
        "clinic_name": "Metro Wellness Center",
        "is_active": False,
        "created_at": "2025-02-10T14:15:00Z"
    }
}

TEST_CATALOG = []
catalog_file_path = os.path.join(os.path.dirname(__file__), 'catalog_data.json')
if os.path.exists(catalog_file_path):
    with open(catalog_file_path, 'r') as f:
        TEST_CATALOG = json.load(f)
else:
    TEST_CATALOG = [
        { "code": "THY001", "name": "Thyroid Profile Total (T3, T4, TSH)", "specimen": "Blood / Serum", "mrp": 600, "b2b_rate": 250, "description": "Thyroid gland evaluation." }
    ]

orders_db = []
WHATSAPP_TARGETS = ["6284828212", "7719401188"]

def parse_iso_datetime(date_str):
    if not date_str:
        return datetime.now()
    try:
        clean = str(date_str).replace('Z', '').split('+')[0].split('.')[0]
        return datetime.fromisoformat(clean)
    except Exception:
        try:
            return datetime.strptime(clean, "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return datetime.now()

def seed_demo_orders():
    now = datetime.now()
    demo_samples = [
        {"days_ago": 0, "pat": "Sunil Kumar", "mob": "9876543210", "doc": "DOC1001", "tests": ["THY001", "HBA003"]},
        {"days_ago": 2, "pat": "Meena Agarwal", "mob": "9812345678", "doc": "DOC1001", "tests": ["LIP002", "VIT004"]},
        {"days_ago": 5, "pat": "Rohan Gupta", "mob": "9988776655", "doc": "DOC1002", "tests": ["CBC007", "LFT005"]},
        {"days_ago": 15, "pat": "Ananya Roy", "mob": "9765432109", "doc": "DOC1001", "tests": ["THY001", "RFT006"]},
        {"days_ago": 45, "pat": "Vikram Singh", "mob": "9654321098", "doc": "DOC1002", "tests": ["CAR008", "HBA003"]},
    ]

    for idx, sample in enumerate(demo_samples):
        placed_dt = now - timedelta(days=sample["days_ago"], hours=idx*2)
        doc = doctors_db.get(sample["doc"])
        selected_tests = [t for t in TEST_CATALOG if t["code"] in sample["tests"]]
        if not selected_tests:
            selected_tests = TEST_CATALOG[:2]
        
        mrp_total = sum(t["mrp"] for t in selected_tests)
        b2b_total = sum(t["b2b_rate"] for t in selected_tests)
        
        order = {
            "order_id": f"ORD-2026-{1000 + idx + 1}",
            "placed_at": placed_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "doctor_id": doc["doctor_id"],
            "doctor_name": doc["doctor_name"],
            "clinic_name": doc["clinic_name"],
            "patient_name": sample["pat"],
            "patient_mobile": sample["mob"],
            "tests": selected_tests,
            "total_mrp": mrp_total,
            "total_b2b": b2b_total,
            "total_savings": mrp_total - b2b_total,
            "recipient_numbers": WHATSAPP_TARGETS,
            "status": "COMPLETED"
        }
        orders_db.append(order)

seed_demo_orders()

def generate_token(doctor_id):
    payload = {
        "doctor_id": doctor_id,
        "exp": int(time.time()) + 28800
    }
    payload_str = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    sig = hmac.new(SECRET_KEY, payload_str.encode(), hashlib.sha256).hexdigest()
    return f"{payload_str}.{sig}"

def verify_token(token):
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None
        payload_str, sig = parts[0], parts[1]
        expected_sig = hmac.new(SECRET_KEY, payload_str.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        padded_str = payload_str + '=' * (4 - len(payload_str) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_str.encode()).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload.get("doctor_id")
    except Exception:
        return None

class PortalHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(os.path.dirname(__file__), 'public'), **kwargs)

    def do_POST(self):
        global orders_db
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b'{}'
        
        try:
            body = json.loads(body_bytes.decode('utf-8'))
        except Exception:
            body = {}

        if parsed.path == '/api/v1/auth/verify-passcode':
            doctor_id = str(body.get('doctor_id', '')).strip().upper()
            passcode = str(body.get('passcode', '')).strip()

            if not doctor_id or not passcode:
                return self.send_json_response(400, {"error": "Doctor ID and Passcode are required."})

            doctor = doctors_db.get(doctor_id)
            if not doctor or doctor['passcode_hash'] != hash_passcode(passcode):
                return self.send_json_response(401, {"error": "Invalid Doctor ID or Passcode."})

            if not doctor['is_active']:
                return self.send_json_response(403, {"error": "Account suspended. Please contact Thyrocare B2B Support."})

            token = generate_token(doctor_id)
            return self.send_json_response(200, {
                "message": "Authentication successful",
                "token": token,
                "doctor": {
                    "doctor_id": doctor["doctor_id"],
                    "doctor_name": doctor["doctor_name"],
                    "clinic_name": doctor["clinic_name"],
                    "is_active": doctor["is_active"]
                }
            })

        elif parsed.path == '/api/v1/doctor/update-profile':
            doctor_id = str(body.get('doctor_id', '')).strip().upper()
            doctor_name = str(body.get('doctor_name', '')).strip()
            clinic_name = str(body.get('clinic_name', '')).strip()
            new_passcode = str(body.get('passcode', '')).strip()

            doc = doctors_db.get(doctor_id)
            if not doc:
                return self.send_json_response(404, {"error": "Doctor account not found."})

            if doctor_name:
                doc["doctor_name"] = doctor_name
            if clinic_name:
                doc["clinic_name"] = clinic_name
            if new_passcode:
                doc["passcode_hash"] = hash_passcode(new_passcode)

            return self.send_json_response(200, {
                "message": "Profile updated successfully!",
                "doctor": {
                    "doctor_id": doc["doctor_id"],
                    "doctor_name": doc["doctor_name"],
                    "clinic_name": doc["clinic_name"],
                    "is_active": doc["is_active"]
                }
            })

        elif parsed.path == '/api/v1/admin/auth':
            admin_password = str(body.get('password', '')).strip()
            if hash_passcode(admin_password) == ADMIN_PASSWORD_HASH:
                admin_token = generate_token("ADMIN_SUPERUSER")
                return self.send_json_response(200, {
                    "message": "Admin authentication successful",
                    "admin_token": admin_token
                })
            else:
                return self.send_json_response(401, {"error": "Invalid Admin Password."})

        elif parsed.path == '/api/v1/orders/place':
            doctor_id = str(body.get('doctor_id', '')).upper()
            patient_name = str(body.get('patient_name', '')).strip()
            patient_mobile = str(body.get('patient_mobile', '')).strip()
            test_codes = body.get('test_codes', [])

            if not doctor_id or not patient_name or not patient_mobile or not test_codes:
                return self.send_json_response(400, {"error": "Missing patient details or test selections."})

            doc = doctors_db.get(doctor_id)
            if not doc:
                return self.send_json_response(404, {"error": "Doctor not found."})

            selected_tests = [t for t in TEST_CATALOG if t["code"] in test_codes]
            if not selected_tests:
                return self.send_json_response(400, {"error": "Invalid test selections."})

            mrp_total = sum(t["mrp"] for t in selected_tests)
            b2b_total = sum(t["b2b_rate"] for t in selected_tests)
            placed_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            order_id = f"ORD-2026-{1000 + len(orders_db) + 1}"

            new_order = {
                "order_id": order_id,
                "placed_at": placed_at,
                "doctor_id": doc["doctor_id"],
                "doctor_name": doc["doctor_name"],
                "clinic_name": doc["clinic_name"],
                "patient_name": patient_name,
                "patient_mobile": patient_mobile,
                "tests": selected_tests,
                "total_mrp": mrp_total,
                "total_b2b": b2b_total,
                "total_savings": mrp_total - b2b_total,
                "recipient_numbers": WHATSAPP_TARGETS,
                "status": "COMPLETED"
            }

            orders_db.append(new_order)

            test_names_str = ", ".join([f"{t['name']} ({t['code']})" for t in selected_tests])
            formatted_dt = datetime.now().strftime("%d %b %Y, %I:%M %p")
            
            wa_text = (
                f"*THYROCARE NEW B2B ORDER*\n"
                f"----------------------------------\n"
                f"🆔 *Order ID*: {order_id}\n"
                f"📅 *Timestamp*: {formatted_dt}\n"
                f"👨‍⚕️ *Doctor*: {doc['doctor_name']}\n"
                f"🏥 *Clinic*: {doc['clinic_name']} ({doc['doctor_id']})\n"
                f"👤 *Patient Name*: {patient_name}\n"
                f"📞 *Patient Mobile*: {patient_mobile}\n"
                f"🧪 *Tests to Perform*: {test_names_str}\n"
                f"💰 *Total B2B Rate*: ₹{b2b_total} (MRP: ₹{mrp_total})\n"
                f"----------------------------------\n"
                f"Please process dispatch & sample collection."
            )

            import urllib.parse
            encoded_text = urllib.parse.quote(wa_text)
            
            whatsapp_links = [
                {"number": "6284828212", "url": f"https://wa.me/916284828212?text={encoded_text}"},
                {"number": "7719401188", "url": f"https://wa.me/917719401188?text={encoded_text}"}
            ]

            return self.send_json_response(200, {
                "message": "Order placed successfully!",
                "order": new_order,
                "whatsapp_text": wa_text,
                "whatsapp_links": whatsapp_links
            })

        elif parsed.path == '/api/v1/admin/orders/edit':
            order_id = str(body.get('order_id', '')).strip()
            patient_name = str(body.get('patient_name', '')).strip()
            patient_mobile = str(body.get('patient_mobile', '')).strip()
            test_codes = body.get('test_codes', [])

            target_order = next((o for o in orders_db if o['order_id'] == order_id), None)
            if not target_order:
                return self.send_json_response(404, {"error": f"Order {order_id} not found."})

            if patient_name:
                target_order['patient_name'] = patient_name
            if patient_mobile:
                target_order['patient_mobile'] = patient_mobile
            if test_codes and len(test_codes) > 0:
                selected_tests = [t for t in TEST_CATALOG if t["code"] in test_codes]
                if selected_tests:
                    target_order['tests'] = selected_tests
                    mrp_total = sum(t["mrp"] for t in selected_tests)
                    b2b_total = sum(t["b2b_rate"] for t in selected_tests)
                    target_order['total_mrp'] = mrp_total
                    target_order['total_b2b'] = b2b_total
                    target_order['total_savings'] = mrp_total - b2b_total

            return self.send_json_response(200, {
                "message": f"Successfully updated order {order_id}",
                "order": target_order
            })

        elif parsed.path == '/api/v1/admin/orders/delete':
            order_id = str(body.get('order_id', '')).strip()
            initial_len = len(orders_db)
            orders_db = [o for o in orders_db if o['order_id'] != order_id]

            if len(orders_db) < initial_len:
                return self.send_json_response(200, {"message": f"Order {order_id} deleted successfully."})
            else:
                return self.send_json_response(404, {"error": f"Order {order_id} not found."})

        elif parsed.path == '/api/v1/admin/doctors/add':
            doc_id = str(body.get('doctor_id', '')).strip().upper()
            doc_name = str(body.get('doctor_name', '')).strip()
            clinic_name = str(body.get('clinic_name', '')).strip()
            passcode = str(body.get('passcode', '')).strip()
            is_active = body.get('is_active', True)

            if not doc_id or not doc_name or not clinic_name or not passcode:
                return self.send_json_response(400, {"error": "All fields are required."})

            if doc_id in doctors_db:
                return self.send_json_response(400, {"error": f"Doctor ID {doc_id} already exists."})

            doctors_db[doc_id] = {
                "doctor_id": doc_id,
                "passcode_hash": hash_passcode(passcode),
                "doctor_name": doc_name,
                "clinic_name": clinic_name,
                "is_active": bool(is_active),
                "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            }

            return self.send_json_response(200, {
                "message": f"Successfully created Doctor {doc_id}",
                "doctor": {
                    "doctor_id": doc_id,
                    "doctor_name": doc_name,
                    "clinic_name": clinic_name,
                    "is_active": bool(is_active)
                }
            })

        elif parsed.path == '/api/v1/admin/doctors/edit':
            doc_id = str(body.get('doctor_id', '')).strip().upper()
            doc_name = str(body.get('doctor_name', '')).strip()
            clinic_name = str(body.get('clinic_name', '')).strip()
            passcode = str(body.get('passcode', '')).strip()
            is_active = body.get('is_active')

            if doc_id not in doctors_db:
                return self.send_json_response(404, {"error": "Doctor account not found."})

            doc = doctors_db[doc_id]
            if doc_name:
                doc["doctor_name"] = doc_name
            if clinic_name:
                doc["clinic_name"] = clinic_name
            if isinstance(is_active, bool):
                doc["is_active"] = is_active
            if passcode:
                doc["passcode_hash"] = hash_passcode(passcode)

            return self.send_json_response(200, {
                "message": f"Successfully updated Doctor {doc_id}",
                "doctor": {
                    "doctor_id": doc["doctor_id"],
                    "doctor_name": doc["doctor_name"],
                    "clinic_name": doc["clinic_name"],
                    "is_active": doc["is_active"]
                }
            })

        else:
            return self.send_json_response(404, {"error": "Not Found"})

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/api/v1/auth/verify-session':
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return self.send_json_response(401, {"valid": False, "error": "Missing or invalid authorization header."})
            
            token = auth_header.split(' ')[1]
            doc_id = verify_token(token)

            if not doc_id or doc_id not in doctors_db:
                return self.send_json_response(401, {"valid": False, "error": "Session expired or invalid."})

            doctor = doctors_db[doc_id]
            if not doctor['is_active']:
                return self.send_json_response(401, {"valid": False, "revoked": True, "error": "Account has been suspended by administration."})

            return self.send_json_response(200, {
                "valid": True,
                "doctor": {
                    "doctor_id": doctor["doctor_id"],
                    "doctor_name": doctor["doctor_name"],
                    "clinic_name": doctor["clinic_name"],
                    "is_active": doctor["is_active"]
                }
            })

        elif parsed.path == '/api/v1/catalog':
            return self.send_json_response(200, {
                "total": len(TEST_CATALOG),
                "catalog": TEST_CATALOG
            })

        elif parsed.path == '/api/v1/admin/doctors':
            sanitized_doctors = []
            for d_id, doc in doctors_db.items():
                sanitized_doctors.append({
                    "doctor_id": doc["doctor_id"],
                    "doctor_name": doc["doctor_name"],
                    "clinic_name": doc["clinic_name"],
                    "is_active": doc["is_active"],
                    "created_at": doc.get("created_at", "")
                })
            return self.send_json_response(200, {
                "total": len(sanitized_doctors),
                "doctors": sanitized_doctors
            })

        elif parsed.path == '/api/v1/admin/orders':
            query_params = parse_qs(parsed.query)
            date_range = query_params.get('range', ['all'])[0]
            start_date_str = query_params.get('start', [''])[0]
            end_date_str = query_params.get('end', [''])[0]

            now = datetime.now()
            filtered_orders = []

            for ord_item in orders_db:
                dt = parse_iso_datetime(ord_item['placed_at'])
                days_diff = (now - dt).total_seconds() / 86400.0

                if date_range == '7days':
                    if 0 <= days_diff <= 7.0:
                        filtered_orders.append(ord_item)
                elif date_range == 'month':
                    if 0 <= days_diff <= 30.0:
                        filtered_orders.append(ord_item)
                elif date_range == 'custom' and start_date_str and end_date_str:
                    try:
                        s_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
                        e_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                        if s_dt <= dt <= e_dt:
                            filtered_orders.append(ord_item)
                    except Exception:
                        filtered_orders.append(ord_item)
                else:
                    filtered_orders.append(ord_item)

            filtered_orders.sort(key=lambda x: parse_iso_datetime(x['placed_at']), reverse=True)

            total_revenue_b2b = sum(o['total_b2b'] for o in filtered_orders)
            total_mrp_val = sum(o['total_mrp'] for o in filtered_orders)
            total_savings_val = sum(o['total_savings'] for o in filtered_orders)

            return self.send_json_response(200, {
                "total_orders": len(filtered_orders),
                "total_revenue_b2b": total_revenue_b2b,
                "total_mrp_val": total_mrp_val,
                "total_savings_val": total_savings_val,
                "range_applied": date_range,
                "orders": filtered_orders
            })

        else:
            filepath = os.path.join(self.directory, parsed.path.lstrip('/'))
            if not os.path.exists(filepath) or os.path.isdir(filepath):
                self.path = '/index.html'
            return super().do_GET()

    def send_json_response(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()

if __name__ == '__main__':
    print("====================================================")
    print(f" Thyrocare B2B Doctor Portal Server Running")
    print(f" URL: http://localhost:{PORT}")
    print(f" Seeded Accounts:")
    print(f"  - DOC1001 : thyrocare123 (Active)")
    print(f"  - DOC1002 : clinic456    (Active)")
    print(f"  - DOC1003 : locked789    (Suspended/Revoked)")
    print(f" Admin Password: Abhinandanverma@8811")
    print("====================================================")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), PortalHandler) as httpd:
        httpd.serve_forever()
