import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import UUID
import uuid
import re
from psycopg2.extras import RealDictCursor

from predict import predict_price
from db import get_connection

app = FastAPI()

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ValveInput(BaseModel):
    Service_Fluid: str
    Valve_Type: str
    Body_Material_Grade: str
    Actuator_Type: str
    End_Connection: str
    Seat_Type: str
    Pressure_Class_ASME: int
    NPS_inch: float
    Operating_Pressure_bar: float
    Operating_Temperature_C: float
    DeltaP_bar: float
    Cv: float


try:
    from paddleocr import PaddleOCR
    OCR_AVAILABLE = True
    OCR_IMPORT_ERROR = None
except Exception as exc:
    OCR_AVAILABLE = False
    OCR_IMPORT_ERROR = str(exc)


OCR_INSTANCE = None


def get_ocr():
    global OCR_INSTANCE
    if OCR_INSTANCE is None:
        if not OCR_AVAILABLE:
            raise RuntimeError(
                OCR_IMPORT_ERROR or "PaddleOCR is not installed")
        OCR_INSTANCE = PaddleOCR(use_angle_cls=True, lang="en")
    return OCR_INSTANCE


def extract_text_from_pdf(file_bytes: bytes) -> str:
    if not OCR_AVAILABLE:
        raise HTTPException(
            status_code=500, detail="PaddleOCR is not installed on the server")

    try:
        import fitz  # PyMuPDF
        render_backend = "fitz"
    except Exception:
        render_backend = None

    if render_backend is None:
        try:
            from pdf2image import convert_from_bytes
            render_backend = "pdf2image"
        except Exception:
            render_backend = None

    if render_backend is None:
        raise HTTPException(
            status_code=500,
            detail="No PDF renderer available. Install PyMuPDF or pdf2image."
        )

    ocr = get_ocr()
    texts = []

    if render_backend == "fitz":
        import fitz  # noqa: F401
        import numpy as np
        from PIL import Image

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_arr = np.array(img)
            result = ocr.ocr(img_arr, cls=True)
            texts.extend(extract_text_lines(result))
        doc.close()
    else:
        from pdf2image import convert_from_bytes
        import numpy as np

        images = convert_from_bytes(file_bytes, dpi=200)
        for img in images:
            img_arr = np.array(img)
            result = ocr.ocr(img_arr, cls=True)
            texts.extend(extract_text_lines(result))

    return " ".join(texts)


def extract_text_lines(ocr_result):
    lines = []
    if not ocr_result:
        return lines

    for block in ocr_result:
        if isinstance(block, list):
            for item in block:
                if isinstance(item, (list, tuple)) and len(item) > 1:
                    content = item[1]
                    if isinstance(content, (list, tuple)) and content:
                        lines.append(str(content[0]))
                    else:
                        lines.append(str(content))
    return lines


def find_value(patterns, text, cast=None):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            value = value.replace(",", "")
            if cast:
                try:
                    return cast(value)
                except ValueError:
                    pass
            return value
    return None


def extract_fields(text: str):
    normalized = re.sub(r"\s+", " ", text)

    patterns = {
        "Service_Fluid": [r"Service\s*Fluid\s*[:=-]\s*([A-Za-z0-9 /-]+)"],
        "Valve_Type": [r"Valve\s*Type\s*[:=-]\s*([A-Za-z0-9 /-]+)"],
        "Body_Material_Grade": [r"Body\s*Material\s*(?:Grade)?\s*[:=-]\s*([A-Za-z0-9 /-]+)"],
        "Actuator_Type": [r"Actuator\s*Type\s*[:=-]\s*([A-Za-z0-9 /-]+)"],
        "End_Connection": [r"End\s*Connection\s*[:=-]\s*([A-Za-z0-9 /-]+)"],
        "Seat_Type": [r"Seat\s*Type\s*[:=-]\s*([A-Za-z0-9 /-]+)"],
        "Pressure_Class_ASME": [r"Pressure\s*Class\s*(?:ASME)?\s*[:=-]\s*([0-9]+)"],
        "NPS_inch": [r"NPS\s*(?:\(in\)|inch|in)?\s*[:=-]\s*([0-9]+(?:\.[0-9]+)?)"],
        "Operating_Pressure_bar": [r"Operating\s*Pressure\s*(?:\(bar\)|bar)?\s*[:=-]\s*([0-9]+(?:\.[0-9]+)?)"],
        "Operating_Temperature_C": [r"Operating\s*Temperature\s*(?:\(C\)|C)?\s*[:=-]\s*([0-9]+(?:\.[0-9]+)?)"],
        "DeltaP_bar": [r"Delta\s*P\s*(?:\(bar\)|bar)?\s*[:=-]\s*([0-9]+(?:\.[0-9]+)?)", r"?P\s*(?:\(bar\)|bar)?\s*[:=-]\s*([0-9]+(?:\.[0-9]+)?)"],
        "Cv": [r"\bCv\b\s*[:=-]\s*([0-9]+(?:\.[0-9]+)?)"]
    }

    extracted = {}
    missing = []

    for key, pats in patterns.items():
        cast = float if key not in {"Pressure_Class_ASME"} else int
        if key in {"Service_Fluid", "Valve_Type", "Body_Material_Grade", "Actuator_Type", "End_Connection", "Seat_Type"}:
            cast = None
        value = find_value(pats, normalized, cast=cast)
        if value is None:
            missing.append(key)
        else:
            extracted[key] = value

    return extracted, missing


def create_prediction(input_data):
    valve_id = str(uuid.uuid4())
    price = predict_price(input_data)

    conn = get_connection()
    cur = conn.cursor()

    query = """
    INSERT INTO valve_price_predictions(
        valve_id,
        service_fluid,
        valve_type,
        body_material_grade,
        actuator_type,
        end_connection,
        seat_type,
        pressure_class_asme,
        nps_inch,
        operating_pressure_bar,
        operating_temperature_c,
        deltap_bar,
        cv,
        predicted_price_inr,
        confidence_score,
        lower_price_range,
        upper_price_range,
        model_name
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    confidence = 85
    lower_price = float(price) * 0.9
    upper_price = float(price) * 1.1

    cur.execute(query, (
        valve_id,
        input_data["Service_Fluid"],
        input_data["Valve_Type"],
        input_data["Body_Material_Grade"],
        input_data["Actuator_Type"],
        input_data["End_Connection"],
        input_data["Seat_Type"],
        int(input_data["Pressure_Class_ASME"]),
        float(input_data["NPS_inch"]),
        float(input_data["Operating_Pressure_bar"]),
        float(input_data["Operating_Temperature_C"]),
        float(input_data["DeltaP_bar"]),
        float(input_data["Cv"]),
        float(price),
        confidence,
        lower_price,
        upper_price,
        "CatBoost_V1"
    ))

    conn.commit()
    cur.close()
    conn.close()

    return {
        "valve_id": valve_id,
        "price": float(price),
        "confidence": confidence
    }


@app.post("/predict")
def predict(valve: ValveInput):
    input_data = valve.dict()
    print("Incoming request:", input_data)
    return create_prediction(input_data)


@app.post("/predict-from-pdf")
async def predict_from_pdf(file: UploadFile = File(...)):
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(
            status_code=415, detail="Only PDF files are supported")

    file_bytes = await file.read()
    text = extract_text_from_pdf(file_bytes)
    extracted, missing = extract_fields(text)

    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Missing required fields from PDF",
                "missing_fields": missing,
                "extracted_fields": extracted
            }
        )

    response = create_prediction(extracted)
    response["extracted_fields"] = extracted
    return response


@app.get("/predictions")
def get_predictions():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT valve_id, predicted_price_inr
    FROM valve_price_predictions
    ORDER BY created_at DESC
    LIMIT 20
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [{"valve_id": r[0], "price": r[1]} for r in rows]


@app.get("/predictions/{valve_id}")
def get_valve_details_by_id(valve_id: UUID):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            id,
            valve_id,
            service_fluid,
            valve_type,
            body_material_grade,
            actuator_type,
            end_connection,
            seat_type,
            pressure_class_asme,
            nps_inch,
            operating_pressure_bar,
            operating_temperature_c,
            deltap_bar,
            cv,
            predicted_price_inr,
            confidence_score,
            lower_price_range,
            upper_price_range,
            model_name,
            created_at
        FROM valve_price_predictions
        WHERE valve_id = %s
    """, (str(valve_id),))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Valve ID not found")

    return row
