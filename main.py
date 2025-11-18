from holidays import holidays_2025 as holidays
from flask import Flask, request
from gcp.utils import *
from utils import *


def entry_point(req):
    # Prerequisito para ejecutar: Inventario de plazas actualizado

    historical_places  = get_historical_places_offered()
    historical_seconds = get_historical_seconds_offered()

    classified_holidays                           = classify_holidays(holidays)
    types_of_days                                 = get_types_of_days(classified_holidays)
    hours_of_azul_service, hours_of_verde_service = hours_of_service(types_of_days)
    hours_by_schedules                            = calculate_hours_by_schedules(hours_of_azul_service, hours_of_verde_service)

    seconds_of_this_month = process_segundos(historical_places, hours_by_schedules)
    merged                = merge_with_historical(historical_seconds, seconds_of_this_month)

    upload_seconds(merged)

    return "ETL ejecutado correctamente\n", 200


app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def run():
    return entry_point(request)
