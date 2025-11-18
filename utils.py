from datetime import date
from rules import *
import pandas as pd
import calendar


months_map = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}
months     = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
week_days  = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO']

prev          = pd.Timestamp.now() - pd.DateOffset(months=1)
n_month, year = prev.month, prev.year
columna       = prev.strftime("%Y%m")


def classify_holidays(holidays):

    # rows de la table (TOTAL + lunes-sábado, sin domingo)
    rows = ['TOTAL FESTIVOS'] + week_days[:-1]

    # Inicializamos estructura
    table = {}
    for row in rows:
        table[row] = {}
        for col in months:
            if row == 'TOTAL FESTIVOS': table[row][col] = 0      # contador
            else:                       table[row][col] = []     # lista de días
        table[row]['TOTAL AÑO'] = 0

    # Procesamos los festivos
    for text in holidays:

        t = text.strip()

        # '1 de enero' -> ['1', 'enero']
        parts = [p.strip() for p in t.split(' de ')]

        day = int(parts[0])
        month_name = parts[1].lower()

        mes_num   = months_map[month_name]
        col_month =     months[mes_num - 1]

        # Creamos la fecha para obtener el día de la semana
        date_obj = date(year, mes_num, day)
        idx_day = date_obj.weekday()   # lunes=0 ... domingo=6

        # Si es domingo, NO se cuenta
        if idx_day == 6: continue

        day_name = week_days[idx_day]

        # Actualizamos totales por mes / año
        table['TOTAL FESTIVOS'][col_month] += 1
        table['TOTAL FESTIVOS']['TOTAL AÑO'] += 1

        # Guardamos el día en su row (lunes-sábado)
        if day_name in table: table[day_name][col_month].append(day)

    # Totales por día de la semana
    for day_name in week_days[:-1]:  # lunes-sábado
        total = 0
        for col in months:
            if isinstance(table[day_name][col], list):
                total += len(table[day_name][col])
        table[day_name]['TOTAL AÑO'] = total

    # Convertimos las listas de días a texto "1 6 24"
    for day_name in week_days[:-1]:
        for col in months:
            days_list = table[day_name][col]
            if isinstance(days_list, list):
                if days_list:
                    table[day_name][col] = ' '.join(
                        str(x) for x in sorted(days_list)
                    )
                else:
                    table[day_name][col] = ''

    # Pasamos a DataFrame
    df = pd.DataFrame(table).T
    df = df.loc[rows]  # asegurar orden de rows
    return df

def get_types_of_days(classified_holidays):

    def _count_days_in_cell(cell):
        """Cuenta cuántos días hay en una celda tipo '1 6 24'."""
        if isinstance(cell, str):
            s = cell.strip()
            if not s:
                return 0
            return len([x for x in s.split() if x])
        elif isinstance(cell, (int, float)):
            return int(cell)
        return 0    
    
    rows = [
        'DÍAS DEL MES',
        'DOMINGOS',
        'FESTIVOS',
        'DÍAS SIN SERVICIO',
        'DÍAS CON SERVICIO',
        'LUNES-VIERNES NO FEST.',
        'SÁBADOS NO FEST.',
    ]

    # Estructura base
    table = {row: {col: 0 for col in months} for row in rows}
    for row in rows: table[row]['TOTAL AÑO'] = 0

    # Recorremos meses
    for m in range(1, 13):
        col = months[m - 1]
        n_month_days = calendar.monthrange(year, m)[1]

        # Contamos lunes-viernes, sábados y domingos del mes
        total_m_f = total_sat = total_sun = 0
        for day in range(1, n_month_days + 1):
            w = date(year, m, day).weekday()   # 0=lunes ... 6=domingo
            if   w <= 4: total_m_f += 1
            elif w == 5: total_sat += 1
            else:        total_sun += 1

        # Festivos de la tabla (ya excluidos los domingos)
        holidays_month = int(classified_holidays.loc['TOTAL FESTIVOS', col])

        # Cuántos festivos caen lunes-viernes y cuántos en sábado
        holidays_m_f = sum(
            _count_days_in_cell(classified_holidays.loc[day_sem, col])
            for day_sem in week_days[:-2]
        )
        holidays_sat = _count_days_in_cell(classified_holidays.loc['SÁBADO', col])

        # (opcional) coherencia interna
        assert holidays_m_f + holidays_sat == holidays_month

        days_without_service = total_sun + holidays_month
        days_with_service    = n_month_days - days_without_service
        m_f_no_fest          = total_m_f - holidays_m_f
        sab_no_fest          = total_sat - holidays_sat

        # Guardamos en la tabla
        table['DÍAS DEL MES'][col]           = n_month_days
        table['DOMINGOS'][col]               = total_sun
        table['FESTIVOS'][col]               = holidays_month
        table['DÍAS SIN SERVICIO'][col]      = days_without_service
        table['DÍAS CON SERVICIO'][col]      = days_with_service
        table['LUNES-VIERNES NO FEST.'][col] = m_f_no_fest
        table['SÁBADOS NO FEST.'][col]       = sab_no_fest

        # Totales año
        table['DÍAS DEL MES']['TOTAL AÑO']           += n_month_days
        table['DOMINGOS']['TOTAL AÑO']               += total_sun
        table['FESTIVOS']['TOTAL AÑO']               += holidays_month
        table['DÍAS SIN SERVICIO']['TOTAL AÑO']      += days_without_service
        table['DÍAS CON SERVICIO']['TOTAL AÑO']      += days_with_service
        table['LUNES-VIERNES NO FEST.']['TOTAL AÑO'] += m_f_no_fest
        table['SÁBADOS NO FEST.']['TOTAL AÑO']       += sab_no_fest

    df = pd.DataFrame(table).T
    df = df.loc[rows]  # asegurar orden de rows
    return df

def hours_of_service(types_of_days):

    def _table_hours(types_of_days, columns, rules, service_days_row):

        # Sub-dataframe con solo las columnas relevantes
        base = types_of_days.loc[:, columns]

        table = {}

        table['DÍAS CON SERVICIO'] = base.loc[service_days_row]

        # Horas por servicio
        for service, weights in rules.items():
            coefficients = pd.Series(weights)  # index = filas usadas
            sub = base.loc[coefficients.index] # solo esas filas
            hours = (sub.T * coefficients).sum(axis=1)
            table[service] = hours

        return pd.DataFrame(table)

    columns = list(months) + ['TOTAL AÑO']

    df_azul = _table_hours(
        types_of_days    = types_of_days,
        columns          = columns,
        rules            = AZUL_RULES,
        service_days_row = 'DÍAS CON SERVICIO'
    )

    df_verde = _table_hours(
        types_of_days    = types_of_days,
        columns          = columns,
        rules            = VERDE_RULES,
        service_days_row = 'LUNES-VIERNES NO FEST.'
    )

    return df_azul, df_verde

def calculate_hours_by_schedules(hours_of_azul_service, hours_of_verde_service):
    
    data_verde = hours_of_verde_service.iloc[n_month-1]
    data_azul  =  hours_of_azul_service.iloc[n_month-1]

    dicc = {**data_verde.to_dict(), **data_azul.to_dict()}

    dicc.pop('DÍAS CON SERVICIO', None)

    dicc = {int(k): int(v) for k, v in dicc.items()}

    return dicc

def process_segundos(historical_places, hours_by_schedules):

    places_of_this_month = historical_places[["ZONA", "SECTOR", "HORARIO", "ID ZONA", "ID GIS", "NOMBRE DE CALLE", columna]].copy()
    places_of_this_month.rename(columns={columna: 'PLAZAS'}, inplace=True)

    # coger la columna del mes y año correspondiente de plazas y multiplicar por las segundos del horario correspondiente al hours_by_schedules
    places_of_this_month['SEGUNDOS'] = places_of_this_month['PLAZAS'] * places_of_this_month['HORARIO'].map(hours_by_schedules) * 3600
    seconds_of_this_month = places_of_this_month.drop(columns=['PLAZAS'], inplace=True)


    # RESULTADOS
    s_verdes = seconds_of_this_month[seconds_of_this_month["ZONA"] == "VERDE"]['SEGUNDOS'].sum() 
    s_azules = seconds_of_this_month[seconds_of_this_month["ZONA"] ==  "AZUL"]['SEGUNDOS'].sum()
    porcentaje_s_verdes = s_verdes / (s_verdes + s_azules) * 100
    porcentaje_s_azules = 100 - porcentaje_s_verdes

    print(f"Segundos verdes: {s_verdes} ({porcentaje_s_verdes:.2f}%)")
    print(f"Segundos azules: {s_azules} ({porcentaje_s_azules:.2f}%)")
    print(f"TOTAL: {s_verdes + s_azules}")

    seconds_of_this_month.rename(columns={'SEGUNDOS': columna}, inplace=True)

    return seconds_of_this_month

def merge_with_historical(historical, this_month):
    merged = pd.merge(historical, this_month, on=['ZONA', 'SECTOR', 'HORARIO', 'ID ZONA', 'ID GIS', 'NOMBRE DE CALLE'], how='outer')
    merged = merged.sort_values(by=['SECTOR', 'ZONA', 'NOMBRE DE CALLE'])
    return merged
